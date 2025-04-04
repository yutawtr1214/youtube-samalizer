# YouTube-Samalizer

YouTubeの動画を要約、チャプター生成、または**課題解決構造を抽出**するCLIツール

## 概要

このツールは、YouTube動画のURLを入力として受け取り、Gemini APIを使用して動画の内容を**要約**、**チャプター分け**、または**動画が解決しようとしている課題とその解決ステップを抽出**するコマンドラインアプリケーションです。

## 要件

### 機能要件

- YouTube動画のURLを入力として受け付ける
- Gemini APIを使用して動画の要約を生成する
- Gemini APIを使用して動画のチャプター（タイムスタンプ付き）を生成する
- **Gemini APIを使用して動画の課題と解決ステップ（タイムスタンプ、URLリンク付き）を抽出する**
- コマンドライン引数でカスタマイズ可能なオプションを提供する
  - **実行モード (要約/チャプター/課題解決)**
  - 要約の長さ（短い/標準/詳細）
  - 出力形式（テキスト/JSON）
  - 追加のプロンプト指定
  - Geminiモデルの選択
- エラーハンドリングとユーザーフレンドリーなエラーメッセージ

### 非機能要件

- 応答時間：要約生成は30秒以内、チャプター生成は60秒以内、**課題解決構造抽出は90秒以内（動画長と内容による）**
- エラー処理：ネットワークエラーやAPI制限に対する適切なハンドリング
- 再利用性：モジュール化された設計
- 拡張性：新しい機能の追加が容易な構造

## アーキテクチャ

```
youtube-samalizer/
├── src/
│   ├── __init__.py
│   ├── cli.py           # CLIインターフェース
│   ├── summarizer.py    # 要約・チャプター・課題解決の制御
│   ├── youtube.py       # YouTube動画情報取得
│   └── gemini.py        # Gemini API連携 (要約・チャプター・課題解決)
├── tests/               # テストファイル
├── requirements.txt     # 依存パッケージ
├── .env.example         # 環境変数設定例
└── .gitignore           # Git無視ファイル
```

### コンポーネント説明

1. CLIインターフェース（cli.py）
   - コマンドライン引数の処理 (`--mode` オプション含む)
   - ユーザー入力の検証
   - 結果の表示 (要約/チャプター/課題解決)

2. 制御エンジン（summarizer.py）
   - **要約、チャプター生成、または課題解決構造抽出処理のメインロジック**
   - YouTubeとGemini APIの連携
   - 結果のフォーマット (**課題解決モードではURLリンク付与**)

3. YouTube連携（youtube.py）
   - 動画情報の取得（OEmbed API / YouTube Data API）
   - URLの検証
   - 動画の長さ情報取得（YouTube Data API使用時のみ）

4. Gemini API連携（gemini.py）
   - APIクライアント
   - **要約・チャプター・課題解決用プロンプト生成**
   - **要約・チャプター・課題解決API呼び出し**
   - レスポンス処理 (**チャプター解析、課題解決構造解析含む**)
   - タイムスタンプの検証（動画の長さ情報と照合）
   - 各種モデルの設定と管理

## 使用API

このアプリケーションは、主に以下の外部APIを使用しています：

### 1. Google Gemini API（必須）
- **用途**: 動画内容の分析、要約、チャプター生成、課題解決構造の抽出
- **認証**: API キーが必要（`.env`ファイルに`GEMINI_API_KEY`として設定）
- **注意点**: 
  - 一定量の無料枠がありますが、大量の使用は課金が必要になります
  - モデルによって性能と処理速度が異なります（要約には`gemini-2.0-flash`、課題解決には`gemini-pro`推奨）

### 2. YouTube APIs
このアプリケーションでは、YouTubeの情報を取得するために2つのAPIを使用しています：

#### a. YouTube OEmbed API（必須・APIキー不要）
- **用途**: 動画の基本情報（タイトル、作者名など）の取得
- **認証**: 不要
- **制限**: 詳細情報（動画の長さなど）は取得できない

#### b. YouTube Data API（オプション・推奨）
- **用途**: 動画の詳細情報、特に動画の長さ（duration）を取得
- **認証**: API キーが必要（`.env`ファイルに`YOUTUBE_API_KEY`として設定）
- **利点**: 
  - 正確な動画長情報の取得が可能（タイムスタンプ検証に使用）
  - より精度の高いチャプターや課題解決ステップのタイムスタンプを生成

#### YouTube Data APIの重要性

