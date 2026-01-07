"""Unit tests for treemux.config."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.scanner import ScannerError

from treemux.config import (
    config_exists,
    create_default_config,
    get_config_path,
    get_treemux_dir,
    load_config,
    save_config,
)
from treemux.models import ServiceConfig, TreemuxConfig


class TestPathHelpers:
    """Tests for path helper functions."""

    def test_get_treemux_dir(self, project_root: Path):
        """.treemuxサブディレクトリを返す"""
        result = get_treemux_dir(project_root)
        assert result == project_root / ".treemux"

    def test_get_config_path(self, project_root: Path):
        """正しいconfig.ymlパスを返す"""
        result = get_config_path(project_root)
        assert result == project_root / ".treemux" / "config.yml"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_existing_config(
        self, project_with_config: Path, sample_treemux_config: TreemuxConfig
    ):
        """既存の設定を正しく読み込む"""
        loaded = load_config(project_with_config)
        assert loaded is not None
        assert loaded.project_name == sample_treemux_config.project_name
        assert len(loaded.services) == len(sample_treemux_config.services)

    def test_load_config_not_exists(self, project_root: Path):
        """設定が存在しない場合はNoneを返す"""
        result = load_config(project_root)
        assert result is None

    def test_load_config_empty_dir(self, project_with_treemux_dir: Path):
        """.treemuxが存在してもconfig.ymlがなければNoneを返す"""
        result = load_config(project_with_treemux_dir)
        assert result is None

    def test_load_config_invalid_yaml(self, project_with_treemux_dir: Path):
        """無効なYAMLはエラーを発生"""
        config_path = project_with_treemux_dir / ".treemux" / "config.yml"
        config_path.write_text("invalid: yaml: content: [")

        with pytest.raises(ScannerError):
            load_config(project_with_treemux_dir)

    def test_load_config_missing_required_field(self, project_with_treemux_dir: Path):
        """必須フィールドが欠けていればバリデーションエラー"""
        config_path = project_with_treemux_dir / ".treemux" / "config.yml"
        yaml = YAML()
        with config_path.open("w") as f:
            yaml.dump({"version": "1", "services": {}}, f)  # Missing project_name

        with pytest.raises(ValidationError):
            load_config(project_with_treemux_dir)


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_creates_directory(
        self, project_root: Path, sample_treemux_config: TreemuxConfig
    ):
        """.treemuxディレクトリがなければ作成する"""
        treemux_dir = project_root / ".treemux"
        assert not treemux_dir.exists()

        save_config(project_root, sample_treemux_config)

        assert treemux_dir.exists()
        assert (treemux_dir / "config.yml").exists()

    def test_save_overwrites_existing(
        self,
        project_with_config: Path,
        sample_treemux_config: TreemuxConfig,  # noqa: ARG002
    ):
        """既存の設定を上書きする"""
        new_config = TreemuxConfig(
            project_name="new-project-name",
            services={"db": ServiceConfig(container_port=5432, base_host_port=5432)},
        )

        save_config(project_with_config, new_config)
        loaded = load_config(project_with_config)

        assert loaded is not None
        assert loaded.project_name == "new-project-name"
        assert "db" in loaded.services

    def test_save_returns_path(
        self, project_root: Path, sample_treemux_config: TreemuxConfig
    ):
        """保存先パスを返す"""
        result = save_config(project_root, sample_treemux_config)
        assert result == project_root / ".treemux" / "config.yml"
        assert result.exists()

    def test_save_preserves_all_fields(
        self, project_root: Path, sample_treemux_config: TreemuxConfig
    ):
        """ラウンドトリップ後も全フィールドを保持"""
        save_config(project_root, sample_treemux_config)
        loaded = load_config(project_root)

        assert loaded is not None
        assert loaded.project_name == sample_treemux_config.project_name
        assert loaded.version == sample_treemux_config.version
        for name, svc in sample_treemux_config.services.items():
            assert name in loaded.services
            assert loaded.services[name].container_port == svc.container_port
            assert loaded.services[name].base_host_port == svc.base_host_port


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""

    def test_default_config_structure(self):
        """デフォルトサービスを含む設定を作成"""
        config = create_default_config("my-project")

        assert config.project_name == "my-project"
        assert config.version == "1"
        assert "web" in config.services
        assert "api" in config.services

    def test_default_web_service(self):
        """デフォルトのwebサービスが正しいポートを持つ"""
        config = create_default_config("test")
        web = config.services["web"]

        assert web.container_port == 3000
        assert web.base_host_port == 8000

    def test_default_api_service(self):
        """デフォルトのapiサービスが正しいポートを持つ"""
        config = create_default_config("test")
        api = config.services["api"]

        assert api.container_port == 5000
        assert api.base_host_port == 8100


class TestConfigExists:
    """Tests for config_exists function."""

    def test_exists_true(self, project_with_config: Path):
        """設定が存在する場合はTrueを返す"""
        assert config_exists(project_with_config) is True

    def test_exists_false_no_dir(self, project_root: Path):
        """.treemuxディレクトリがない場合はFalseを返す"""
        assert config_exists(project_root) is False

    def test_exists_false_empty_dir(self, project_with_treemux_dir: Path):
        """.treemuxがあってもconfig.ymlがなければFalseを返す"""
        assert config_exists(project_with_treemux_dir) is False
