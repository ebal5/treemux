"""CLI integration tests using typer.testing.CliRunner."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from treemux import __version__
from treemux.cli import app
from treemux.config import save_config
from treemux.models import InstanceInfo, TreemuxConfig, TreemuxState
from treemux.state import save_state

pytestmark = pytest.mark.integration


class TestVersionCommand:
    """Tests for version command."""

    def test_shows_version(self, cli_runner: CliRunner):
        """バージョン文字列を表示する"""
        result = cli_runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert "treemux" in result.stdout
        assert __version__ in result.stdout


class TestInitCommand:
    """Tests for init command."""

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_creates_config(
        self, _mock_git_root, cli_runner: CliRunner, mock_cwd: Path
    ):
        """設定ファイルとオーバーライドファイルを作成する"""
        result = cli_runner.invoke(app, ["init", "--name", "test-project"])

        assert result.exit_code == 0
        assert (mock_cwd / ".treemux" / "config.yml").exists()
        assert (mock_cwd / "docker-compose.override.treemux.yml").exists()

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_uses_directory_name_when_no_name(
        self, _mock_git_root, cli_runner: CliRunner, mock_cwd: Path
    ):
        """名前が指定されない場合はディレクトリ名を使用する"""
        result = cli_runner.invoke(app, ["init"])

        assert result.exit_code == 0
        assert (mock_cwd / ".treemux" / "config.yml").exists()

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_existing_no_force_fails(
        self, _mock_git_root, cli_runner: CliRunner, mock_cwd: Path
    ):
        """--forceなしで既存設定があるとエラー"""
        # Create existing config
        treemux_dir = mock_cwd / ".treemux"
        treemux_dir.mkdir()
        (treemux_dir / "config.yml").write_text(
            "version: 1\nproject_name: test\nservices: {}"
        )

        result = cli_runner.invoke(app, ["init"])

        assert result.exit_code == 1
        assert "既に存在" in result.stdout

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_force_overwrites(
        self, _mock_git_root, cli_runner: CliRunner, mock_cwd: Path
    ):
        """--forceで上書きする"""
        # Create existing config
        treemux_dir = mock_cwd / ".treemux"
        treemux_dir.mkdir()
        (treemux_dir / "config.yml").write_text(
            "version: 1\nproject_name: old\nservices: {}"
        )

        result = cli_runner.invoke(app, ["init", "--force", "--name", "new-project"])

        assert result.exit_code == 0


class TestUpCommand:
    """Tests for up command."""

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_no_config_fails(self, _mock_git_root, cli_runner: CliRunner):
        """設定がない場合はエラー"""
        result = cli_runner.invoke(app, ["up", "test"])

        assert result.exit_code == 1
        assert "設定が見つかりません" in result.stdout

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.check_docker_compose_available", return_value=False)
    def test_no_docker_fails(
        self,
        _mock_docker,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
        sample_treemux_config: TreemuxConfig,
    ):
        """docker composeが利用できない場合はエラー"""
        save_config(mock_cwd, sample_treemux_config)

        result = cli_runner.invoke(app, ["up", "test"])

        assert result.exit_code == 1
        assert "docker compose" in result.stdout.lower()

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.check_docker_compose_available", return_value=True)
    @patch("treemux.cli.find_available_index", return_value=None)
    def test_no_available_index_fails(
        self,
        _mock_find_index,
        _mock_docker,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
        sample_treemux_config: TreemuxConfig,
    ):
        """空きインデックスがない場合はエラー"""
        save_config(mock_cwd, sample_treemux_config)

        result = cli_runner.invoke(app, ["up", "test"])

        assert result.exit_code == 1
        assert "空きインデックス" in result.stdout

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.check_docker_compose_available", return_value=True)
    def test_already_running_fails(
        self,
        _mock_docker,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
        sample_treemux_config: TreemuxConfig,
    ):
        """既に起動中の場合はエラー"""
        save_config(mock_cwd, sample_treemux_config)
        state = TreemuxState(
            instances={
                "test": InstanceInfo(
                    index=0,
                    started_at=datetime.now(UTC),
                    ports={"web": 8000},
                )
            }
        )
        save_state(mock_cwd, state)

        result = cli_runner.invoke(app, ["up", "test"])

        assert result.exit_code == 1
        assert "既に起動中" in result.stdout


class TestDownCommand:
    """Tests for down command."""

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_no_config_fails(self, _mock_git_root, cli_runner: CliRunner):
        """設定がない場合はエラー"""
        result = cli_runner.invoke(app, ["down", "test"])

        assert result.exit_code == 1

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_not_running_fails(
        self,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
        sample_treemux_config: TreemuxConfig,
    ):
        """インスタンスが起動していない場合はエラー"""
        save_config(mock_cwd, sample_treemux_config)

        result = cli_runner.invoke(app, ["down", "non-existent"])

        assert result.exit_code == 1
        assert "起動していません" in result.stdout


class TestListCommand:
    """Tests for list command."""

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_empty_list(self, _mock_git_root, cli_runner: CliRunner):
        """インスタンスがない場合は空メッセージを表示"""
        result = cli_runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "ありません" in result.stdout

    @patch("treemux.cli.get_git_root", return_value=None)
    def test_with_instances(
        self,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
        sample_treemux_config: TreemuxConfig,
        sample_state_with_instances: TreemuxState,
    ):
        """インスタンスがある場合はテーブルを表示"""
        save_config(mock_cwd, sample_treemux_config)
        save_state(mock_cwd, sample_state_with_instances)

        result = cli_runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "feature-a" in result.stdout
        assert "feature-b" in result.stdout


class TestUrlCommand:
    """Tests for url command."""

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.get_current_branch", return_value="test-branch")
    def test_not_running_fails(
        self, _mock_branch, _mock_git_root, cli_runner: CliRunner
    ):
        """インスタンスが起動していない場合はエラー"""
        result = cli_runner.invoke(app, ["url", "test"])

        assert result.exit_code == 1
        assert "起動していません" in result.stdout

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.get_current_branch", return_value="test")
    def test_shows_urls(
        self,
        _mock_branch,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
    ):
        """起動中インスタンスのURLを表示する"""
        state = TreemuxState(
            instances={
                "test": InstanceInfo(
                    index=0,
                    started_at=datetime.now(UTC),
                    ports={"web": 8000, "api": 8100},
                )
            }
        )
        save_state(mock_cwd, state)

        result = cli_runner.invoke(app, ["url", "test"])

        assert result.exit_code == 0
        assert "8000" in result.stdout
        assert "8100" in result.stdout

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.get_current_branch", return_value="test")
    def test_shows_single_service_url(
        self,
        _mock_branch,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
    ):
        """単一サービスのURLを表示する"""
        state = TreemuxState(
            instances={
                "test": InstanceInfo(
                    index=0,
                    started_at=datetime.now(UTC),
                    ports={"web": 8000, "api": 8100},
                )
            }
        )
        save_state(mock_cwd, state)

        result = cli_runner.invoke(app, ["url", "test", "web"])

        assert result.exit_code == 0
        assert "8000" in result.stdout

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.get_current_branch", return_value="test")
    def test_service_not_found(
        self,
        _mock_branch,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
    ):
        """存在しないサービスの場合はエラー"""
        state = TreemuxState(
            instances={
                "test": InstanceInfo(
                    index=0,
                    started_at=datetime.now(UTC),
                    ports={"web": 8000},
                )
            }
        )
        save_state(mock_cwd, state)

        result = cli_runner.invoke(app, ["url", "test", "nonexistent"])

        assert result.exit_code == 1
        assert "見つかりません" in result.stdout


class TestPlaywrightCommand:
    """Tests for playwright command."""

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.get_current_branch", return_value="test-branch")
    def test_not_running_fails(
        self, _mock_branch, _mock_git_root, cli_runner: CliRunner
    ):
        """インスタンスが起動していない場合はエラー"""
        result = cli_runner.invoke(app, ["playwright", "test"])

        assert result.exit_code == 1

    @patch("treemux.cli.get_git_root", return_value=None)
    @patch("treemux.cli.get_current_branch", return_value="test")
    def test_shows_env_vars(
        self,
        _mock_branch,
        _mock_git_root,
        cli_runner: CliRunner,
        mock_cwd: Path,
    ):
        """環境変数を表示する"""
        state = TreemuxState(
            instances={
                "test": InstanceInfo(
                    index=0,
                    started_at=datetime.now(UTC),
                    ports={"web": 8000},
                )
            }
        )
        save_state(mock_cwd, state)

        result = cli_runner.invoke(app, ["playwright", "test"])

        assert result.exit_code == 0
        assert "export WEB_URL=http://localhost:8000" in result.stdout
