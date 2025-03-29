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
from .summarizer import SummarizerError, generate_summary

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
    '--model',
    default=os.getenv('DEFAULT_MODEL', 'gemini-2.0-flash'),
    help='使用するGeminiモデル（デフォルト: gemini-2.0-flash）'
)
@click.option(
    '--length',
    type=click.Choice(['short', 'normal', 'detailed']),
    default=os.getenv('DEFAULT_SUMMARY_LENGTH', 'normal'),
    help='要約の長さ（short/normal/detailed）'
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
    help='出力言語（デフォルト: 日本語）'
)
@click.option(
    '--prompt',
    help='追加のプロンプト（例: "5歳児向けに説明して"）'
)
@click.option(
    '--stream',
    is_flag=True,
    default=False,
    help='ストリーミングモードを有効化（要約をリアルタイムで表示）'
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
    model: str,
    length: str,
    output_format: str,
    lang: str,
    prompt: Optional[str],
    stream: bool,
    debug: bool
) -> None:
    """YouTube動画を要約するCLIツール

    URL: YouTube動画のURL
    """
    # 環境変数の検証 (generate_summary呼び出し前に移動)
    if not os.getenv('GEMINI_API_KEY'):
        click.echo("エラー: GEMINI_API_KEYが設定されていません。.envファイルを確認してください。", err=True)
        sys.exit(1)

    try:
        # デバッグモードの設定
        if debug:
            click.echo("デバッグモード: 有効", err=True)
            # パラメータの表示
            click.echo("パラメータ:", err=True)
            click.echo(f"URL: {url}", err=True)
            click.echo(f"モデル: {model}", err=True)
            click.echo(f"長さ: {length}", err=True)
            click.echo(f"出力形式: {output_format}", err=True)
            click.echo(f"言語: {lang}", err=True)
            click.echo(f"ストリーミング: {stream}", err=True)
            if prompt:
                click.echo(f"追加プロンプト: {prompt}", err=True)

        # ストリーミングモードではJSON出力を無効化
        if stream and output_format == 'json':
            click.echo("警告: ストリーミングモードではJSON出力は利用できません。テキスト形式で出力します。", err=True)
            output_format = 'text'

        if stream:
            # ストリーミングモードでの出力
            click.echo("\n=== 要約生成中 ===\n")
            summary = generate_summary(
                url=url,
                model=model,
                length=length,
                output_format='text',  # ストリーミングではテキストのみ
                lang=lang,
                prompt=prompt,
                stream=True
            )
            click.echo("\n===============\n")
        else:
            # 通常モードでの出力
            with click.progressbar(
                length=4,
                label='要約を生成中...',
                show_pos=True
            ) as progress:
                # 要約の生成
                summary = generate_summary(
                    url=url,
                    model=model,
                    length=length,
                    output_format=output_format,
                    lang=lang,
                    prompt=prompt,
                    stream=False
                )
                progress.update(4)

            # 結果の出力
            if output_format == 'json':
                click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
            else:
                click.echo("\n=== 要約結果 ===\n")
                click.echo(summary)
                click.echo("\n===============\n")

    except SummarizerError as e:
        if debug:
            # デバッグモードの場合は詳細なエラー情報を表示
            click.echo(f"要約エラー: {str(e)}", err=True)
            raise
        else:
            # 通常モードではユーザーフレンドリーなエラーメッセージを表示
            click.echo(f"エラー: {str(e)}", err=True)
            sys.exit(1)
    except Exception as e:
        if debug:
            click.echo(f"予期せぬエラー: {str(e)}", err=True)
            raise
        else:
            click.echo("予期せぬエラーが発生しました。--debugオプションを使用して詳細を確認してください。", err=True)
            sys.exit(1)

if __name__ == '__main__':
    main()