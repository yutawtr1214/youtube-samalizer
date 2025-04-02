"""
Gemini API連携モジュールのテスト
"""
import json
import re
from unittest.mock import Mock, patch

import pytest
from google.genai import types

# テスト対象のクラスと例外をインポート
from src.gemini import GeminiClient, GeminiError, SolutionStructure

# テスト用のモックデータ
MOCK_VIDEO_INFO = {
    'title': 'Test Video',
    'author': 'Test Author',
    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'video_id': 'dQw4w9WgXcQ'
}

# _parse_solution_structure のテスト用データ
PARSE_SOLUTION_VALID_JSON_TEXT = """
```json
{
  "problem": "動画の課題",
  "steps": [
    {
      "timestamp": "0:1:5",
      "description": "ステップ1"
    },
    {
      "timestamp": "00:10:30",
      "description": "ステップ2"
    },
    {
      "timestamp": "1:00:00",
      "description": "ステップ3"
    }
  ]
}
```
"""
PARSE_SOLUTION_EXPECTED_VALID = {
    "problem": "動画の課題",
    "steps": [
        {"timestamp": "00:01:05", "description": "ステップ1"},
        {"timestamp": "00:10:30", "description": "ステップ2"},
        {"timestamp": "01:00:00", "description": "ステップ3"}
    ]
}
PARSE_SOLUTION_INVALID_JSON_TEXT = "これはJSONではありません"
PARSE_SOLUTION_INVALID_STRUCTURE_TEXT = """
```json
{
  "issue": "課題",
  "actions": []
}
```
"""
PARSE_SOLUTION_INVALID_TIMESTAMP_TEXT = """
```json
{
  "problem": "課題",
  "steps": [
    {"timestamp": "abc", "description": "無効なタイムスタンプ"}
  ]
}
```
"""
PARSE_SOLUTION_MISSING_KEY_TEXT = """
```json
{
  "problem": "課題",
  "steps": [
    {"timestamp": "00:00:01"}
  ]
}
```
"""

# generate_solution_structure のテスト用データ
MOCK_GEMINI_RESPONSE_TEXT = PARSE_SOLUTION_VALID_JSON_TEXT # 正常系の応答テキスト

@pytest.fixture(scope="function")
def gemini_client_instance():
    """テストごとに独立したGeminiClientインスタンスを生成"""
    # シングルトンを回避するために毎回新しいインスタンスを作成
    with patch.dict('os.environ', {'GEMINI_API_KEY': 'dummy_key'}):
         # _instanceをリセットして新しいインスタンスを強制生成
        GeminiClient._instance = None
        client = GeminiClient()
        # 実際のAPI呼び出しを防ぐためにモック化
        client.client = Mock()
        yield client
        # テスト終了後にリセット
        GeminiClient._instance = None


# --- _parse_solution_structure のテスト ---

def test_parse_solution_structure_valid(gemini_client_instance):
    """_parse_solution_structure: 正常なJSONテキストのパース"""
    result = gemini_client_instance._parse_solution_structure(PARSE_SOLUTION_VALID_JSON_TEXT)
    assert result == PARSE_SOLUTION_EXPECTED_VALID

def test_parse_solution_structure_no_markdown(gemini_client_instance):
    """_parse_solution_structure: マークダウンなしの正常なJSONテキスト"""
    plain_json = json.dumps(PARSE_SOLUTION_EXPECTED_VALID)
    result = gemini_client_instance._parse_solution_structure(plain_json)
    # タイムスタンプは正規化される前の形式で比較する必要がある場合があるが、
    # このテストケースでは期待値が正規化済みなのでこれでOK
    assert result == PARSE_SOLUTION_EXPECTED_VALID


def test_parse_solution_structure_invalid_json(gemini_client_instance):
    """_parse_solution_structure: 不正なJSON形式"""
    with pytest.raises(GeminiError) as excinfo:
        gemini_client_instance._parse_solution_structure(PARSE_SOLUTION_INVALID_JSON_TEXT)
    assert "JSONパースに失敗しました" in str(excinfo.value)

