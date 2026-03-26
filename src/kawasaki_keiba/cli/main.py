"""CLI エントリポイント

Usage:
    kawasaki validate <data_dir>
    kawasaki predict <race_id>
    kawasaki gate <race_id>
    kawasaki video tag <race_id>
    kawasaki paddock observe <race_id>
    kawasaki warmup observe <race_id>
    kawasaki integrate <race_id>
    kawasaki monitor status
    kawasaki monitor roi
    kawasaki log show <race_id>
"""

import click


@click.group()
@click.version_option()
def cli() -> None:
    """川崎競馬 意思決定AIシステム"""
    pass


# --- データ品質 ---

@cli.command()
@click.argument("data_dir", type=click.Path(exists=True))
def validate(data_dir: str) -> None:
    """データ品質チェックを実行する"""
    click.echo(f"Validating data in {data_dir} ...")
    # Phase 2 で実装
    click.echo("[未実装] Phase 2 で実装予定")


# --- Core 予測 ---

@cli.command()
@click.argument("race_id")
@click.option("--popularity-baseline", is_flag=True, help="人気順ベースラインと比較")
def predict(race_id: str, popularity_baseline: bool) -> None:
    """Core モデルで予測を実行する"""
    click.echo(f"Predicting {race_id} ...")
    click.echo("[未実装] Phase 2 で実装予定")


# --- Gate 判定 ---

@cli.command()
@click.argument("race_id")
def gate(race_id: str) -> None:
    """Gate (no-bet/bet) 判定を実行する"""
    click.echo(f"Gate decision for {race_id} ...")
    click.echo("[未実装] Phase 2 で実装予定")


# --- 映像系 ---

@cli.group()
def video() -> None:
    """Race Video System"""
    pass


@video.command()
@click.argument("race_id")
def tag(race_id: str) -> None:
    """レース映像タグを記録する"""
    click.echo(f"Video tagging for {race_id} ...")
    click.echo("[未実装] Phase 3 で実装予定")


@cli.group()
def paddock() -> None:
    """Paddock System"""
    pass


@paddock.command()
@click.argument("race_id")
@click.option("--mode", type=click.Choice(["off", "advisory", "integrated"]), default="off")
def observe(race_id: str, mode: str) -> None:
    """パドック観測を記録する"""
    click.echo(f"Paddock observe {race_id} (mode={mode}) ...")
    click.echo("[未実装] Phase 4 で実装予定")


@cli.group()
def warmup() -> None:
    """Warmup System"""
    pass


@warmup.command("observe")
@click.argument("race_id")
@click.option("--mode", type=click.Choice(["off", "advisory", "integrated"]), default="off")
def warmup_observe(race_id: str, mode: str) -> None:
    """返し馬観測を記録する"""
    click.echo(f"Warmup observe {race_id} (mode={mode}) ...")
    click.echo("[未実装] Phase 4 で実装予定")


# --- 統合 ---

@cli.command()
@click.argument("race_id")
def integrate(race_id: str) -> None:
    """全システムのスコアを統合する"""
    click.echo(f"Integrating {race_id} ...")
    click.echo("[未実装] Phase 3-4 で実装予定")


# --- 監視 ---

@cli.group()
def monitor() -> None:
    """Monitoring System"""
    pass


@monitor.command()
def status() -> None:
    """現在の監視ステータスを表示する"""
    click.echo("[未実装] Phase 2 で実装予定")


@monitor.command()
@click.option("--recent", type=int, default=30, help="直近Nレース")
def roi(recent: int) -> None:
    """ROI を表示する"""
    click.echo(f"ROI (recent {recent} races) ...")
    click.echo("[未実装] Phase 2 で実装予定")


# --- ログ ---

@cli.group()
def log() -> None:
    """判定ログ"""
    pass


@log.command()
@click.argument("race_id")
def show(race_id: str) -> None:
    """判定ログを表示する"""
    click.echo(f"Judgment log for {race_id} ...")
    click.echo("[未実装] Phase 2 で実装予定")
