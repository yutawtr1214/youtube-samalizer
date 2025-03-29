# YouTube-Samalizer

YouTubeの動画を要約またはチャプター生成するCLIツール

## 概要

このツールは、YouTube動画のURLを入力として受け取り、Gemini APIを使用して動画の内容を**要約**または**チャプター分け**するコマンドラインアプリケーションです。

## 要件

### 機能要件

- YouTube動画のURLを入力として受け付ける
- Gemini APIを使用して動画の要約を生成する
- **Gemini APIを使用して動画のチャプター（タイムスタンプ付き）を生成する**
- コマンドライン引数でカスタマイズ可能なオプションを提供する
  - **実行モード (要約/チャプター)**
  - 要約の長さ（短い/標準/詳細）
  - 出力形式（テキスト/JSON）
  - 追加のプロンプト指定
  - Geminiモデルの選択
- エラーハンドリングとユーザーフレンドリーなエラーメッセージ

### 非機能要件

- 応答時間：要約生成は30秒以内、**チャプター生成は60秒以内（動画長による）**
- エラー処理：ネットワークエラーやAPI制限に対する適切なハンドリング
- 再利用性：モジュール化された設計
- 拡張性：新しい機能の追加が容易な構造

## アーキテクチャ

```
youtube-samalizer/
├── src/
│   ├── __init__.py
│   ├── cli.py           # CLIインターフェース
│   ├── summarizer.py    # 要約・チャプター生成の制御 
│   ├── youtube.py       # YouTube動画情報取得
│   └── gemini.py        # Gemini API連携 (要約・チャプター生成)
├── tests/               # テストファイル
├── requirements.txt     # 依存パッケージ
├── .env.example         # 環境変数設定例
└── .gitignore           # Git無視ファイル
```

### コンポーネント説明

1. CLIインターフェース（cli.py）
   - コマンドライン引数の処理 (`--mode` オプション含む)
   - ユーザー入力の検証
   - 結果の表示 (要約/チャプター)

2. 制御エンジン（summarizer.py）
   - **要約またはチャプター生成処理のメインロジック**
   - YouTubeとGemini APIの連携
   - 結果のフォーマット

3. YouTube連携（youtube.py）
   - 動画情報の取得
   - URLの検証

4. Gemini API連携（gemini.py）
   - APIクライアント
   - **要約・チャプター生成用プロンプト生成**
   - **要約・チャプター生成API呼び出し**
   - レスポンス処理 (**チャプター解析含む**)
   - 各種モデルの設定と管理

## 使用技術

- Python 3.9+
- **google-genai (Gemini API)**
- click (CLIフレームワーク)
- python-dotenv (環境変数管理)
- requests (HTTPクライアント)
- pytest (テスト)

## CLIの使い方

```bash
# 要約の基本的な使用方法 (デフォルトモード: summary)
python -m src.cli <YouTube-URL>

# チャプター生成の基本的な使用方法
python -m src.cli <YouTube-URL> --mode chapter

# 要約オプション指定
python -m src.cli <YouTube-URL> --length short --format json

# チャプター生成でモデル指定
python -m src.cli <YouTube-URL> --mode chapter --model gemini-pro

# 追加プロンプト指定 (要約・チャプター共通)
python -m src.cli <YouTube-URL> --prompt="重要なポイントを強調して"

# ヘルプ表示
python -m src.cli --help
```

### オプション

- `--mode`: 実行モード (`summary` または `chapter`、デフォルト: `summary`)
- `--length`: 要約の長さ (`short`/`normal`/`detailed`、`summary`モードのみ、デフォルト: `normal`)
- `--format`: 出力形式 (`text`/`json`、デフォルト: `text`)
- `--prompt`: 追加のプロンプト (要約・チャプター共通)
- `--lang`: 要約の出力言語 (`summary`モードのみ、デフォルト: `ja`)
- `--model`: 使用するGeminiモデル (デフォルト: `gemini-2.0-flash`)
  - 利用可能なモデル例:
    - `gemini-2.0-flash`: 高速な処理
    - `gemini-pro`: より詳細な分析
    - `gemini-pro-vision`: 視覚要素も考慮 (APIサポート状況による)
- `--stream`: ストリーミングモード (`summary`モードのテキスト出力のみ、デフォルト: 無効)
- `--version`: バージョン情報を表示
- `--debug`: デバッグモードを有効化

## インストールと実行

**1. リポジトリのクローン:**
```bash
git clone https://github.com/your-username/youtube-samalizer.git # あなたのリポジトリURLに置き換えてください
cd youtube-samalizer
```

**2. 仮想環境の作成と有効化:**
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
```

**3. 依存パッケージのインストール:**
```bash
pip install -r requirements.txt
```

**4. 環境変数の設定:**
   - `.env.example` ファイルをコピーして `.env` ファイルを作成します。
   - `.env` ファイルを開き、`GEMINI_API_KEY` にあなたのGemini APIキーを設定します。
   ```.env
   GEMINI_API_KEY=YOUR_API_KEY_HERE
   # 他のデフォルト設定は必要に応じて変更
   ```

**5. 実行:**
```bash
# 要約 (デフォルト)
python -m src.cli <YouTube-URL>

# チャプター生成
python -m src.cli <YouTube-URL> --mode chapter
```

## 開発環境のセットアップ

上記インストール手順 1-4 を実行後、開発用パッケージもインストールします。
```bash
pip install -r requirements.txt # 念のため再実行
# 開発用依存関係はrequirements.txtに含めているため、追加インストールは不要
# (もし分ける場合は pip install -r requirements-dev.txt のようなコマンド)

# テストの実行
python -m pytest tests/ -v