def test_parse_solution_structure_invalid_structure(gemini_client_instance):
    """_parse_solution_structure: JSON構造が期待と異なる"""
    with pytest.raises(GeminiError) as excinfo:
        gemini_client_instance._parse_solution_structure(PARSE_SOLUTION_INVALID_STRUCTURE_TEXT)
    assert "JSONの基本構造が不正です" in str(excinfo.value)

def test_parse_solution_structure_invalid_timestamp(gemini_client_instance):
    """_parse_solution_structure: 不正なタイムスタンプが含まれる"""
    result = gemini_client_instance._parse_solution_structure(PARSE_SOLUTION_INVALID_TIMESTAMP_TEXT)
    # 不正なタイムスタンプのステップは無視されるため、stepsは空になる
    assert result["problem"] == "課題"
    assert result["steps"] == []

def test_parse_solution_structure_missing_key(gemini_client_instance):
    """_parse_solution_structure: ステップに必要なキーがない"""
    result = gemini_client_instance._parse_solution_structure(PARSE_SOLUTION_MISSING_KEY_TEXT)
    # 必須キーがないステップは無視されるため、stepsは空になる
    assert result["problem"] == "課題"
    assert result["steps"] == []

# --- generate_solution_structure のテスト ---

def test_generate_solution_structure_success(gemini_client_instance):
    """generate_solution_structure: 正常系のテスト"""
    # API応答のモックを設定
    mock_response = Mock()
    mock_response.text = MOCK_GEMINI_RESPONSE_TEXT
    gemini_client_instance.client.models.generate_content.return_value = mock_response

    result = gemini_client_instance.generate_solution_structure(
        video_info=MOCK_VIDEO_INFO,
        model='gemini-pro' # テスト用にモデル指定
    )

    assert result == PARSE_SOLUTION_EXPECTED_VALID
    # generate_contentが適切な引数で呼ばれたか検証
    gemini_client_instance.client.models.generate_content.assert_called_once()
    call_args, call_kwargs = gemini_client_instance.client.models.generate_content.call_args
    assert call_kwargs['model'] == 'gemini-pro'
    # contentsの中身（プロンプト）も検証できるとより良い
    assert isinstance(call_kwargs['contents'], list)
    assert call_kwargs['config'].response_mime_type == "application/json"


def test_generate_solution_structure_api_error(gemini_client_instance):
    """generate_solution_structure: APIエラー発生時のテスト"""
    # API呼び出し時にエラーを発生させる
    gemini_client_instance.client.models.generate_content.side_effect = Exception("API connection failed")

    with pytest.raises(GeminiError) as excinfo:
        gemini_client_instance.generate_solution_structure(video_info=MOCK_VIDEO_INFO)
    assert "課題解決構造の生成中にエラーが発生しました" in str(excinfo.value)
    assert "API connection failed" in str(excinfo.value)


def test_generate_solution_structure_empty_response(gemini_client_instance):
    """generate_solution_structure: API応答が空の場合のテスト"""
    mock_response = Mock()
    mock_response.text = "" # 空の応答
    gemini_client_instance.client.models.generate_content.return_value = mock_response

    with pytest.raises(GeminiError) as excinfo:
        gemini_client_instance.generate_solution_structure(video_info=MOCK_VIDEO_INFO)
    assert "APIからの応答が空です" in str(excinfo.value)


def test_generate_solution_structure_parse_error(gemini_client_instance):
    """generate_solution_structure: 応答のパースに失敗する場合のテスト"""
    mock_response = Mock()
    mock_response.text = PARSE_SOLUTION_INVALID_JSON_TEXT # 不正なJSON
    gemini_client_instance.client.models.generate_content.return_value = mock_response

    with pytest.raises(GeminiError) as excinfo:
        gemini_client_instance.generate_solution_structure(video_info=MOCK_VIDEO_INFO)
    # _parse_solution_structure内で発生したエラーメッセージが含まれるか確認
    assert "JSONパースに失敗しました" in str(excinfo.value)