YouTube Data APIの設定は必須ではありませんが、推奨します。設定しない場合：

- 動画の長さ情報がGemini APIに提供されず、生成されるタイムスタンプの精度が低下
- タイムスタンプの検証が実質的に無効になり、不正確なタイムスタンプが結果に含まれる可能性
- 特にチャプターモードと課題解決モードでは、実際の動画時間を超えるタイムスタンプが生成される可能性があります

## 使用技術

- Python 3.9+
- **google-genai (Gemini API)**
- click (CLIフレームワーク)
- python-dotenv (環境変数管理)
- requests (HTTPクライアント)
- isodate (YouTube動画時間のパース)
- pytest (テスト)

## CLIの使い方

```bash
# 要約の基本的な使用方法 (デフォルトモード: summary)
python -m src.cli <YouTube-URL>

# チャプター生成の基本的な使用方法
python -m src.cli <YouTube-URL> --mode chapter

# 課題解決構造の抽出 (テキスト形式)
python -m src.cli <YouTube-URL> --mode solution

# 課題解決構造の抽出 (JSON形式)
python -m src.cli <YouTube-URL> --mode solution --format json

# 要約オプション指定
python -m src.cli <YouTube-URL> --length short --format json

# チャプター生成でモデル指定 (課題解決モードでも同様)
python -m src.cli <YouTube-URL> --mode chapter --model gemini-pro

# 追加プロンプト指定 (全モード共通)
python -m src.cli <YouTube-URL> --prompt="重要なポイントを強調して"

# ヘルプ表示
python -m src.cli --help
```

### オプション

- `--mode`: 実行モード (`summary`, `chapter`, `solution`、デフォルト: `summary`)
- `--length`: 要約の長さ (`short`/`normal`/`detailed`、`summary`モードのみ、デフォルト: `normal`)
- `--format`: 出力形式 (`text`/`json`、デフォルト: `text`)
- `--prompt`: 追加のプロンプト (全モード共通)
- `--lang`: 要約の出力言語 (`summary`モードのみ、デフォルト: `ja`)
- `--model`: 使用するGeminiモデル (デフォルト: `gemini-2.0-flash`)
  - 利用可能なモデル例:
    - `gemini-2.0-flash`: 高速な処理
    - `gemini-pro`: より詳細な分析、**課題解決モード推奨**
    - `gemini-pro-vision`: 視覚要素も考慮 (APIサポート状況による)
- `--stream`: ストリーミングモード (`summary`モードのテキスト出力のみ、デフォルト: 無効)
- `--version`: バージョン情報を表示
- `--debug`: デバッグモードを有効化

## インストールと実行

**1. リポジトリのクローン:**
```bash
git clone https://github.com/yutawtr1214/youtube-samalizer.git # あなたのリポジトリURLに置き換えてください
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
   - `.env` ファイルを開き、以下の環境変数を設定します：
   
   ```env
   # 必須: Gemini APIキー
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   
   # 推奨: YouTube Data APIキー (より正確なタイムスタンプ生成のため)
   YOUTUBE_API_KEY=YOUR_YOUTUBE_API_KEY_HERE
   
   # 他のオプション設定（必要に応じて変更）
   DEFAULT_MODEL=gemini-2.0-flash
   DEFAULT_SUMMARY_LENGTH=normal
   DEFAULT_OUTPUT_FORMAT=text
   DEFAULT_LANGUAGE=ja
   ```

**5. 実行:**
```bash
# 要約 (デフォルト)
python -m src.cli <YouTube-URL>

# チャプター生成
python -m src.cli <YouTube-URL> --mode chapter

# 課題解決構造の抽出
python -m src.cli <YouTube-URL> --mode solution
```

### APIキーの取得方法

1. **Gemini API キー (必須)**:
   - [Google AI Studio](https://ai.google.dev/) にアクセス
   - アカウント作成/ログイン後、APIキーを作成

2. **YouTube Data API キー (推奨)**:
   - [Google Cloud Console](https://console.cloud.google.com/) にアクセス
   - プロジェクトを作成
   - YouTube Data API v3 を有効化
   - 認証情報ページからAPIキーを作成

## 開発環境のセットアップ

上記インストール手順 1-4 を実行後、開発用パッケージもインストールします。
```bash
pip install -r requirements.txt # 念のため再実行
# 開発用依存関係はrequirements.txtに含めているため、追加インストールは不要
# (もし分ける場合は pip install -r requirements-dev.txt のようなコマンド)

# テストの実行
python -m pytest tests/ -v
```