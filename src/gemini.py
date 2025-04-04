"""
Gemini API連携モジュール
"""
import os
import re # 正規表現モジュールをインポート
from typing import Dict, Optional, Generator, List, Tuple

import json # JSONパース用
from typing import Dict, Optional, Generator, List, Tuple, Any # Anyを追加

from google import genai
from google.genai import types

class GeminiError(Exception):
    """Gemini API関連の例外クラス"""
    pass

# 課題解決構造の型定義 (仮)
SolutionStructure = Dict[str, Any] # 例: {"problem": "...", "steps": [{"timestamp": "...", "description": "..."}, ...]}

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

    def _create_chapter_contents(self, video_info: Dict[str, Any], additional_prompt: Optional[str] = None) -> list:
        """チャプター生成用のコンテンツを生成する (内部ヘルパー)"""
        # 動画の長さ情報を取得（API経由で取得できた場合のみ）
        duration_info = ""
        if 'duration_seconds' in video_info and video_info['duration_seconds'] > 0:
            duration_text = video_info.get('duration_text', '00:00:00')
            duration_seconds = video_info.get('duration_seconds', 0)
            duration_info = f"""
動画の長さ: {duration_text} ({duration_seconds}秒)"""

        base_prompt = f"""以下のYouTube動画の内容を分析し、主要なトピックや話題の変わり目に基づいてチャプターを生成してください。
各チャプターは必ず以下の形式で出力してください：
[HH:MM:SS] チャプターの簡単な説明

動画タイトル: {video_info['title']}
動画作成者: {video_info['author']}{duration_info}

重要: チャプターのタイムスタンプは動画内の実際の時間に合わせてください。
最初のチャプターは [00:00:00] から始め、最後のチャプターは動画の終了時間を超えないようにしてください。
各チャプターは動画内の実際の内容の変わり目に対応させてください。

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

    def _create_solution_contents(self, video_info: Dict[str, Any], additional_prompt: Optional[str] = None) -> list:
        """課題解決構造抽出用のコンテンツを生成する (内部ヘルパー) - JSON出力試行"""
        # 動画の長さ情報を取得（API経由で取得できた場合のみ）
        duration_info = ""
        if 'duration_seconds' in video_info and video_info['duration_seconds'] > 0:
            duration_text = video_info.get('duration_text', '00:00:00')
            duration_seconds = video_info.get('duration_seconds', 0)
            duration_info = f"""
動画の長さ: {duration_text} ({duration_seconds}秒)"""

        base_prompt = f"""以下のYouTube動画の内容を分析し、動画全体で解決しようとしている「課題」と、その課題を解決するための「ステップ」を抽出してください。
出力は必ず以下のJSON形式に従ってください。

```json
{{
  "problem": "動画全体で解決しようとしている課題の説明（簡潔に）",
  "steps": [
    {{
      "timestamp": "HH:MM:SS",
      "description": "このステップでの具体的な解決行動や説明"
    }},
    // ... 他のステップ
  ]
}}
```

動画タイトル: {video_info['title']}
動画作成者: {video_info['author']}{duration_info}

重要: ステップのタイムスタンプは動画内の実際の時間に合わせてください。
最初のステップは 00:00:00 から始まる必要はありませんが、全てのタイムスタンプは動画の長さ内に収まるようにしてください。
必ず動画内の実際の内容に対応するタイムスタンプを使用してください。

