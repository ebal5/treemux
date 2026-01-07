"""共有テストfixtures"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ruamel.yaml import YAML
from typer.testing import CliRunner

from treemux.models import (
    InstanceInfo,
    ServiceConfig,
    TreemuxConfig,
    TreemuxState,
)

# ============================================================
# Basic Model Fixtures
# ============================================================


@pytest.fixture
def sample_service_config() -> ServiceConfig:
    """サンプルServiceConfigを作成"""
    return ServiceConfig(container_port=3000, base_host_port=8000)


@pytest.fixture
def sample_treemux_config() -> TreemuxConfig:
    """サンプルTreemuxConfig（web/apiサービス）を作成"""
    return TreemuxConfig(
        project_name="test-project",
        services={
            "web": ServiceConfig(container_port=3000, base_host_port=8000),
            "api": ServiceConfig(container_port=5000, base_host_port=8100),
        },
    )


@pytest.fixture
def sample_instance_info() -> InstanceInfo:
    """サンプルInstanceInfoを作成"""
    return InstanceInfo(
        index=0,
        started_at=datetime.now(UTC),
        ports={"web": 8000, "api": 8100},
        worktree_path=Path("/tmp/test-worktree"),
    )


@pytest.fixture
def sample_state_with_instances() -> TreemuxState:
    """複数インスタンスを持つTreemuxStateを作成"""
    now = datetime.now(UTC)
    return TreemuxState(
        instances={
            "feature-a": InstanceInfo(
                index=0,
                started_at=now,
                ports={"web": 8000, "api": 8100},
            ),
            "feature-b": InstanceInfo(
                index=2,
                started_at=now,
                ports={"web": 8002, "api": 8102},
            ),
        }
    )


@pytest.fixture
def empty_state() -> TreemuxState:
    """空のTreemuxStateを作成"""
    return TreemuxState()


# ============================================================
# File System Fixtures (using tmp_path)
# ============================================================


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """一時プロジェクトルートディレクトリを作成"""
    return tmp_path


@pytest.fixture
def project_with_treemux_dir(tmp_path: Path) -> Path:
    """.treemuxディレクトリを持つプロジェクトを作成"""
    treemux_dir = tmp_path / ".treemux"
    treemux_dir.mkdir()
    return tmp_path


@pytest.fixture
def project_with_config(tmp_path: Path, sample_treemux_config: TreemuxConfig) -> Path:
    """.treemux/config.ymlを持つプロジェクトを作成"""
    treemux_dir = tmp_path / ".treemux"
    treemux_dir.mkdir()
    config_path = treemux_dir / "config.yml"

    yaml = YAML()
    yaml.default_flow_style = False
    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(sample_treemux_config.model_dump(mode="json"), f)

    return tmp_path


@pytest.fixture
def project_with_state(
    tmp_path: Path,
    sample_state_with_instances: TreemuxState,
) -> Path:
    """.treemux/state.jsonを持つプロジェクトを作成"""
    treemux_dir = tmp_path / ".treemux"
    treemux_dir.mkdir()
    state_path = treemux_dir / "state.json"

    with state_path.open("w", encoding="utf-8") as f:
        json.dump(
            sample_state_with_instances.model_dump(mode="json"),
            f,
            indent=2,
            default=str,
        )

    return tmp_path


# ============================================================
# CLI Test Fixtures
# ============================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """typer CliRunnerインスタンスを作成"""
    return CliRunner()


@pytest.fixture
def mock_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """カレントワーキングディレクトリをモック"""
    monkeypatch.chdir(tmp_path)
    return tmp_path
