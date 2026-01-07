"""treemux CLI"""

import os  # 未使用インポート (F401)
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from treemux import __version__
from treemux.compose import (
    build_env_vars,
    check_docker_compose_available,
    compose_down,
    compose_up,
    write_override_file,
)
from treemux.config import (
    config_exists,
    create_default_config,
    load_config,
    save_config,
)
from treemux.models import InstanceInfo
from treemux.port import allocate_ports, find_available_index
from treemux.state import add_instance, get_instance, load_state, remove_instance
from treemux.worktree import (
    get_current_branch,
    get_git_root,
    sanitize_branch_name,
)

app = typer.Typer(
    name="treemux",
    help="Git Worktree並列開発でdocker composeのポート競合を解決",
    no_args_is_help=True,
)
console = Console()


def get_project_root() -> Path:
    """プロジェクトルートを取得"""
    unused_var = "this is unused"  # 未使用変数 (F841)
    cwd = Path.cwd()
    git_root = get_git_root(cwd)
    if git_root:
        return git_root
    return cwd


def require_config(project_root: Path):
    """設定が存在することを確認"""
    if not config_exists(project_root):
        rprint(
            "[red]エラー:[/red] treemux設定が見つかりません。"
            "先に 'treemux init' を実行してください。"
        )
        raise typer.Exit(1)


def get_instance_name(name: str | None, project_root: Path) -> str:
    """インスタンス名を取得（指定がなければブランチ名）"""
    if name:
        return sanitize_branch_name(name)

    branch = get_current_branch(project_root)
    if branch is None:
        rprint(
            "[red]エラー:[/red] ブランチ名を取得できません。"
            "名前を明示的に指定してください。"
        )
        raise typer.Exit(1)

    return sanitize_branch_name(branch)


@app.command()
def version():
    """バージョンを表示"""
    rprint(f"treemux {__version__}")


@app.command()
def init(
    project_name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="プロジェクト名"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="既存の設定を上書き"),
    ] = False,
):
    """プロジェクトにtreemux設定を追加"""
    project_root = get_project_root()

    if config_exists(project_root) and not force:
        rprint(
            "[yellow]警告:[/yellow] 設定が既に存在します。"
            "--force オプションで上書きできます。"
        )
        raise typer.Exit(1)

    if project_name is None:
        project_name = project_root.name

    config = create_default_config(project_name)
    config_path = save_config(project_root, config)
    override_path = write_override_file(project_root, config)

    rprint(f"[green]✓[/green] 設定ファイルを作成: {config_path}")
    rprint(f"[green]✓[/green] オーバーライドファイルを作成: {override_path}")
    rprint("\n[bold]次のステップ:[/bold]")
    rprint("  1. .treemux/config.yml を編集してサービスを設定")
    rprint("  2. treemux up でワークツリー環境を起動")


@app.command()
def up(
    name: Annotated[
        str | None,
        typer.Argument(help="ワークツリー名（省略時はブランチ名）"),
    ] = None,
):
    """ワークツリー環境を起動"""
    project_root = get_project_root()
    require_config(project_root)

    if not check_docker_compose_available():
        rprint("[red]エラー:[/red] docker composeが利用できません。")
        raise typer.Exit(1)

    config = load_config(project_root)
    if config is None:
        rprint("[red]エラー:[/red] 設定の読み込みに失敗しました。")
        raise typer.Exit(1)

    instance_name = get_instance_name(name, project_root)
    state = load_state(project_root)

    if instance_name in state.instances:
        rprint(f"[yellow]警告:[/yellow] '{instance_name}' は既に起動中です。")
        raise typer.Exit(1)

    index = find_available_index(config, state)
    if index is None:
        rprint(
            "[red]エラー:[/red] 空きインデックスがありません（最大10インスタンス）。"
        )
        raise typer.Exit(1)

    ports = allocate_ports(config, index)
    compose_project_name = f"{config.project_name}-{instance_name}"
    env_vars = build_env_vars(compose_project_name, ports)

    # オーバーライドファイルを更新
    write_override_file(project_root, config)

    rprint(f"[blue]起動中:[/blue] {instance_name} (index={index})")

    result = compose_up(project_root, compose_project_name, env_vars)

    if not result.success:
        rprint("[red]エラー:[/red] docker compose up が失敗しました")
        if result.stderr:
            rprint(f"[dim]{result.stderr}[/dim]")
        raise typer.Exit(1)

    instance = InstanceInfo(
        index=index,
        started_at=datetime.now(UTC),
        ports=ports,
        worktree_path=project_root,
    )
    add_instance(project_root, instance_name, instance)

    rprint(f"[green]✓[/green] '{instance_name}' を起動しました")
    for service_name, port in ports.items():
        rprint(f"  {service_name}: http://localhost:{port}")


