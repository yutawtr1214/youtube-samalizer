"""
要約・チャプター生成エンジンモジュールのテスト
"""
from unittest.mock import Mock, patch

import pytest
from google.genai import types

# ProcessingError と process_video をインポート
from src.summarizer import ProcessingError, process_video
from src.youtube import YouTubeError # YouTubeErrorをインポート
from src.gemini import GeminiError # GeminiErrorをインポート

# テスト用のモックデータ
MOCK_VIDEO_INFO = {
    'title': 'Test Video',
    'author': 'Test Author',
    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'video_id': 'dQw4w9WgXcQ'
}

MOCK_SUMMARY = "これはテスト用の要約です。"
MOCK_CHAPTERS_RAW = """
[00:00:10] チャプター1の説明
[00:01:25] チャプター2の説明、少し長め
[00:05:03] 最後のチャプター
"""
MOCK_CHAPTERS_PARSED = [
    ("00:00:10", "チャプター1の説明"),
    ("00:01:25", "チャプター2の説明、少し長め"),
    ("00:05:03", "最後のチャプター"),
]
MOCK_CHAPTERS_TEXT_OUTPUT = """00:00:10 チャプター1の説明
00:01:25 チャプター2の説明、少し長め
00:05:03 最後のチャプター"""
MOCK_CHAPTERS_JSON_OUTPUT = {
    'video': MOCK_VIDEO_INFO,
    'chapters': [
        {'timestamp': '00:00:10', 'description': 'チャプター1の説明'},
        {'timestamp': '00:01:25', 'description': 'チャプター2の説明、少し長め'},
        {'timestamp': '00:05:03', 'description': '最後のチャプター'}
    ]
}
# 課題解決モード用のモックデータ
MOCK_SOLUTION_STRUCTURE = {
    "problem": "動画の課題はこれです。",
    "steps": [
        {"timestamp": "00:00:05", "description": "ステップ1の説明"},
        {"timestamp": "00:00:30", "description": "ステップ2の説明"}
    ]
}
MOCK_SOLUTION_TEXT_OUTPUT = """## 解決する課題
動画の課題はこれです。

## 解決ステップ
1. [00:00:05](https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5s) ステップ1の説明
2. [00:00:30](https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s) ステップ2の説明"""
MOCK_SOLUTION_JSON_OUTPUT = {
    'video': MOCK_VIDEO_INFO,
    'solution': {
        "problem": "動画の課題はこれです。",
        "steps": [
            {"timestamp": "00:00:05", "description": "ステップ1の説明", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5s"},
            {"timestamp": "00:00:30", "description": "ステップ2の説明", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s"}
        ]
    }
}


@pytest.fixture
def mock_gemini_client():
    """Gemini APIクライアントのモック (src.summarizer内のGeminiClientをpatch)"""
    with patch('src.summarizer.GeminiClient') as mock:
        client_instance = Mock()
        # generate_summaryメソッドのモック
        client_instance.generate_summary.return_value = MOCK_SUMMARY
        # generate_chaptersメソッドのモック (パース済みのリストを返す)
        client_instance.generate_chapters.return_value = MOCK_CHAPTERS_PARSED
        # generate_solution_structureメソッドのモック (構造化データを返す)
        client_instance.generate_solution_structure.return_value = MOCK_SOLUTION_STRUCTURE
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

# --- 要約モードのテスト ---

def test_process_video_summary_text(mock_gemini_client, mock_youtube):
    """要約モード・テキスト形式のテスト"""
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='summary',
        output_format='text'
    )
    assert result == MOCK_SUMMARY
    mock_gemini_client.return_value.generate_summary.assert_called_once()
    mock_gemini_client.return_value.generate_chapters.assert_not_called()

def test_process_video_summary_json(mock_gemini_client, mock_youtube):
    """要約モード・JSON形式のテスト"""
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='summary',
        output_format='json'
    )
    assert isinstance(result, dict)
    assert result['summary']['text'] == MOCK_SUMMARY
    mock_gemini_client.return_value.generate_summary.assert_called_once()

def test_process_video_summary_with_options(mock_gemini_client, mock_youtube):
    """要約モード・オプション付きのテスト"""
    options = {
        'model': 'gemini-pro',
        'length': 'detailed',
        'lang': 'en',
        'prompt': 'Explain like I am five',
        'stream': False
    }
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='summary',
        **options
    )
    assert result == MOCK_SUMMARY
    mock_gemini_client.return_value.generate_summary.assert_called_once_with(
        video_info=MOCK_VIDEO_INFO,
        model='gemini-pro',
        length='detailed',
        additional_prompt='以下の要約をenで生成してください。\nExplain like I am five',
        stream=False
    )

# --- チャプターモードのテスト ---

def test_process_video_chapter_text(mock_gemini_client, mock_youtube):
    """チャプターモード・テキスト形式のテスト"""
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='chapter',
        output_format='text'
    )
    assert result == MOCK_CHAPTERS_TEXT_OUTPUT
    mock_gemini_client.return_value.generate_chapters.assert_called_once()
    mock_gemini_client.return_value.generate_summary.assert_not_called()


