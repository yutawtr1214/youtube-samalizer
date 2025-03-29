"""
YouTube動画情報取得モジュール
"""
import re
from typing import Dict, Optional
from urllib.parse import parse_qs, urlparse

import requests


class YouTubeError(Exception):
    """YouTube関連の例外クラス"""
    pass


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


def get_video_info(url: str) -> Dict[str, str]:
    """YouTube動画の情報を取得する

    Args:
        url (str): YouTube動画のURL

    Returns:
        Dict[str, str]: 動画情報（タイトル、説明など）

    Raises:
        YouTubeError: 動画情報の取得に失敗した場合
    """
    try:
        video_id = extract_video_id(url)
        
        # YouTube Data APIを使用せずにOEmbedエンドポイントから基本情報を取得
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        response = requests.get(oembed_url)
        response.raise_for_status()
        
        data = response.json()
        return {
            'video_id': video_id,
            'title': data.get('title', ''),
            'author': data.get('author_name', ''),
            'url': url
        }

    except requests.RequestException as e:
        raise YouTubeError(f"動画情報の取得に失敗しました: {str(e)}")
    except ValueError as e:
        raise YouTubeError(f"動画情報の解析に失敗しました: {str(e)}")


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