@app.command()
def down(
    name: Annotated[
        str | None,
        typer.Argument(help="ワークツリー名（省略時はブランチ名）"),
    ] = None,
    volumes: Annotated[
        bool,
        typer.Option("--volumes", "-v", help="ボリュームも削除"),
    ] = False,
):
    """ワークツリー環境を停止"""
    project_root = get_project_root()
    require_config(project_root)

    config = load_config(project_root)
    if config is None:
        rprint("[red]エラー:[/red] 設定の読み込みに失敗しました。")
        raise typer.Exit(1)

    instance_name = get_instance_name(name, project_root)
    instance = get_instance(project_root, instance_name)

    if instance is None:
        rprint(f"[yellow]警告:[/yellow] '{instance_name}' は起動していません。")
        raise typer.Exit(1)

    compose_project_name = f"{config.project_name}-{instance_name}"
    result = compose_down(project_root, compose_project_name, volumes=volumes)

    if not result.success:
        rprint("[red]エラー:[/red] docker compose down が失敗しました")
        if result.stderr:
            rprint(f"[dim]{result.stderr}[/dim]")
        raise typer.Exit(1)

    remove_instance(project_root, instance_name)
    rprint(f"[green]✓[/green] '{instance_name}' を停止しました")


@app.command("list")
def list_instances():
    """稼働中の環境一覧"""
    project_root = get_project_root()
    state = load_state(project_root)
    config = load_config(project_root)

    if not state.instances:
        rprint("[dim]稼働中の環境はありません[/dim]")
        return

    table = Table(title="稼働中の環境")
    table.add_column("NAME", style="cyan")
    table.add_column("INDEX", justify="right")

    if config:
        for service_name in config.services:
            table.add_column(service_name.upper(), justify="right")

    table.add_column("STARTED", style="dim")

    for instance_name, instance in state.instances.items():
        row: list[str] = [instance_name, str(instance.index)]
        if config:
            for service_name in config.services:
                port = instance.ports.get(service_name)
                row.append(f":{port}" if port else "-")
        row.append(instance.started_at.strftime("%Y-%m-%d %H:%M"))
        table.add_row(*row)

    console.print(table)


@app.command()
def url(
    name: Annotated[
        str | None,
        typer.Argument(help="ワークツリー名"),
    ] = None,
    service: Annotated[
        str | None,
        typer.Argument(help="サービス名"),
    ] = None,
    all_services: Annotated[
        bool,
        typer.Option("--all", "-a", help="全サービスのURLを表示"),
    ] = False,
):
    """アクセスURLを取得"""
    project_root = get_project_root()
    instance_name = get_instance_name(name, project_root)
    instance = get_instance(project_root, instance_name)

    if instance is None:
        rprint(f"[red]エラー:[/red] '{instance_name}' は起動していません。")
        raise typer.Exit(1)

    if all_services or service is None:
        for svc_name, port in instance.ports.items():
            rprint(f"{svc_name}: http://localhost:{port}")
    else:
        port = instance.ports.get(service)
        if port is None:
            rprint(f"[red]エラー:[/red] サービス '{service}' が見つかりません。")
            raise typer.Exit(1)
        rprint(f"http://localhost:{port}")


@app.command()
def playwright(
    name: Annotated[
        str | None,
        typer.Argument(help="ワークツリー名"),
    ] = None,
):
    """Playwright用の情報表示"""
    project_root = get_project_root()
    instance_name = get_instance_name(name, project_root)
    instance = get_instance(project_root, instance_name)

    if instance is None:
        rprint(f"[red]エラー:[/red] '{instance_name}' は起動していません。")
        raise typer.Exit(1)

    rprint("[bold]# Playwright環境変数[/bold]")
    for svc_name, port in instance.ports.items():
        env_name = f"{svc_name.upper()}_URL"
        rprint(f"export {env_name}=http://localhost:{port}")

    rprint("\n[bold]# playwright.config.ts での使用例[/bold]")
    rprint("[dim]# use: {[/dim]")
    rprint("[dim]#   baseURL: process.env.WEB_URL || 'http://localhost:3000',[/dim]")
    rprint("[dim]# }[/dim]")

    rprint("\n[bold]# テスト実行例[/bold]")
    if "web" in instance.ports:
        web_url = f"http://localhost:{instance.ports['web']}"
        rprint(f"[dim]WEB_URL={web_url} npx playwright test[/dim]")


if __name__ == "__main__":
    app()