def test_process_video_chapter_json(mock_gemini_client, mock_youtube):
    """チャプターモード・JSON形式のテスト"""
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='chapter',
        output_format='json'
    )
    assert isinstance(result, dict)
    assert result == MOCK_CHAPTERS_JSON_OUTPUT
    mock_gemini_client.return_value.generate_chapters.assert_called_once()

def test_process_video_chapter_with_prompt(mock_gemini_client, mock_youtube):
    """チャプターモード・プロンプト付きのテスト"""
    prompt = "特に技術的な部分を詳しく"
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='chapter',
        prompt=prompt
    )
    assert result == MOCK_CHAPTERS_TEXT_OUTPUT # モックは同じ結果を返す
    mock_gemini_client.return_value.generate_chapters.assert_called_once_with(
        video_info=MOCK_VIDEO_INFO,
        model='gemini-2.0-flash', # デフォルトモデル
        additional_prompt=prompt
    )

# --- 課題解決モードのテスト ---

def test_process_video_solution_text(mock_gemini_client, mock_youtube):
    """課題解決モード・テキスト形式のテスト"""
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='solution',
        output_format='text'
    )
    assert result == MOCK_SOLUTION_TEXT_OUTPUT
    mock_gemini_client.return_value.generate_solution_structure.assert_called_once()
    mock_gemini_client.return_value.generate_summary.assert_not_called()
    mock_gemini_client.return_value.generate_chapters.assert_not_called()

def test_process_video_solution_json(mock_gemini_client, mock_youtube):
    """課題解決モード・JSON形式のテスト"""
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='solution',
        output_format='json'
    )
    assert isinstance(result, dict)
    assert result == MOCK_SOLUTION_JSON_OUTPUT
    mock_gemini_client.return_value.generate_solution_structure.assert_called_once()

def test_process_video_solution_with_prompt(mock_gemini_client, mock_youtube):
    """課題解決モード・プロンプト付きのテスト"""
    prompt = "初心者向けに解説して"
    result = process_video(
        url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        mode='solution',
        prompt=prompt
    )
    assert result == MOCK_SOLUTION_TEXT_OUTPUT # モックは同じ結果を返す
    mock_gemini_client.return_value.generate_solution_structure.assert_called_once_with(
        video_info=MOCK_VIDEO_INFO,
        model='gemini-2.0-flash', # デフォルトモデル
        additional_prompt=prompt
    )

# --- 共通エラーテスト ---

def test_process_video_invalid_url(mock_gemini_client, mock_youtube):
    """無効なURLでのエラーハンドリングをテスト"""
    mock_youtube['validate'].return_value = False
    with pytest.raises(ProcessingError) as excinfo:
        process_video('invalid_url', mode='summary')
    assert '無効なYouTube URL' in str(excinfo.value)
    mock_gemini_client.assert_not_called() # GeminiClient自体が呼ばれないはず

def test_process_video_youtube_error(mock_gemini_client, mock_youtube):
    """YouTube情報取得エラーのハンドリングをテスト"""
    # YouTubeErrorを発生させるように設定
    mock_youtube['get_info'].side_effect = YouTubeError("YouTube error")
    with pytest.raises(ProcessingError) as excinfo:
        process_video('https://www.youtube.com/watch?v=dQw4w9WgXcQ', mode='chapter')
    assert 'YouTube動画の処理中にエラーが発生しました' in str(excinfo.value)
    mock_gemini_client.return_value.generate_chapters.assert_not_called()

def test_process_video_gemini_error_summary(mock_gemini_client, mock_youtube):
    """Gemini APIエラーのハンドリングをテスト (要約モード)"""
    mock_gemini_client.return_value.generate_summary.side_effect = GeminiError("Gemini API error")
    with pytest.raises(ProcessingError) as excinfo:
        process_video('https://www.youtube.com/watch?v=dQw4w9WgXcQ', mode='summary')
    assert 'Gemini APIとの通信中にエラーが発生しました' in str(excinfo.value)

def test_process_video_gemini_error_chapter(mock_gemini_client, mock_youtube):
    """Gemini APIエラーのハンドリングをテスト (チャプターモード)"""
    mock_gemini_client.return_value.generate_chapters.side_effect = GeminiError("Gemini API error")
    with pytest.raises(ProcessingError) as excinfo:
        process_video('https://www.youtube.com/watch?v=dQw4w9WgXcQ', mode='chapter')
    assert 'Gemini APIとの通信中にエラーが発生しました' in str(excinfo.value)

def test_process_video_invalid_mode(mock_gemini_client, mock_youtube):
    """無効なモード指定のテスト"""
    with pytest.raises(ProcessingError) as excinfo:
        process_video('https://www.youtube.com/watch?v=dQw4w9WgXcQ', mode='invalid_mode')
    assert '無効なモード指定' in str(excinfo.value)