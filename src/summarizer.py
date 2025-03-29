"""
要約エンジンモジュール
"""
from typing import Dict, Optional, Union

from .gemini import GeminiClient, GeminiError
from .youtube import YouTubeError, get_video_info, validate_youtube_url

class SummarizerError(Exception):
    """要約エンジン関連の例外クラス"""
    pass

def generate_summary(
    url: str,
    model: str = 'gemini-2.0-flash',
    length: str = 'normal',
    output_format: str = 'text',
    lang: str = 'ja',
    prompt: Optional[str] = None,
    stream: bool = False
) -> Union[str, Dict]:
    """YouTube動画の要約を生成する

    Args:
        url (str): YouTube動画のURL
        model (str): 使用するGeminiモデル
        length (str): 要約の長さ（short/normal/detailed）
        output_format (str): 出力形式（text/json）
        lang (str): 出力言語
        prompt (Optional[str]): 追加のプロンプト
        stream (bool): ストリーミングモードを使用するかどうか

    Returns:
        Union[str, Dict]: 生成された要約（出力形式に応じて文字列またはdict）

    Raises:
        SummarizerError: 要約生成に失敗した場合
    """
    try:
        # URLの検証
        if not validate_youtube_url(url):
            raise SummarizerError(f"無効なYouTube URL: {url}")

        # 動画情報の取得
        video_info = get_video_info(url)

        # 言語指定がある場合、プロンプトに追加
        if lang and lang != 'ja':
            if prompt:
                prompt = f"以下の要約を{lang}で生成してください。\n{prompt}"
            else:
                prompt = f"以下の要約を{lang}で生成してください。"

        # Gemini APIを使用して要約を生成
        gemini_client = GeminiClient()
        summary = gemini_client.generate_summary(
            video_info=video_info,
            model=model,
            length=length,
            additional_prompt=prompt,
            stream=stream
        )

        # 出力形式に応じて結果を整形
        if output_format == 'json':
            return {
                'video': {
                    'title': video_info['title'],
                    'author': video_info['author'],
                    'url': url,
                    'video_id': video_info['video_id']
                },
                'summary': {
                    'text': summary,
                    'model': model,
                    'length': length,
                    'language': lang
                }
            }
        else:
            return summary

    except YouTubeError as e:
        raise SummarizerError(f"YouTube動画の処理中にエラーが発生しました: {str(e)}")
    except GeminiError as e:
        raise SummarizerError(f"要約の生成中にエラーが発生しました: {str(e)}")
    except Exception as e:
        raise SummarizerError(f"予期せぬエラーが発生しました: {str(e)}")