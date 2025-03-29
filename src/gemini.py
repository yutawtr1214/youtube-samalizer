"""
Gemini API連携モジュール
"""
import os
from typing import Dict, Optional, Generator

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

            # Gemini APIの初期化 (APIキー方式に変更)
            self.client = genai.Client(
                api_key=api_key,
            )
            self.initialized = True

    def create_contents(self, video_info: Dict[str, str], length: str, additional_prompt: Optional[str] = None) -> list:
        """要約用のコンテンツを生成する

        Args:
            video_info (Dict[str, str]): 動画情報
            length (str): 要約の長さ（short/normal/detailed）
            additional_prompt (Optional[str]): 追加のプロンプト

        Returns:
            list: 生成されたコンテンツ
        """
        # 基本プロンプト
        base_prompt = f"次のYouTube動画を要約してください:\n標題: {video_info['title']}\n作成者: {video_info['author']}"

        # 長さに応じたプロンプトの追加
        length_prompts = {
            'short': '重要なポイントのみを箇条書きで簡潔に要約してください。',
            'normal': '主要なポイントを含む標準的な長さの要約を作成してください。',
            'detailed': '詳細な内容を含む包括的な要約を作成してください。重要な引用や具体例も含めてください。'
        }

        prompt = f"{base_prompt}\n\n{length_prompts[length]}"

        # 追加のプロンプトがあれば追加
        if additional_prompt:
            prompt += f"\n\n追加の要件: {additional_prompt}"

        # コンテンツの構築
        return [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_uri(
                        file_uri=video_info['url'],
                        mime_type="video/*"
                    ),
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
        """動画の要約を生成する

        Args:
            video_info (Dict[str, str]): 動画情報
            model (str): 使用するモデル
            length (str): 要約の長さ
            additional_prompt (Optional[str]): 追加のプロンプト
            stream (bool): ストリーミングモードを使用するかどうか

        Returns:
            str: 生成された要約

        Raises:
            GeminiError: 要約生成に失敗した場合
        """
        try:
            # コンテンツを準備
            contents = self.create_contents(video_info, length, additional_prompt)

            # 生成設定
            generate_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
            )

            if stream:
                # ストリーミングモードでの生成
                response_text = ""
                for chunk in self.client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=generate_config,
                ):
                    response_text += chunk.text
                return response_text
            else:
                # 一括生成
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=generate_config,
                )
                return response.text

        except Exception as e:
            raise GeminiError(f"要約の生成中にエラーが発生しました: {str(e)}")

    def get_available_models(self) -> list:
        """利用可能なモデルの一覧を取得する

        Returns:
            list: 利用可能なモデルのリスト
        """
        try:
            # 利用可能なモデルをAPIから取得する方が望ましいが、
            # 現状のSDKでは直接的なメソッドがないため、固定リストを使用
            models = [
                "gemini-2.0-flash",  # 高速な要約生成
                "gemini-pro",        # より詳細な分析
                "gemini-pro-vision"  # 視覚要素も考慮
            ]
            return models
        except Exception as e:
            raise GeminiError(f"モデル一覧の取得に失敗しました: {str(e)}")