"""
CLIモジュールのテスト
"""
import json # jsonモジュールをインポート
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.cli import main
# ProcessingError をインポート
from src.summarizer import ProcessingError

# テスト用のモックデータ
MOCK_SUMMARY_TEXT = "これはテスト用の要約です。"
MOCK_SUMMARY_JSON = {
    "video": {"title": "Test Video", "author": "Test Author", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video_id": "dQw4w9WgXcQ"},
    "summary": {"text": MOCK_SUMMARY_TEXT, "model": "gemini-2.0-flash", "length": "normal", "language": "ja"}
}
MOCK_CHAPTERS_TEXT = """00:00:10 チャプター1の説明
00:01:25 チャプター2の説明"""
MOCK_CHAPTERS_JSON = {
    "video": {"title": "Test Video", "author": "Test Author", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video_id": "dQw4w9WgXcQ"},
    "chapters": [
        {"timestamp": "00:00:10", "description": "チャプター1の説明"},
        {"timestamp": "00:01:25", "description": "チャプター2の説明"}
    ]
}


@pytest.fixture
def runner():
    """CLIテスト用のランナー"""
    return CliRunner()

@pytest.fixture
def mock_process_video():
    """process_video関数のモック"""
    # src.cli内でimportされているprocess_videoをpatchする
    with patch('src.cli.process_video') as mock:
        # デフォルトでは要約テキストを返すように設定
        mock.return_value = MOCK_SUMMARY_TEXT
        yield mock

def test_version(runner):
    """バージョン表示オプションのテスト"""
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'YouTube-Samalizer version' in result.output

# --- 要約モードのテスト ---

def test_summary_mode_basic(runner, mock_process_video):
    """要約モードの基本的な使用方法のテスト"""
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, ['https://www.youtube.com/watch?v=dQw4w9WgXcQ']) # mode指定なし -> summary

            assert result.exit_code == 0
            assert MOCK_SUMMARY_TEXT in result.output
            mock_process_video.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                mode='summary', # デフォルトモード
                model='gemini-2.0-flash',
                length='normal',
                output_format='text',
                lang='ja',
                prompt=None,
                stream=False
            )

def test_summary_mode_with_options(runner, mock_process_video):
    """要約モード・オプション付きでの使用のテスト"""
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--mode', 'summary', # 明示的に指定
                '--model', 'gemini-pro',
                '--length', 'detailed',
                '--format', 'text',
                '--lang', 'en',
                '--prompt', 'Explain like I am five'
            ])

            assert result.exit_code == 0
            mock_process_video.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                mode='summary',
                model='gemini-pro',
                length='detailed',
                output_format='text',
                lang='en',
                prompt='Explain like I am five',
                stream=False
            )

def test_summary_mode_json_output(runner, mock_process_video):
    """要約モード・JSON形式での出力のテスト"""
    mock_process_video.return_value = MOCK_SUMMARY_JSON

    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--format', 'json' # mode指定なし -> summary
            ])

            assert result.exit_code == 0
            # JSON文字列として比較するためにdumpsを使用
            expected_output = json.dumps(MOCK_SUMMARY_JSON, ensure_ascii=False, indent=2)
            # 出力に含まれる改行などを考慮して比較
            assert expected_output in result.output.strip()
            mock_process_video.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                mode='summary',
                model='gemini-2.0-flash',
                length='normal',
                output_format='json', # JSON形式を指定
                lang='ja',
                prompt=None,
                stream=False
            )

def test_summary_mode_stream(runner, mock_process_video):
    """要約モード・ストリーミングのテスト"""
    # ストリーミングはテキストのみを返す想定
    mock_process_video.return_value = MOCK_SUMMARY_TEXT
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--stream' # mode指定なし -> summary
            ])

            assert result.exit_code == 0
            # アサーション文字列を修正 ('...' を追加)
            assert '=== 要約を生成中... ===' in result.output
            assert MOCK_SUMMARY_TEXT in result.output
            mock_process_video.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                mode='summary',
                model='gemini-2.0-flash',
                length='normal',
                output_format='text', # ストリーミング時はtext固定
                lang='ja',
                prompt=None,
                stream=True
            )

# --- チャプターモードのテスト ---

def test_chapter_mode_basic_text(runner, mock_process_video):
    """チャプターモード・基本的な使用方法・テキスト出力のテスト"""
    mock_process_video.return_value = MOCK_CHAPTERS_TEXT
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--mode', 'chapter'
            ])

            assert result.exit_code == 0
            assert '=== Chapter 結果 ===' in result.output
            assert MOCK_CHAPTERS_TEXT in result.output
            mock_process_video.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                mode='chapter',
                model='gemini-2.0-flash', # デフォルトモデル
                length='normal', # チャプターモードでは無視される
                output_format='text', # デフォルト形式
                lang='ja', # チャプターモードでは無視される
                prompt=None,
                stream=False # チャプターモードではstream=False固定
            )

def test_chapter_mode_json_output(runner, mock_process_video):
    """チャプターモード・JSON形式での出力のテスト"""
    mock_process_video.return_value = MOCK_CHAPTERS_JSON
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--mode', 'chapter',
                '--format', 'json'
            ])

            assert result.exit_code == 0
            expected_output = json.dumps(MOCK_CHAPTERS_JSON, ensure_ascii=False, indent=2)
            assert expected_output in result.output.strip()
            mock_process_video.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                mode='chapter',
                model='gemini-2.0-flash',
                length='normal',
                output_format='json', # JSON形式を指定
                lang='ja',
                prompt=None,
                stream=False
            )

def test_chapter_mode_with_prompt(runner, mock_process_video):
    """チャプターモード・プロンプト付きのテスト"""
    mock_process_video.return_value = MOCK_CHAPTERS_TEXT
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--mode', 'chapter',
                '--prompt', 'Focus on technical parts'
            ])

            assert result.exit_code == 0
            assert MOCK_CHAPTERS_TEXT in result.output
            mock_process_video.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                mode='chapter',
                model='gemini-2.0-flash',
                length='normal',
                output_format='text',
                lang='ja',
                prompt='Focus on technical parts', # プロンプトを指定
                stream=False
            )

# --- 共通エラーテスト ---

def test_missing_api_key(runner):
    """APIキーが設定されていない場合のエラーテスト"""
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {}, clear=True):
            result = runner.invoke(main, ['https://www.youtube.com/watch?v=dQw4w9WgXcQ'])

            assert result.exit_code != 0
            assert 'GEMINI_API_KEY' in result.output

def test_debug_mode(runner, mock_process_video):
    """デバッグモードのテスト"""
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--debug'
            ])

            assert result.exit_code == 0
            assert 'デバッグモード: 有効' in result.output
            assert 'パラメータ:' in result.output

def test_processing_error(runner, mock_process_video):
    """処理エラー発生時のテスト"""
    mock_process_video.side_effect = ProcessingError("Test processing error")
    with runner.isolated_filesystem(temp_dir=None) as td:
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, ['https://www.youtube.com/watch?v=dQw4w9WgXcQ'])

            assert result.exit_code != 0
            assert 'エラー: Test processing error' in result.output