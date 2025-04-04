"""
YouTube動画情報取得モジュール
"""
import os
import re
from typing import Dict, Optional, Any
from urllib.parse import parse_qs, urlparse

import requests
import isodate  # ISO 8601 duration parsing


class YouTubeError(Exception):
    """YouTube関連の例外クラス"""
    pass


def format_seconds_to_hhmmss(seconds: int) -> str:
    """秒数をHH:MM:SS形式に変換する

    Args:
        seconds (int): 秒数

    Returns:
        str: HH:MM:SS形式の文字列
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def extract_video_id(url: str) -> str:
    """YouTubeのURLからVideo IDを抽出する

    Args:
        url (str): YouTube動画のURL

    Returns:
        str: 動画ID

    Raises:
        YouTubeError: URLが無効な場合
    """
    # URLのパターン
    patterns = [
        r'^https?:\/\/(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'^https?:\/\/(?:www\.)?youtube\.com\/v\/([^&]+)',
        r'^https?:\/\/youtu\.be\/([^&]+)',
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1)

    # URLからクエリパラメータを解析して取得を試みる
    parsed_url = urlparse(url)
    if 'youtube.com' in parsed_url.netloc:
        query_params = parse_qs(parsed_url.query)
        if 'v' in query_params:
            return query_params['v'][0]

    raise YouTubeError(f"無効なYouTube URL: {url}")


def get_video_info(url: str) -> Dict[str, Any]:
    """YouTube動画の情報を取得する

    Args:
        url (str): YouTube動画のURL

    Returns:
        Dict[str, Any]: 動画情報（タイトル、説明、長さなど）

    Raises:
        YouTubeError: 動画情報の取得に失敗した場合
    """
    try:
        video_id = extract_video_id(url)
        
        # まずOEmbedエンドポイントから基本情報を取得
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        oembed_response = requests.get(oembed_url)
        oembed_response.raise_for_status()
        oembed_data = oembed_response.json()
        
        # YouTube Data APIから詳細情報を取得
        # APIキーが設定されていればData APIを使用、なければ代替方法で取得
        api_key = os.getenv('YOUTUBE_API_KEY')
        
        if api_key:
            # YouTube Data APIを使用して詳細情報を取得
            api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=contentDetails,snippet"
            api_response = requests.get(api_url)
            api_response.raise_for_status()
            api_data = api_response.json()
            
            if not api_data.get('items'):
                raise YouTubeError(f"動画が見つかりません: {video_id}")
            
            video_data = api_data['items'][0]
            
            # 動画の長さを解析（ISO 8601形式のdurationから秒数を計算）
            duration_iso = video_data['contentDetails']['duration']
            duration_seconds = int(isodate.parse_duration(duration_iso).total_seconds())
            
            return {
                'video_id': video_id,
                'title': oembed_data.get('title', video_data['snippet'].get('title', '')),
                'author': oembed_data.get('author_name', video_data['snippet'].get('channelTitle', '')),
                'url': url,
                'duration_seconds': duration_seconds,
                'duration_text': format_seconds_to_hhmmss(duration_seconds)
            }
        
        # YouTube Data APIが利用できない場合は代替方法で取得
        # この場合、動画の長さ情報は正確でない可能性がある
        else:
            # HTMLページをスクレイピングして動画長を推定する方法もあるが、
            # ここでは単純に基本情報のみを返す
            return {
                'video_id': video_id,
                'title': oembed_data.get('title', ''),
                'author': oembed_data.get('author_name', ''),
                'url': url,
                'duration_seconds': 0,  # 正確な長さ不明
                'duration_text': '00:00:00'  # 正確な長さ不明
            }

    except requests.RequestException as e:
        raise YouTubeError(f"動画情報の取得に失敗しました: {str(e)}")
    except ValueError as e:
        raise YouTubeError(f"動画情報の解析に失敗しました: {str(e)}")
    except Exception as e:
        raise YouTubeError(f"予期せぬエラーが発生しました: {str(e)}")


def validate_youtube_url(url: str) -> bool:
    """YouTube URLが有効かどうかを検証する

    Args:
        url (str): 検証するURL

    Returns:
        bool: URLが有効な場合はTrue
    """
    try:
        extract_video_id(url)
        return True
    except YouTubeError:
        return False


def is_video_available(url: str) -> bool:
    """動画が視聴可能かどうかを確認する

    Args:
        url (str): YouTube動画のURL

    Returns:
        bool: 動画が視聴可能な場合はTrue
    """
    try:
        video_info = get_video_info(url)
        return bool(video_info.get('title'))
    except YouTubeError:
        return False