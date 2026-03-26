"""CLI 雛形: 各サブシステム用グループのみ（処理は未実装）。"""

from __future__ import annotations

import json

import click

from kawasaki_ai.config import AppConfig, SystemModule
from kawasaki_ai.paths import data_layout, suggested_module_paths
from kawasaki_ai.utils.logging import get_logger, setup_logging


@click.group(context_settings={"auto_envvar_prefix": "KAWASAKI_AI"})
@click.option("--log-level", default="INFO", show_default=True, help="ログレベル")
@click.pass_context
def cli(ctx: click.Context, log_level: str) -> None:
    """川崎競馬AIシステム（拡張用土台）。"""
    ctx.ensure_object(dict)
    setup_logging(level=log_level)
    ctx.obj["log"] = get_logger("cli")


@cli.command("config-dump")
def config_dump() -> None:
    """現在の既定 AppConfig を JSON で表示。"""
    cfg = AppConfig()
    click.echo(json.dumps(cfg.model_dump(mode="json"), indent=2, ensure_ascii=False))


@cli.command("paths-dump")
def paths_dump() -> None:
    """データレイアウトとモジュール別推奨パスを表示。"""
    layout = {k: str(v) for k, v in data_layout().items()}
    modules = {m.value: str(p) for m, p in suggested_module_paths().items()}
    click.echo(json.dumps({"data_layout": layout, "module_paths": modules}, indent=2))


def _stub_group(module: SystemModule) -> click.Group:
    @click.group(name=module.value, help=f"{module.name}（未実装・拡張用）")
    def grp() -> None:
        pass

    @grp.command("status")
    def status() -> None:
        click.echo(f"[{module.value}] 未実装（土台のみ）")

    return grp


cli.add_command(_stub_group(SystemModule.CORE))
cli.add_command(_stub_group(SystemModule.GATE))
cli.add_command(_stub_group(SystemModule.RACE_VIDEO), name="race-video")
cli.add_command(_stub_group(SystemModule.PADDOCK))
cli.add_command(_stub_group(SystemModule.WARMUP))
cli.add_command(_stub_group(SystemModule.INTEGRATION))
cli.add_command(_stub_group(SystemModule.MONITORING))


@click.group(name="logging", help="LOGGING（未実装・拡張用）")
def logging_group() -> None:
    pass


@logging_group.command("status")
def logging_status() -> None:
    click.echo("[logging] 未実装（土台のみ）")


cli.add_command(logging_group)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
