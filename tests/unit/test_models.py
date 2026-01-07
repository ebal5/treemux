"""Unit tests for treemux.models."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from treemux.models import (
    ComposeResult,
    InstanceInfo,
    ServiceConfig,
    TreemuxConfig,
    TreemuxState,
)


class TestServiceConfig:
    """Tests for ServiceConfig model."""

    def test_valid_ports(self):
        """有効なポートは受け入れられる"""
        config = ServiceConfig(container_port=3000, base_host_port=8000)
        assert config.container_port == 3000
        assert config.base_host_port == 8000

    def test_container_port_boundary_min(self):
        """container_port=1は有効"""
        config = ServiceConfig(container_port=1, base_host_port=8000)
        assert config.container_port == 1

    def test_container_port_boundary_max(self):
        """container_port=65535は有効"""
        config = ServiceConfig(container_port=65535, base_host_port=8000)
        assert config.container_port == 65535

    def test_container_port_zero_invalid(self):
        """container_port=0はValidationErrorを発生"""
        with pytest.raises(ValidationError):
            ServiceConfig(container_port=0, base_host_port=8000)

    def test_container_port_negative_invalid(self):
        """負のcontainer_portはValidationErrorを発生"""
        with pytest.raises(ValidationError):
            ServiceConfig(container_port=-1, base_host_port=8000)

    def test_container_port_too_large_invalid(self):
        """container_port > 65535はValidationErrorを発生"""
        with pytest.raises(ValidationError):
            ServiceConfig(container_port=65536, base_host_port=8000)

    def test_base_host_port_boundary_min(self):
        """base_host_port=1024は有効"""
        config = ServiceConfig(container_port=3000, base_host_port=1024)
        assert config.base_host_port == 1024

    def test_base_host_port_below_1024_invalid(self):
        """base_host_port < 1024はValidationErrorを発生"""
        with pytest.raises(ValidationError):
            ServiceConfig(container_port=3000, base_host_port=1023)

    def test_base_host_port_too_large_invalid(self):
        """base_host_port > 65535はValidationErrorを発生"""
        with pytest.raises(ValidationError):
            ServiceConfig(container_port=3000, base_host_port=65536)

    def test_base_host_port_overflow_boundary_valid(self):
        """base_host_port=65526は有効（65526+9=65535）"""
        config = ServiceConfig(container_port=3000, base_host_port=65526)
        assert config.base_host_port == 65526

    def test_base_host_port_overflow_invalid(self):
        """base_host_port=65527は無効（65527+9=65536 > 65535）"""
        with pytest.raises(ValidationError) as exc_info:
            ServiceConfig(container_port=3000, base_host_port=65527)
        assert "exceeds 65535" in str(exc_info.value)


class TestInstanceInfo:
    """Tests for InstanceInfo model."""

    def test_valid_index_zero(self):
        """index=0は有効"""
        info = InstanceInfo(
            index=0,
            started_at=datetime.now(UTC),
            ports={"web": 8000},
        )
        assert info.index == 0

    def test_valid_index_nine(self):
        """index=9は有効（最大値）"""
        info = InstanceInfo(
            index=9,
            started_at=datetime.now(UTC),
            ports={},
        )
        assert info.index == 9

    def test_index_negative_invalid(self):
        """負のindexはValidationErrorを発生"""
        with pytest.raises(ValidationError):
            InstanceInfo(
                index=-1,
                started_at=datetime.now(UTC),
                ports={},
            )

    def test_index_ten_invalid(self):
        """index=10はValidationErrorを発生"""
        with pytest.raises(ValidationError):
            InstanceInfo(
                index=10,
                started_at=datetime.now(UTC),
                ports={},
            )

    def test_optional_worktree_path(self):
        """worktree_pathはオプショナル"""
        info = InstanceInfo(
            index=0,
            started_at=datetime.now(UTC),
            ports={},
        )
        assert info.worktree_path is None

        info_with_path = InstanceInfo(
            index=0,
            started_at=datetime.now(UTC),
            ports={},
            worktree_path=Path("/some/path"),
        )
        assert info_with_path.worktree_path == Path("/some/path")


class TestTreemuxState:
    """Tests for TreemuxState model."""

    def test_get_used_indices_empty(self, empty_state: TreemuxState):
        """空のstateは空のsetを返す"""
        assert empty_state.get_used_indices() == set()

    def test_get_used_indices_with_instances(
        self, sample_state_with_instances: TreemuxState
    ):
        """使用中インデックスの正しいsetを返す"""
        used = sample_state_with_instances.get_used_indices()
        assert used == {0, 2}

    def test_get_next_available_index_empty(self, empty_state: TreemuxState):
        """空のstateは0を返す"""
        assert empty_state.get_next_available_index() == 0

    def test_get_next_available_index_finds_gap(self):
        """使用中インデックスの隙間を見つける"""
        state = TreemuxState(
            instances={
                "a": InstanceInfo(index=0, started_at=datetime.now(UTC), ports={}),
                "b": InstanceInfo(index=2, started_at=datetime.now(UTC), ports={}),
            }
        )
        assert state.get_next_available_index() == 1

    def test_get_next_available_index_sequential(self):
        """隙間がない場合は次の番号を返す"""
        state = TreemuxState(
            instances={
                "a": InstanceInfo(index=0, started_at=datetime.now(UTC), ports={}),
                "b": InstanceInfo(index=1, started_at=datetime.now(UTC), ports={}),
            }
        )
        assert state.get_next_available_index() == 2

    def test_get_next_available_index_full_raises(self):
        """10個全て使用中の場合はValueErrorを発生"""
        instances = {}
        for i in range(10):
            instances[f"instance-{i}"] = InstanceInfo(
                index=i, started_at=datetime.now(UTC), ports={}
            )
        state = TreemuxState(instances=instances)

        with pytest.raises(ValueError, match="No available index"):
            state.get_next_available_index()


class TestTreemuxConfig:
    """Tests for TreemuxConfig model."""

    def test_empty_project_name_invalid(self):
        """空のproject_nameはValidationErrorを発生"""
        with pytest.raises(ValidationError):
            TreemuxConfig(project_name="")

    def test_default_services_empty(self):
        """デフォルトのservicesは空のdict"""
        config = TreemuxConfig(project_name="test")
        assert config.services == {}

    def test_default_subdomain_disabled(self):
        """デフォルトのsubdomainは無効"""
        config = TreemuxConfig(project_name="test")
        assert config.subdomain.enabled is False

    # --- project_name validation tests ---

    def test_valid_project_name_alphanumeric(self):
        """英数字のみのproject_nameは有効"""
        config = TreemuxConfig(project_name="myproject123")
        assert config.project_name == "myproject123"

    def test_valid_project_name_with_hyphen(self):
        """ハイフンを含むproject_nameは有効"""
        config = TreemuxConfig(project_name="my-project")
        assert config.project_name == "my-project"

    def test_valid_project_name_with_underscore(self):
        """アンダースコアを含むproject_nameは有効"""
        config = TreemuxConfig(project_name="my_project")
        assert config.project_name == "my_project"

    def test_valid_project_name_mixed(self):
        """ハイフンとアンダースコアを混在させたproject_nameは有効"""
        config = TreemuxConfig(project_name="my-project_123")
        assert config.project_name == "my-project_123"

    def test_valid_project_name_starts_with_number(self):
        """数字開始のproject_nameは有効"""
        config = TreemuxConfig(project_name="123test")
        assert config.project_name == "123test"

    @pytest.mark.parametrize(
        "invalid_name,description",
        [
            ("test/../../../etc", "パストラバーサル（../）"),
            ("test/path", "スラッシュ"),
            ("test\\path", "バックスラッシュ"),
            ("test;rm -rf /", "セミコロン（コマンドインジェクション）"),
            ("test|cat /etc/passwd", "パイプ（コマンドインジェクション）"),
            ("test$HOME", "ドル記号（変数展開）"),
            ("test`id`", "バッククォート（コマンド置換）"),
            ("test&background", "アンパサンド（バックグラウンド実行）"),
            ("test>output", "リダイレクト（>）"),
            ("test<input", "リダイレクト（<）"),
            ("test name", "スペース"),
            ("-test", "ハイフン開始"),
            ("_test", "アンダースコア開始"),
        ],
    )
    def test_dangerous_project_name_rejected(
        self,
        invalid_name: str,
        description: str,  # noqa: ARG002
    ):
        """危険文字を含むproject_nameは拒否される: {description}"""
        with pytest.raises(ValidationError) as exc_info:
            TreemuxConfig(project_name=invalid_name)
        assert "invalid characters" in str(exc_info.value)


class TestComposeResult:
    """Tests for ComposeResult model."""

    def test_success_result(self):
        """成功結果の作成をテスト"""
        result = ComposeResult(
            success=True,
            return_code=0,
            stdout="output",
            stderr="",
            command=["docker", "compose", "up"],
        )
        assert result.success is True
        assert result.return_code == 0

    def test_failure_result(self):
        """失敗結果の作成をテスト"""
        result = ComposeResult(
            success=False,
            return_code=1,
            stderr="error message",
        )
        assert result.success is False
        assert result.return_code == 1
