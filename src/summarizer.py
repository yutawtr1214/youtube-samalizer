"""
要約・チャプター生成エンジンモジュール
"""
import datetime # タイムスタンプ変換用
from typing import Dict, Optional, Union, List, Tuple, Any # Anyを追加

from .gemini import GeminiClient, GeminiError
from .youtube import YouTubeError, get_video_info, validate_youtube_url

class ProcessingError(Exception):
    """処理中の汎用エラー"""
    pass

def _timestamp_to_seconds(timestamp: str) -> int:
    """HH:MM:SS形式のタイムスタンプを秒に変換する"""
    try:
        h, m, s = map(int, timestamp.split(':'))
        return h * 3600 + m * 60 + s
    except ValueError:
        # 不正な形式の場合は0秒として扱う（エラー処理は要検討）
        return 0

def process_video(
    url: str,
    mode: str = 'summary', # 'summary', 'chapter', or 'solution'
    model: str = 'gemini-2.0-flash',
    length: str = 'normal', # summary mode only
    output_format: str = 'text',
    lang: str = 'ja', # summary mode only (for now)
    prompt: Optional[str] = None,
    stream: bool = False # summary mode only
) -> Union[str, Dict, List[Tuple[str, str]]]:
    """YouTube動画の要約またはチャプターを生成する

    Args:
        url (str): YouTube動画のURL
        mode (str): 処理モード ('summary' または 'chapter')
        model (str): 使用するGeminiモデル
        length (str): 要約の長さ（summaryモードのみ）
        output_format (str): 出力形式（text/json）
        lang (str): 出力言語（summaryモードのみ）
        prompt (Optional[str]): 追加のプロンプト
        stream (bool): ストリーミングモード（summaryモードのみ）

    Returns:
        Union[str, Dict, List[Tuple[str, str]]]: 生成結果

    Raises:
        ProcessingError: 処理に失敗した場合
    """
    try:
        # URLの検証
        if not validate_youtube_url(url):
            raise ProcessingError(f"無効なYouTube URL: {url}")

        # 動画情報の取得
        video_info = get_video_info(url)

        gemini_client = GeminiClient()

        if mode == 'summary':
            # --- 要約処理 ---
            # 言語指定がある場合、プロンプトに追加
            summary_prompt = prompt
            if lang and lang != 'ja':
                 if summary_prompt:
                     summary_prompt = f"以下の要約を{lang}で生成してください。\n{summary_prompt}"
                 else:
                     summary_prompt = f"以下の要約を{lang}で生成してください。"

            summary_text = gemini_client.generate_summary(
                video_info=video_info,
                model=model,
                length=length,
                additional_prompt=summary_prompt,
                stream=stream # ストリーミングはgenerate_summary内で処理
            )

            # ストリーミング時はテキストのみ返す
            if stream:
                return summary_text

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
                        'text': summary_text,
                        'model': model,
                        'length': length,
                        'language': lang
                    }
                }
            else:
                return summary_text

        elif mode == 'chapter':
            # --- チャプター生成処理 ---
            chapters = gemini_client.generate_chapters(
                video_info=video_info,
                model=model, # チャプター生成に適したモデルを選ぶ
                additional_prompt=prompt
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
                    'chapters': [
                        {'timestamp': ts, 'description': desc} for ts, desc in chapters
                    ]
                }
            else:
                # テキスト形式で整形して返す
                chapter_lines = [f"{ts} {desc}" for ts, desc in chapters]
                return "\n".join(chapter_lines)

        elif mode == 'solution':
            # --- 課題解決構造の生成処理 ---
            solution_data: Dict[str, Any] = gemini_client.generate_solution_structure(
                video_info=video_info,
                model=model, # 課題解決に適したモデルを選ぶ (例: gemini-pro)
                additional_prompt=prompt
            )

            # 出力形式に応じて結果を整形
            if output_format == 'json':
                # JSON形式の場合、タイムスタンプからURLを生成して追加
                if 'steps' in solution_data and isinstance(solution_data['steps'], list):
                    for step in solution_data['steps']:
                        if 'timestamp' in step:
                            seconds = _timestamp_to_seconds(step['timestamp'])
                            step['url'] = f"https://www.youtube.com/watch?v={video_info['video_id']}&t={seconds}s"
                return {
                    'video': {
                        'title': video_info['title'],
                        'author': video_info['author'],
                        'url': url,
                        'video_id': video_info['video_id']
                    },
                    'solution': solution_data # 課題定義とステップリストを含む想定
                }
            else:
                # テキスト形式で整形して返す
                output_lines = []
                if 'problem' in solution_data:
                    output_lines.append(f"## 解決する課題\n{solution_data['problem']}\n")
                if 'steps' in solution_data and isinstance(solution_data['steps'], list):
                    output_lines.append("## 解決ステップ")
                    for i, step in enumerate(solution_data['steps']):
                        timestamp = step.get('timestamp', 'N/A')
                        description = step.get('description', '説明なし')
                        seconds = _timestamp_to_seconds(timestamp)
                        step_url = f"https://www.youtube.com/watch?v={video_info['video_id']}&t={seconds}s"
                        output_lines.append(f"{i+1}. [{timestamp}]({step_url}) {description}")
                return "\n".join(output_lines)

        else:
            raise ProcessingError(f"無効なモード指定: {mode}")

    except YouTubeError as e:
        raise ProcessingError(f"YouTube動画の処理中にエラーが発生しました: {str(e)}")
    except GeminiError as e:
        raise ProcessingError(f"Gemini APIとの通信中にエラーが発生しました: {str(e)}")
    except Exception as e:
        # 予期せぬエラーは型名を付けて再raiseする方がデバッグしやすい
        raise ProcessingError(f"予期せぬエラーが発生しました ({type(e).__name__}): {str(e)}")