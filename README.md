# drone-circle-pm-bot

学生ドローン部の「週次ロードマップ生成 + タスクアサイン」自動化ボットです。

## 目的

ドローン部の属人化を解消したいですが、属人化の正体は「作業」ではなく「視点」の属人化です。
PMが普段行っている「目標から逆算してロードマップを分解し、タスクを各メンバーにアサインする」という
チーム全体を俯瞰する判断をLLM(Gemini)に代行させます。

さらに通知には必ず「なぜこの優先順位にしたか」という理由を含めます。これにより、単なる作業自動化ではなく、
部員が逆算思考そのものを学べること(思考の移植)を狙っています。

> **Note**: 旧来の「進行中・未着手タスクを列挙するだけ」の週次通知(`notify_active_tasks_csv.py`)は、
> 本システムの「優先順位づけ + 理由づけ」を含む上位版に統合し、置き換えました。

## アーキテクチャ

```
[Googleスプレッドシート]  ← 部員が週次で状況入力
        │ (週次Cronで起動)
        ▼
[GitHub Actions]
        ▼
[Python]
   1. Sheets読み込み (gspread + サービスアカウント)
   2. 前処理・事実の集計  ← ここはAIを使わない(Pythonだけ)
        ・依存関係からクリティカルパス算出(networkx)
        ・停滞タスク検知
        ・メンバーの空き稼働時間の集計
        ・大会までの残日数・直前判定
   3. 履歴ログ読み込み(前回の提案)
   4. Gemini APIで判断  ← ここだけAI
        入力 = 前処理で要約した「事実サマリ」
        出力 = ロードマップ+アサイン+理由(構造化JSON)
   5. Discord用に整形して送信
   6. 履歴ログに1行追記
```

役割分担の原則: **事実の集計はPython、総合判断だけGemini。** 生データを丸投げせず、
クリティカルパス・停滞・空き時間をPythonで要約してから渡します(精度もコストも良くなります)。

## ディレクトリ構成

```
drone-circle-pm-bot/
├── .github/workflows/weekly-roadmap.yml   # 週次Cron(月9:00 JST)+ workflow_dispatch
├── src/
│   ├── main.py         # 全体の流れ。--dry-run で送信・追記なしの確認モード
│   ├── config.py       # タブ名・ヘッダー別名・環境変数
│   ├── sheets.py        # gspreadで読み書き。normalize_header()でヘッダー表記ゆれを吸収
│   ├── preprocess.py   # 事実集計(AI不要):critical_path / detect_stalled / member_load / analyze_goal
│   ├── llm.py           # Gemini呼び出し。pydantic(RoadmapOutput)で構造化出力
│   ├── formatter.py     # 出力をDiscord用テキストに整形
│   └── notify.py        # Discord Webhook送信
├── prompts/system_prompt.md   # 逆算ロジック(判断軸)。コード変更なしで調整可
├── requirements.txt
├── .env.example
└── .gitignore
```

## スプレッドシート構成

対象: `SPREADSHEET_ID = 1AO2TPZP1_bZZ3BbGmwfwRYvMpWSIne7CnxEjP-JpYvs`

以下のタブを使います(ヘッダーは1行目。日付は `YYYY-MM-DD`、真偽は `TRUE`/`FALSE`)。
ヘッダー表記のゆれ(括弧・スペースの有無など)は `src/sheets.py` の `normalize_header()` で吸収しますが、
対応していない大きな表記違いがある場合は `src/config.py` の `*_HEADER_ALIASES` に追記してください。

| タブ | 列 |
|---|---|
| 大会・目標 | 大会名 / 大会日 / 目標内容 / 現在の目標か |
| タスク進捗 | タスクID / タスク名 / 部門 / 担当者 / 進捗率 / ステータス(未着手・進行中・完了) / ボトルネック理由(なし・部品待ち・技術難易度・稼働不足) / 依存タスクID / 残工数h / 備考 |
| メンバー状況 | 名前 / 週稼働時間h / 得意分野 / 経験レベル(初心者・中級・経験者) / 現在の担当タスク数 / 特記事項 |
| 履歴ログ | 週 / ロードマップJSON / 実績差分メモ(プログラムが自動追記) |

## セットアップ

### 1. Googleサービスアカウントの準備

1. GCPでサービスアカウントを作成し、鍵(JSON)を発行する
2. 鍵JSONの `client_email` を対象スプレッドシートに**編集者**として共有する

### 2. ローカルでの疎通確認

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env に GEMINI_API_KEY / SPREADSHEET_ID / GCP_SERVICE_ACCOUNT_JSON / DISCORD_WEBHOOK_URL を設定
set -a; source .env; set +a

python src/main.py --dry-run
```

`--dry-run` を付けると、Discordへの送信と履歴ログへの追記を行わず、事実サマリと送信予定メッセージを
標準出力に表示するだけの確認モードになります。

### 3. GitHub Secretsの登録

リポジトリの Settings → Secrets and variables → Actions に以下を登録します。

- `GEMINI_API_KEY`
- `GCP_SERVICE_ACCOUNT_JSON` (鍵JSONファイルの中身をそのまま貼り付け)
- `SPREADSHEET_ID`
- `DISCORD_WEBHOOK_URL`

### 4. 動作確認・週次運用

GitHub Actions の `Weekly Roadmap` ワークフローを `Run workflow` で手動実行して本番疎通を確認したら、
`.github/workflows/weekly-roadmap.yml` の cron(毎週月曜9:00 JST)により自動運用に移行します。

## 判断軸のカスタマイズ

`prompts/system_prompt.md` を編集することで、コードを変更せずにGeminiの判断ロジック(優先順位づけ・
アサインの考え方)を調整できます。

## 今後の拡張(TODO)

- 停滞検知を「前週比の進捗差分」で精緻化する(履歴にper-task進捗を持たせる)
- アサインをDiscordのリアクションで承認制にする
- Notionへの書き出しを追加する
