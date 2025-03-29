"""
要約エンジンモジュールのテスト
"""
from unittest.mock import Mock, patch

import pytest
from google.genai import types

from src.summarizer import SummarizerError, generate_summary

# テスト用のモックデータ
MOCK_VIDEO_INFO = {
    'title': 'Test Video',
    'author': 'Test Author',
    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'video_id': 'dQw4w9WgXcQ'
}

MOCK_SUMMARY = "これはテスト用の要約です。"

@pytest.fixture
def mock_gemini_client():
    """Gemini APIクライアントのモック"""
    with patch('src.gemini.GeminiClient') as mock:
        client_instance = Mock()
        # generate_contentメソッドのモック
        mock_response = Mock()
        mock_response.text = MOCK_SUMMARY
        client_instance.models.generate_content.return_value = mock_response
        
        # generate_content_streamメソッドのモック
        mock_chunk = Mock()
        mock_chunk.text = MOCK_SUMMARY
        client_instance.models.generate_content_stream.return_value = [mock_chunk]
        
        mock.return_value = client_instance
        yield mock

@pytest.fixture
def mock_youtube():
    """YouTube関連関数のモック"""
    with patch('src.summarizer.validate_youtube_url') as mock_validate, \
         patch('src.summarizer.get_video_info') as mock_get_info:
        
        mock_validate.return_value = True
        mock_get_info.return_value = MOCK_VIDEO_INFO
        yield {
            'validate': mock_validate,
            'get_info': mock_get_info
        }

def test_generate_summary_text_format(mock_gemini_client, mock_youtube):
    """テキスト形式での要約生成をテスト"""
    summary = generate_summary(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        output_format='text'
    )

    assert summary == MOCK_SUMMARY
    mock_youtube['validate'].assert_called_once()
    mock_youtube['get_info'].assert_called_once()

def test_generate_summary_json_format(mock_gemini_client, mock_youtube):
    """JSON形式での要約生成をテスト"""
    summary = generate_summary(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        output_format='json'
    )

    assert isinstance(summary, dict)
    assert 'video' in summary
    assert 'summary' in summary
    assert summary['video'] == MOCK_VIDEO_INFO
    assert summary['summary']['text'] == MOCK_SUMMARY

def test_generate_summary_invalid_url(mock_gemini_client, mock_youtube):
    """無効なURLでのエラーハンドリングをテスト"""
    mock_youtube['validate'].return_value = False

    with pytest.raises(SummarizerError) as excinfo:
        generate_summary('invalid_url')

    assert '無効なYouTube URL' in str(excinfo.value)

def test_generate_summary_youtube_error(mock_gemini_client, mock_youtube):
    """YouTube情報取得エラーのハンドリングをテスト"""
    mock_youtube['get_info'].side_effect = Exception("YouTube error")

    with pytest.raises(SummarizerError) as excinfo:
        generate_summary('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

    assert 'YouTube動画の処理中にエラーが発生しました' in str(excinfo.value)

def test_generate_summary_with_options(mock_gemini_client, mock_youtube):
    """オプション付きでの要約生成をテスト"""
    options = {
        'model': 'gemini-pro',
        'length': 'detailed',
        'lang': 'en',
        'prompt': 'Explain like I am five'
    }

    summary = generate_summary(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        **options
    )

    assert summary == MOCK_SUMMARY
    # コンテンツ生成の呼び出しを確認
    mock_gemini_client.return_value.models.generate_content.assert_called_once()