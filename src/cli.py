"""
CLIインターフェースモジュール
"""
import json
import os
import sys
from typing import Optional

import click
from dotenv import load_dotenv

from . import __version__
# SummarizerErrorをProcessingErrorに変更
from .summarizer import ProcessingError, process_video

# 環境変数の読み込み
load_dotenv()

def print_version(ctx: click.Context, param: click.Parameter, value: bool) -> None:
    """バージョン情報を表示"""
    if not value or ctx.resilient_parsing:
        return
    click.echo(f"YouTube-Samalizer version {__version__}")
    ctx.exit()

@click.command()
@click.argument('url')
@click.option(
    '--mode',
    type=click.Choice(['summary', 'chapter', 'solution']),
    default='summary',
    help='実行モード (summary: 要約, chapter: チャプター生成, solution: 課題解決)'
)
@click.option(
    '--model',
    default=os.getenv('DEFAULT_MODEL', 'gemini-2.0-flash'),
    help='使用するGeminiモデル'
)
@click.option(
    '--length',
    type=click.Choice(['short', 'normal', 'detailed']),
    default=os.getenv('DEFAULT_SUMMARY_LENGTH', 'normal'),
    help='要約の長さ（summaryモードのみ）'
)
@click.option(
    '--format',
    'output_format',
    type=click.Choice(['text', 'json']),
    default=os.getenv('DEFAULT_OUTPUT_FORMAT', 'text'),
    help='出力形式（text/json）'
)
@click.option(
    '--lang',
    default=os.getenv('DEFAULT_LANGUAGE', 'ja'),
    help='要約の出力言語（summaryモードのみ、デフォルト: 日本語）'
)
@click.option(
    '--prompt',
    help='追加のプロンプト（例: "5歳児向けに説明して"）'
)
@click.option(
    '--stream',
    is_flag=True,
    default=False,
    help='ストリーミングモードを有効化（summaryモードのテキスト出力のみ）'
)
@click.option(
    '--version',
    is_flag=True,
    callback=print_version,
    expose_value=False,
    is_eager=True,
    help='バージョン情報を表示'
)
@click.option(
    '--debug',
    is_flag=True,
    default=bool(os.getenv('DEBUG_MODE', 'false').lower() == 'true'),
    help='デバッグモードを有効化'
)
def main(
    url: str,
    mode: str,
    model: str,
    length: str,
    output_format: str,
    lang: str,
    prompt: Optional[str],
    stream: bool,
    debug: bool
) -> None:
    """YouTube動画を要約またはチャプター生成するCLIツール

    URL: YouTube動画のURL
    """
    # 環境変数の検証
    if not os.getenv('GEMINI_API_KEY'):
        click.echo("エラー: GEMINI_API_KEYが設定されていません。.envファイルを確認してください。", err=True)
        sys.exit(1)

    try:
        # デバッグモードの設定
        if debug:
            click.echo("デバッグモード: 有効", err=True)
            click.echo("パラメータ:", err=True)
            click.echo(f"  URL: {url}", err=True)
            click.echo(f"  モード: {mode}", err=True)
            click.echo(f"  モデル: {model}", err=True)
            if mode == 'summary':
                click.echo(f"  要約長: {length}", err=True)
                click.echo(f"  言語: {lang}", err=True)
                click.echo(f"  ストリーミング: {stream}", err=True)
            click.echo(f"  出力形式: {output_format}", err=True)
            if prompt:
                click.echo(f"  追加プロンプト: {prompt}", err=True)

        # モードに応じた警告
        if mode == 'chapter' and stream:
            click.echo("警告: チャプターモードではストリーミングはサポートされていません。", err=True)
            stream = False # ストリーミングを無効化
        if mode == 'chapter' and output_format == 'json' and stream:
             click.echo("警告: ストリーミングモードではJSON出力は利用できません。テキスト形式で出力します。", err=True)
             output_format = 'text' # JSONも無効化

        label = "チャプターを生成中..." if mode == 'chapter' else "要約を生成中..."

        if stream and mode == 'summary':
            # 要約のストリーミングモード
            click.echo(f"\n=== {label} ===\n")
            result = process_video(
                url=url, mode=mode, model=model, length=length,
                output_format='text', lang=lang, prompt=prompt, stream=True
            )
            # process_videoがストリームでテキストを返す想定 (要確認/修正)
            # 現状の実装ではgenerate_summaryがテキストを返すので、そのまま表示
            click.echo(result)
            click.echo("\n===============\n")
        else:
            # 通常モード (要約 or チャプター)
            with click.progressbar(length=4, label=label, show_pos=True) as progress:
                result = process_video(
                    url=url, mode=mode, model=model, length=length,
                    output_format=output_format, lang=lang, prompt=prompt, stream=False
                )
                progress.update(4)

            # 結果の出力
            if output_format == 'json':
                click.echo(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                click.echo(f"\n=== {mode.capitalize()} 結果 ===\n")
                click.echo(result)
                click.echo("\n====================\n")

    except ProcessingError as e:
        if debug:
            click.echo(f"処理エラー: {str(e)}", err=True)
            # raise # デバッグ時は元の例外を再raiseするのも有効
        else:
            click.echo(f"エラー: {str(e)}", err=True)
            sys.exit(1)
    except Exception as e:
        if debug:
            click.echo(f"予期せぬエラー ({type(e).__name__}): {str(e)}", err=True)
            raise
        else:
            click.echo("予期せぬエラーが発生しました。--debugオプションを使用して詳細を確認してください。", err=True)
            sys.exit(1)

if __name__ == '__main__':
    main()