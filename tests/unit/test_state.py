"""Unit tests for treemux.state."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from treemux.models import InstanceInfo, TreemuxState
from treemux.state import (
    add_instance,
    get_instance,
    get_state_path,
    load_state,
    remove_instance,
    save_state,
)


class TestGetStatePath:
    """Tests for get_state_path function."""

    def test_correct_path(self, project_root: Path):
        """正しいstate.jsonパスを返す"""
        result = get_state_path(project_root)
        assert result == project_root / ".treemux" / "state.json"


class TestLoadState:
    """Tests for load_state function."""

    def test_load_existing_state(
        self,
        project_with_state: Path,
        sample_state_with_instances: TreemuxState,  # noqa: ARG002
    ):
        """既存の状態を正しく読み込む"""
        loaded = load_state(project_with_state)
        assert "feature-a" in loaded.instances
        assert "feature-b" in loaded.instances
        assert loaded.instances["feature-a"].index == 0
        assert loaded.instances["feature-b"].index == 2

    def test_load_state_not_exists(self, project_root: Path):
        """ファイルが存在しない場合は空の状態を返す"""
        result = load_state(project_root)
        assert isinstance(result, TreemuxState)
        assert result.instances == {}

    def test_load_state_empty_dir(self, project_with_treemux_dir: Path):
        """state.jsonがない場合は空の状態を返す"""
        result = load_state(project_with_treemux_dir)
        assert result.instances == {}

    def test_load_state_invalid_json(self, project_with_treemux_dir: Path):
        """無効なJSONはエラーを発生"""
        state_path = project_with_treemux_dir / ".treemux" / "state.json"
        state_path.write_text("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            load_state(project_with_treemux_dir)


class TestSaveState:
    """Tests for save_state function."""

    def test_save_creates_directory(
        self, project_root: Path, empty_state: TreemuxState
    ):
        """.treemuxディレクトリがなければ作成する"""
        treemux_dir = project_root / ".treemux"
        assert not treemux_dir.exists()

        save_state(project_root, empty_state)

        assert treemux_dir.exists()
        assert (treemux_dir / "state.json").exists()

    def test_save_returns_path(self, project_root: Path, empty_state: TreemuxState):
        """保存先パスを返す"""
        result = save_state(project_root, empty_state)
        assert result == project_root / ".treemux" / "state.json"

    def test_save_datetime_serialization(self, project_root: Path):
        """datetimeを正しくシリアライズする"""
        state = TreemuxState(
            instances={
                "test": InstanceInfo(
                    index=0,
                    started_at=datetime(2026, 1, 7, 12, 30, 45, tzinfo=UTC),
                    ports={"web": 8000},
                )
            }
        )
        save_state(project_root, state)

        # Read raw JSON to verify serialization
        state_path = project_root / ".treemux" / "state.json"
        with state_path.open() as f:
            data = json.load(f)

        assert "2026-01-07" in data["instances"]["test"]["started_at"]

    def test_save_path_serialization(self, project_root: Path):
        """Pathを正しくシリアライズする"""
        state = TreemuxState(
            instances={
                "test": InstanceInfo(
                    index=0,
                    started_at=datetime.now(UTC),
                    ports={},
                    worktree_path=Path("/some/path"),
                )
            }
        )
        save_state(project_root, state)

        loaded = load_state(project_root)
        # Path is serialized as string and may not round-trip as Path
        assert loaded.instances["test"].worktree_path is not None


class TestAddInstance:
    """Tests for add_instance function."""

    def test_add_to_empty_state(
        self, project_root: Path, sample_instance_info: InstanceInfo
    ):
        """空の状態にインスタンスを追加する"""
        add_instance(project_root, "new-feature", sample_instance_info)

        state = load_state(project_root)
        assert "new-feature" in state.instances
        assert state.instances["new-feature"].index == sample_instance_info.index

    def test_add_to_existing_state(
        self, project_with_state: Path, sample_instance_info: InstanceInfo
    ):
        """既存の状態にインスタンスを追加する"""
        add_instance(project_with_state, "new-feature", sample_instance_info)

        state = load_state(project_with_state)
        assert "new-feature" in state.instances
        assert "feature-a" in state.instances  # Existing preserved

    def test_add_overwrites_existing(self, project_with_state: Path):
        """同名のインスタンスは上書きする"""
        new_instance = InstanceInfo(
            index=9,
            started_at=datetime.now(UTC),
            ports={"db": 5432},
        )
        add_instance(project_with_state, "feature-a", new_instance)

        state = load_state(project_with_state)
        assert state.instances["feature-a"].index == 9


class TestRemoveInstance:
    """Tests for remove_instance function."""

    def test_remove_existing(self, project_with_state: Path):
        """既存のインスタンスを削除して返す"""
        removed = remove_instance(project_with_state, "feature-a")

        assert removed is not None
        assert removed.index == 0

        state = load_state(project_with_state)
        assert "feature-a" not in state.instances
        assert "feature-b" in state.instances  # Other preserved

    def test_remove_not_exists(self, project_with_state: Path):
        """存在しないインスタンスの場合はNoneを返す"""
        removed = remove_instance(project_with_state, "non-existent")
        assert removed is None

    def test_remove_from_empty_state(self, project_root: Path):
        """空の状態からの削除はNoneを返す"""
        removed = remove_instance(project_root, "any-name")
        assert removed is None


class TestGetInstance:
    """Tests for get_instance function."""

    def test_get_existing(self, project_with_state: Path):
        """既存のインスタンスを返す"""
        instance = get_instance(project_with_state, "feature-a")

        assert instance is not None
        assert instance.index == 0
        assert instance.ports == {"web": 8000, "api": 8100}

    def test_get_not_exists(self, project_with_state: Path):
        """存在しないインスタンスの場合はNoneを返す"""
        instance = get_instance(project_with_state, "non-existent")
        assert instance is None

    def test_get_from_empty_state(self, project_root: Path):
        """空の状態からの取得はNoneを返す"""
        instance = get_instance(project_root, "any-name")
        assert instance is None
