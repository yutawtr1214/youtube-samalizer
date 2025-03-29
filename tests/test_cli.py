"""
CLIモジュールのテスト
"""
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from src.cli import main

# テスト用のモックデータ
MOCK_SUMMARY_TEXT = "これはテスト用の要約です。"
MOCK_SUMMARY_JSON = {
    "video": {
        "title": "Test Video",
        "author": "Test Author",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_id": "dQw4w9WgXcQ"
    },
    "summary": {
        "text": MOCK_SUMMARY_TEXT,
        "model": "gemini-2.0-flash-001",
        "length": "normal",
        "language": "ja"
    }
}

@pytest.fixture
def runner():
    """CLIテスト用のランナー"""
    return CliRunner()

@pytest.fixture
def mock_generate_summary():
    """generate_summary関数のモック"""
    with patch('src.cli.generate_summary') as mock:
        mock.return_value = MOCK_SUMMARY_TEXT
        yield mock

def test_version(runner):
    """バージョン表示オプションのテスト"""
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert 'YouTube-Samalizer version' in result.output

def test_basic_usage(runner, mock_generate_summary):
    """基本的な使用方法のテスト"""
    with runner.isolated_filesystem():
        # 環境変数を設定
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, ['https://www.youtube.com/watch?v=dQw4w9WgXcQ'])
            
            assert result.exit_code == 0
            assert MOCK_SUMMARY_TEXT in result.output
            mock_generate_summary.assert_called_once()

def test_with_options(runner, mock_generate_summary):
    """オプション付きでの使用のテスト"""
    with runner.isolated_filesystem():
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--model', 'gemini-pro',
                '--length', 'detailed',
                '--format', 'text',
                '--lang', 'en',
                '--prompt', 'Explain like I am five'
            ])
            
            assert result.exit_code == 0
            mock_generate_summary.assert_called_once_with(
                url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                model='gemini-pro',
                length='detailed',
                output_format='text',
                lang='en',
                prompt='Explain like I am five'
            )

def test_json_output(runner, mock_generate_summary):
    """JSON形式での出力のテスト"""
    mock_generate_summary.return_value = MOCK_SUMMARY_JSON
    
    with runner.isolated_filesystem():
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--format', 'json'
            ])
            
            assert result.exit_code == 0
            assert '"title": "Test Video"' in result.output
            assert '"text": "これはテスト用の要約です。"' in result.output

def test_missing_api_key(runner):
    """APIキーが設定されていない場合のエラーテスト"""
    with runner.isolated_filesystem():
        with patch.dict('os.environ', clear=True):
            result = runner.invoke(main, ['https://www.youtube.com/watch?v=dQw4w9WgXcQ'])
            
            assert result.exit_code == 1
            assert 'GEMINI_API_KEY' in result.output

def test_debug_mode(runner, mock_generate_summary):
    """デバッグモードのテスト"""
    with runner.isolated_filesystem():
        with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
            result = runner.invoke(main, [
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                '--debug'
            ])
            
            assert result.exit_code == 0
            assert 'デバッグモード: 有効' in result.output
            assert 'パラメータ:' in result.output