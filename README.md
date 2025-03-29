# YouTube-Samalizer

YouTubeの動画を要約するCLIツール

## 概要

このツールは、YouTube動画のURLを入力として受け取り、Gemini APIを使用して動画の内容を要約するコマンドラインアプリケーションです。

## 要件

### 機能要件

- YouTube動画のURLを入力として受け付ける
- Gemini APIを使用して動画の要約を生成する
- コマンドライン引数でカスタマイズ可能なオプションを提供する
  - 要約の長さ（短い/標準/詳細）
  - 出力形式（テキスト/JSON）
  - 追加のプロンプト指定
  - Geminiモデルの選択
- エラーハンドリングとユーザーフレンドリーなエラーメッセージ

### 非機能要件

- 応答時間：要約生成は30秒以内
- エラー処理：ネットワークエラーやAPI制限に対する適切なハンドリング
- 再利用性：モジュール化された設計
- 拡張性：新しい機能の追加が容易な構造

## アーキテクチャ

```
youtube-samalizer/
├── src/
│   ├── __init__.py
│   ├── cli.py           # CLIインターフェース
│   ├── summarizer.py    # 要約ロジック
│   ├── youtube.py       # YouTube動画情報取得
│   └── gemini.py        # Gemini API連携
├── tests/               # テストファイル
├── requirements.txt     # 依存パッケージ
└── .env                 # 環境変数（APIキーなど）
```

### コンポーネント説明

1. CLIインターフェース（cli.py）
   - コマンドライン引数の処理
   - ユーザー入力の検証
   - 結果の表示

2. 要約エンジン（summarizer.py）
   - 要約処理のメインロジック
   - YouTubeとGemini APIの連携
   - 結果のフォーマット

3. YouTube連携（youtube.py）
   - 動画情報の取得
   - URLの検証

4. Gemini API連携（gemini.py）
   - APIクライアント
   - プロンプト生成
   - レスポンス処理
   - 各種モデルの設定と管理

## 使用技術

- Python 3.9+
- google-generativeai (Gemini API)
- click (CLIフレームワーク)
- python-dotenv (環境変数管理)
- pytest (テスト)

## CLIの使い方

```bash
# 基本的な使用方法
youtube-samalizer <YouTube-URL>

# オプション指定
youtube-samalizer <YouTube-URL> --length=short --format=json

# 追加プロンプト指定
youtube-samalizer <YouTube-URL> --prompt="5歳児向けに説明して"

# モデル指定
youtube-samalizer <YouTube-URL> --model=gemini-pro

# ヘルプ表示
youtube-samalizer --help
```

### オプション

- `--length`: 要約の長さ（short/normal/detailed）
- `--format`: 出力形式（text/json）
- `--prompt`: 追加のプロンプト
- `--lang`: 出力言語（デフォルト: 日本語）
- `--model`: 使用するGeminiモデル（デフォルト: gemini-2.0-flash-001）
  - 利用可能なモデル:
    - gemini-2.0-flash-001 (デフォルト): 高速な要約生成
    - gemini-pro: より詳細な分析と要約
    - gemini-pro-vision: 動画のビジュアル要素も考慮した要約

## インストール

```bash
pip install youtube-samalizer
```

## 環境設定

1. `.env`ファイルを作成
2. 必要な環境変数を設定:
   ```
   GEMINI_API_KEY=your_api_key
   ```

## 開発環境のセットアップ

```bash
# リポジトリのクローン
git clone https://github.com/username/youtube-samalizer.git
cd youtube-samalizer

# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt