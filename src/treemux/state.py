"""実行時状態の管理"""

import json
from pathlib import Path

from treemux.models import InstanceInfo, TreemuxState

STATE_FILE = "state.json"


def get_state_path(project_root: Path) -> Path:
    """状態ファイルパスを取得"""
    return project_root / ".treemux" / STATE_FILE


def load_state(project_root: Path) -> TreemuxState:
    """状態を読み込み

    Args:
        project_root: プロジェクトルートパス

    Returns:
        状態オブジェクト（存在しなければ空の状態）
    """
    state_path = get_state_path(project_root)
    if not state_path.exists():
        return TreemuxState()

    with state_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return TreemuxState.model_validate(data)


def save_state(project_root: Path, state: TreemuxState) -> Path:
    """状態を保存

    Args:
        project_root: プロジェクトルートパス
        state: 状態オブジェクト

    Returns:
        保存先パス
    """
    state_path = get_state_path(project_root)
    state_path.parent.mkdir(exist_ok=True)

    with state_path.open("w", encoding="utf-8") as f:
        json.dump(
            state.model_dump(mode="json"),
            f,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    return state_path


def add_instance(
    project_root: Path,
    name: str,
    instance: InstanceInfo,
) -> None:
    """インスタンスを追加

    Args:
        project_root: プロジェクトルートパス
        name: インスタンス名
        instance: インスタンス情報
    """
    state = load_state(project_root)
    state.instances[name] = instance
    save_state(project_root, state)


def remove_instance(project_root: Path, name: str) -> InstanceInfo | None:
    """インスタンスを削除

    Args:
        project_root: プロジェクトルートパス
        name: インスタンス名

    Returns:
        削除されたインスタンス情報、存在しない場合はNone
    """
    state = load_state(project_root)
    instance = state.instances.pop(name, None)
    if instance:
        save_state(project_root, state)
    return instance


def get_instance(project_root: Path, name: str) -> InstanceInfo | None:
    """インスタンスを取得

    Args:
        project_root: プロジェクトルートパス
        name: インスタンス名

    Returns:
        インスタンス情報、存在しない場合はNone
    """
    state = load_state(project_root)
    return state.instances.get(name)
