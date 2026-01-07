"""設定ファイルの読み書き"""

from pathlib import Path

from ruamel.yaml import YAML

from treemux.models import ServiceConfig, TreemuxConfig

TREEMUX_DIR = ".treemux"
CONFIG_FILE = "config.yml"


def get_treemux_dir(project_root: Path) -> Path:
    """treemux設定ディレクトリを取得"""
    return project_root / TREEMUX_DIR


def get_config_path(project_root: Path) -> Path:
    """設定ファイルパスを取得"""
    return get_treemux_dir(project_root) / CONFIG_FILE


def load_config(project_root: Path) -> TreemuxConfig | None:
    """設定ファイルを読み込み

    Args:
        project_root: プロジェクトルートパス

    Returns:
        設定オブジェクト、存在しない場合はNone
    """
    config_path = get_config_path(project_root)
    if not config_path.exists():
        return None

    yaml = YAML()
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)

    return TreemuxConfig.model_validate(data)


def save_config(project_root: Path, config: TreemuxConfig) -> Path:
    """設定ファイルを保存

    Args:
        project_root: プロジェクトルートパス
        config: 設定オブジェクト

    Returns:
        保存先パス
    """
    treemux_dir = get_treemux_dir(project_root)
    treemux_dir.mkdir(exist_ok=True)

    config_path = get_config_path(project_root)
    yaml = YAML()
    yaml.default_flow_style = False

    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(mode="json"), f)

    return config_path


def create_default_config(project_name: str) -> TreemuxConfig:
    """デフォルト設定を作成

    Args:
        project_name: プロジェクト名

    Returns:
        デフォルト設定オブジェクト
    """
    return TreemuxConfig(
        project_name=project_name,
        services={
            "web": ServiceConfig(container_port=3000, base_host_port=8000),
            "api": ServiceConfig(container_port=5000, base_host_port=8100),
        },
    )


def config_exists(project_root: Path) -> bool:
    """設定ファイルが存在するか確認"""
    return get_config_path(project_root).exists()
