"""
Gemini API連携モジュール
"""
import os
import re # 正規表現モジュールをインポート
from typing import Dict, Optional, Generator, List, Tuple

from google import genai
from google.genai import types

class GeminiError(Exception):
    """Gemini API関連の例外クラス"""
    pass

class GeminiClient:
    """Gemini APIクライアント"""
    _instance = None

    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初期化"""
        if not hasattr(self, 'initialized'):
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise GeminiError("GEMINI_API_KEYが設定されていません")

            # Gemini APIの初期化 (APIキー方式)
            self.client = genai.Client(
                api_key=api_key,
            )
            self.initialized = True

    def _create_summary_contents(self, video_info: Dict[str, str], length: str, additional_prompt: Optional[str] = None) -> list:
        """要約用のコンテンツを生成する (内部ヘルパー)"""
        base_prompt = f"次のYouTube動画を要約してください:\n標題: {video_info['title']}\n作成者: {video_info['author']}"
        length_prompts = {
            'short': '重要なポイントのみを箇条書きで簡潔に要約してください。',
            'normal': '主要なポイントを含む標準的な長さの要約を作成してください。',
            'detailed': '詳細な内容を含む包括的な要約を作成してください。重要な引用や具体例も含めてください。'
        }
        prompt = f"{base_prompt}\n\n{length_prompts[length]}"
        if additional_prompt:
            prompt += f"\n\n追加の要件: {additional_prompt}"

        return [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(file_uri=video_info['url'], mime_type="video/*"),
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]

    def _create_chapter_contents(self, video_info: Dict[str, str], additional_prompt: Optional[str] = None) -> list:
        """チャプター生成用のコンテンツを生成する (内部ヘルパー)"""
        base_prompt = f"""以下のYouTube動画の内容を分析し、主要なトピックや話題の変わり目に基づいてチャプターを生成してください。
各チャプターは必ず以下の形式で出力してください：
[HH:MM:SS] チャプターの簡単な説明

動画タイトル: {video_info['title']}
動画作成者: {video_info['author']}

チャプターリスト:"""
        prompt = base_prompt
        if additional_prompt:
            prompt += f"\n\n追加の指示: {additional_prompt}" # プロンプトインジェクション対策は別途必要

        return [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(file_uri=video_info['url'], mime_type="video/*"),
                    types.Part.from_text(text=prompt),
                ],
            ),
        ]

    def generate_summary(
        self,
        video_info: Dict[str, str],
        model: str = 'gemini-2.0-flash',
        length: str = 'normal',
        additional_prompt: Optional[str] = None,
        stream: bool = False
    ) -> str:
        """動画の要約を生成する"""
        try:
            contents = self._create_summary_contents(video_info, length, additional_prompt)
            generate_config = types.GenerateContentConfig(response_mime_type="text/plain")

            if stream:
                response_text = ""
                for chunk in self.client.models.generate_content_stream(
                    model=model, contents=contents, config=generate_config
                ):
                    response_text += chunk.text
                return response_text
            else:
                response = self.client.models.generate_content(
                    model=model, contents=contents, config=generate_config
                )
                return response.text
        except Exception as e:
            raise GeminiError(f"要約の生成中にエラーが発生しました: {str(e)}")

    def generate_chapters(
        self,
        video_info: Dict[str, str],
        model: str = 'gemini-2.0-flash', # チャプター生成に適したモデルを選ぶ必要あり
        additional_prompt: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """動画のチャプターを生成する"""
        try:
            contents = self._create_chapter_contents(video_info, additional_prompt)
            # チャプター生成は長くなる可能性があるので、トークン上限を増やすか検討
            generate_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
                # max_output_tokens=4096 # 必要に応じて調整
            )

            response = self.client.models.generate_content(
                model=model, contents=contents, config=generate_config
            )

            if not response.text:
                raise GeminiError("チャプター情報の生成に失敗しました。")

            # 生成されたテキストからチャプター情報をパース
            chapters = self._parse_chapters(response.text)
            if not chapters:
                raise GeminiError("生成されたテキストからチャプター情報を抽出できませんでした。形式が不正か、チャプターが見つかりませんでした。")

            return chapters

        except Exception as e:
            raise GeminiError(f"チャプターの生成中にエラーが発生しました: {str(e)}")

    def _parse_chapters(self, text: str) -> List[Tuple[str, str]]:
        """生成されたテキストからチャプター情報を抽出する"""
        # 正規表現で [HH:MM:SS] 説明 の形式を抽出
        # HH, MM, SSはそれぞれ1桁または2桁の数字に対応
        pattern = re.compile(r"\[(\d{1,2}:\d{1,2}:\d{1,2})\]\s*(.+)")
        chapters = []
        lines = text.strip().split('\n')
        for line in lines:
            match = pattern.match(line.strip())
            if match:
                timestamp = match.group(1)
                description = match.group(2).strip()
                # タイムスタンプのフォーマットをHH:MM:SSに正規化 (例: 1:2:3 -> 01:02:03)
                parts = timestamp.split(':')
                try:
                    normalized_timestamp = "{:02d}:{:02d}:{:02d}".format(
                        int(parts[0]), int(parts[1]), int(parts[2])
                    )
                    chapters.append((normalized_timestamp, description))
                except (IndexError, ValueError):
                    # 不正なタイムスタンプ形式は無視
                    continue
        return chapters


    def get_available_models(self) -> list:
        """利用可能なモデルの一覧を取得する"""
        try:
            # 利用可能なモデルをAPIから取得する方が望ましいが、
            # 現状のSDKでは直接的なメソッドがないため、固定リストを使用
            models = [
                "gemini-2.0-flash",
                "gemini-pro",
                "gemini-pro-vision"
            ]
            return models
        except Exception as e:
            raise GeminiError(f"モデル一覧の取得に失敗しました: {str(e)}")