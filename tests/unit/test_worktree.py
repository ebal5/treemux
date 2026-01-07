"""Unit tests for treemux.worktree."""

from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, patch

import pytest

from treemux.worktree import (
    get_current_branch,
    get_git_root,
    get_worktree_name,
    is_git_repository,
    is_worktree,
    sanitize_branch_name,
)


class TestGetGitRoot:
    """Tests for get_git_root function."""

    @patch("treemux.worktree.subprocess.run")
    def test_success(self, mock_run):
        """成功時はPathを返す"""
        mock_run.return_value = MagicMock(
            stdout="/home/user/project\n",
            returncode=0,
        )

        result = get_git_root(Path("/home/user/project/src"))

        assert result == Path("/home/user/project")
        mock_run.assert_called_once()

    @patch("treemux.worktree.subprocess.run")
    def test_not_repo(self, mock_run):
        """gitリポジトリでない場合はNoneを返す"""
        mock_run.side_effect = CalledProcessError(128, "git")

        result = get_git_root(Path("/tmp/not-a-repo"))

        assert result is None


class TestGetWorktreeName:
    """Tests for get_worktree_name function."""

    @patch("treemux.worktree.get_git_root")
    def test_returns_directory_name(self, mock_git_root):
        """gitルートのディレクトリ名を返す"""
        mock_git_root.return_value = Path("/home/user/my-project")

        result = get_worktree_name(Path("/home/user/my-project/src"))

        assert result == "my-project"

    @patch("treemux.worktree.get_git_root")
    def test_not_repo(self, mock_git_root):
        """gitリポジトリでない場合はNoneを返す"""
        mock_git_root.return_value = None

        result = get_worktree_name(Path("/tmp/not-a-repo"))

        assert result is None


class TestGetCurrentBranch:
    """Tests for get_current_branch function."""

    @patch("treemux.worktree.subprocess.run")
    def test_success(self, mock_run):
        """成功時はブランチ名を返す"""
        mock_run.return_value = MagicMock(
            stdout="feature/my-branch\n",
            returncode=0,
        )

        result = get_current_branch(Path("."))

        assert result == "feature/my-branch"

    @patch("treemux.worktree.subprocess.run")
    def test_detached_head(self, mock_run):
        """detached HEADの場合はNoneを返す"""
        mock_run.return_value = MagicMock(
            stdout="HEAD\n",
            returncode=0,
        )

        result = get_current_branch(Path("."))

        assert result is None

    @patch("treemux.worktree.subprocess.run")
    def test_not_repo(self, mock_run):
        """gitリポジトリでない場合はNoneを返す"""
        mock_run.side_effect = CalledProcessError(128, "git")

        result = get_current_branch(Path("/tmp/not-a-repo"))

        assert result is None


class TestIsWorktree:
    """Tests for is_worktree function."""

    def test_worktree_git_file(self, tmp_path: Path):
        """.gitがファイルの場合はTrue（worktree）"""
        git_file = tmp_path / ".git"
        git_file.write_text("gitdir: /path/to/.git/worktrees/branch-name")

        assert is_worktree(tmp_path) is True

    def test_main_repo_git_directory(self, tmp_path: Path):
        """.gitがディレクトリの場合はFalse（メインリポジトリ）"""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        assert is_worktree(tmp_path) is False

    def test_no_git(self, tmp_path: Path):
        """.gitがない場合はFalse"""
        assert is_worktree(tmp_path) is False


class TestIsGitRepository:
    """Tests for is_git_repository function."""

    @patch("treemux.worktree.get_git_root")
    def test_is_repo(self, mock_git_root):
        """get_git_rootがパスを返す場合はTrue"""
        mock_git_root.return_value = Path("/some/path")

        assert is_git_repository(Path(".")) is True

    @patch("treemux.worktree.get_git_root")
    def test_not_repo(self, mock_git_root):
        """get_git_rootがNoneを返す場合はFalse"""
        mock_git_root.return_value = None

        assert is_git_repository(Path(".")) is False


class TestSanitizeBranchName:
    """Tests for sanitize_branch_name function."""

    def test_slash_to_hyphen(self):
        """/を-に置換する"""
        assert sanitize_branch_name("feature/add-test") == "feature-add-test"

    def test_multiple_slashes(self):
        """複数の/を処理する"""
        assert sanitize_branch_name("a/b/c/d") == "a-b-c-d"

    def test_preserve_alphanumeric(self):
        """英数字を保持する"""
        assert sanitize_branch_name("abc123") == "abc123"

    def test_preserve_hyphen_underscore(self):
        """ハイフンとアンダースコアを保持する"""
        assert sanitize_branch_name("my-branch_name") == "my-branch_name"

    def test_remove_special_chars(self):
        """特殊文字を削除する"""
        assert sanitize_branch_name("feat@#$%^&*()!") == "feat"

    def test_complex_name(self):
        """複雑なブランチ名を処理する"""
        result = sanitize_branch_name("feature/JIRA-123_add-tests@v2")
        assert result == "feature-JIRA-123_add-testsv2"

    def test_empty_string(self):
        """空文字列を処理する"""
        assert sanitize_branch_name("") == ""

    @pytest.mark.parametrize(
        "input_name,expected",
        [
            ("main", "main"),
            ("develop", "develop"),
            ("feature/foo", "feature-foo"),
            ("bugfix/issue-123", "bugfix-issue-123"),
            ("release/v1.0.0", "release-v100"),  # . is removed
            ("hotfix/urgent_fix", "hotfix-urgent_fix"),
        ],
    )
    def test_common_branch_patterns(self, input_name, expected):
        """一般的なブランチ名パターンをテスト"""
        assert sanitize_branch_name(input_name) == expected
