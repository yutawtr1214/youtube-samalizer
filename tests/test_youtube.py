"""
YouTubeモジュールのテスト
"""
import pytest
from src.youtube import YouTubeError, extract_video_id, validate_youtube_url

def test_extract_video_id_valid_urls():
    """有効なYouTube URLからvideo_idを抽出できることを確認"""
    test_cases = [
        ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ('https://youtu.be/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ('https://www.youtube.com/v/dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
        ('https://youtube.com/watch?v=dQw4w9WgXcQ', 'dQw4w9WgXcQ'),
    ]

    for url, expected_id in test_cases:
        assert extract_video_id(url) == expected_id

def test_extract_video_id_invalid_urls():
    """無効なURLでYouTubeErrorが発生することを確認"""
    invalid_urls = [
        'https://example.com',
        'https://youtube.com',
        'https://www.youtube.com/channel/123',
        'invalid_url',
    ]

    for url in invalid_urls:
        with pytest.raises(YouTubeError):
            extract_video_id(url)

def test_validate_youtube_url():
    """URLバリデーションが正しく機能することを確認"""
    valid_urls = [
        'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'https://youtu.be/dQw4w9WgXcQ',
    ]

    invalid_urls = [
        'https://example.com',
        'invalid_url',
    ]

    for url in valid_urls:
        assert validate_youtube_url(url) is True

    for url in invalid_urls:
        assert validate_youtube_url(url) is False