分析結果のJSON:"""
        prompt = base_prompt
        if additional_prompt:
            prompt += f"\n\n追加の指示: {additional_prompt}"

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
        video_info: Dict[str, Any],
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

            # タイムスタンプの検証（動画の長さ情報がある場合）
            if 'duration_seconds' in video_info and video_info['duration_seconds'] > 0:
                video_duration = video_info['duration_seconds']
                validated_chapters = []
                
                for timestamp, description in chapters:
                    # タイムスタンプを秒数に変換
                    h, m, s = map(int, timestamp.split(':'))
                    timestamp_seconds = h * 3600 + m * 60 + s
                    
                    # 動画の長さを超えていないか確認
                    if timestamp_seconds <= video_duration:
                        validated_chapters.append((timestamp, description))
                    else:
                        # ログ出力あるいは警告（開発者向け）
                        print(f"警告: タイムスタンプ {timestamp} が動画長 {video_info['duration_text']} を超えています。無視します。")
                
                if validated_chapters:
                    return validated_chapters
                else:
                    # 全てのチャプターが無効な場合は元のチャプターを返す
                    # エラーメッセージをログに出力
                    print("警告: 全てのチャプターのタイムスタンプが動画の長さを超えています。検証をスキップします。")
                    return chapters
            
            return chapters

        except Exception as e:
            raise GeminiError(f"チャプターの生成中にエラーが発生しました: {str(e)}")

    def generate_solution_structure(
        self,
        video_info: Dict[str, Any],
        model: str = 'gemini-pro', # 課題解決にはより高性能なモデルを推奨
        additional_prompt: Optional[str] = None,
    ) -> SolutionStructure:
        """動画の課題解決構造を生成する"""
        try:
            contents = self._create_solution_contents(video_info, additional_prompt)
            # JSONモードを試す (モデルがサポートしている場合)
            # 注意: モデルによってはJSONモードが利用できない、または挙動が異なる可能性あり
            generate_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                # max_output_tokens=4096 # 必要に応じて調整
            )

            response = self.client.models.generate_content(
                model=model, contents=contents, config=generate_config
            )

            if not response.text: # JSONモードでもtextに結果が入る場合がある
                 raise GeminiError("課題解決構造の生成に失敗しました。APIからの応答が空です。")

            # 生成されたJSONテキストから課題解決構造をパース
            solution_data = self._parse_solution_structure(response.text)
            if not solution_data or 'problem' not in solution_data or 'steps' not in solution_data:
                 raise GeminiError("生成された応答から課題解決構造を抽出できませんでした。形式が不正か、構造が見つかりませんでした。")

            # タイムスタンプの検証（動画の長さ情報がある場合）
            if 'duration_seconds' in video_info and video_info['duration_seconds'] > 0 and 'steps' in solution_data:
                video_duration = video_info['duration_seconds']
                validated_steps = []
                
                for step in solution_data['steps']:
                    if 'timestamp' in step:
                        # タイムスタンプを秒数に変換
                        timestamp = step['timestamp']
                        h, m, s = map(int, timestamp.split(':'))
                        timestamp_seconds = h * 3600 + m * 60 + s
                        
                        # 動画の長さを超えていないか確認
                        if timestamp_seconds <= video_duration:
                            validated_steps.append(step)
                        else:
                            # ログ出力あるいは警告（開発者向け）
                            print(f"警告: ステップのタイムスタンプ {timestamp} が動画長 {video_info['duration_text']} を超えています。無視します。")
                
                if validated_steps:
                    solution_data['steps'] = validated_steps
                else:
                    # 全てのステップが無効な場合はログに警告を出力
                    print("警告: 全てのステップのタイムスタンプが動画の長さを超えています。検証をスキップします。")
            
            return solution_data

        except Exception as e:
            # JSONモード失敗時のフォールバックとしてテキストモードで再試行するなども検討可能
            raise GeminiError(f"課題解決構造の生成中にエラーが発生しました: {str(e)}")

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

    def _parse_solution_structure(self, text: str) -> SolutionStructure:
        """生成されたJSONテキストから課題解決構造を抽出・検証する"""
        try:
            # JSON文字列をパース
            # API応答が ```json ... ``` のようなマークダウン形式で返る場合があるため、
            # JSON部分のみを抽出する前処理を行う
            match = re.search(r"```json\s*([\s\S]+?)\s*```", text)
            if match:
                json_text = match.group(1)
            else:
                # マークダウン形式でない場合は、そのままパース試行
                json_text = text

            data = json.loads(json_text)

            # 基本的な構造の検証
            if not isinstance(data, dict) or 'problem' not in data or 'steps' not in data or not isinstance(data['steps'], list):
                raise ValueError("JSONの基本構造が不正です ('problem' または 'steps' が存在しないか、'steps'がリストではありません)")

            # ステップ内のタイムスタンプを正規化
            validated_steps = []
            for step in data['steps']:
                if not isinstance(step, dict) or 'timestamp' not in step or 'description' not in step:
                    # 必須キーがないステップはスキップ（またはエラーにするか検討）
                    continue

                timestamp = step['timestamp']
                parts = timestamp.split(':')
                try:
                    normalized_timestamp = "{:02d}:{:02d}:{:02d}".format(
                        int(parts[0]), int(parts[1]), int(parts[2])
                    )
                    step['timestamp'] = normalized_timestamp # 正規化したタイムスタンプで上書き
                    validated_steps.append(step)
                except (IndexError, ValueError):
                    # 不正なタイムスタンプ形式のステップはスキップ
                    continue

            data['steps'] = validated_steps # 検証・正規化済みのステップリストで上書き
            return data

        except json.JSONDecodeError as e:
            raise GeminiError(f"課題解決構造のJSONパースに失敗しました: {str(e)}\n応答テキスト: {text}")
        except ValueError as e:
            raise GeminiError(f"抽出された課題解決構造の検証に失敗しました: {str(e)}\n応答テキスト: {text}")
        except Exception as e:
            raise GeminiError(f"課題解決構造の解析中に予期せぬエラーが発生しました: {str(e)}\n応答テキスト: {text}")


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