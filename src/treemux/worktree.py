"""Git Worktree関連のユーティリティ"""

import subprocess
from pathlib import Path


def get_git_root(path: Path) -> Path | None:
    """Gitリポジトリのルートを取得

    Args:
        path: 検索開始パス

    Returns:
        Gitルートパス、Gitリポジトリでない場合はNone
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        return None


def get_worktree_name(path: Path) -> str | None:
    """現在のワークツリー名を取得

    Args:
        path: 対象パス

    Returns:
        ワークツリー名（ディレクトリ名）、取得できない場合はNone
    """
    git_root = get_git_root(path)
    if not git_root:
        return None

    return git_root.name


def get_current_branch(path: Path) -> str | None:
    """現在のブランチ名を取得

    Args:
        path: 対象パス

    Returns:
        ブランチ名、取得できない場合はNone
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            check=True,
        )
        branch = result.stdout.strip()
        # detached HEADの場合
        return branch if branch != "HEAD" else None
    except subprocess.CalledProcessError:
        return None


def is_worktree(path: Path) -> bool:
    """パスがワークツリーかどうかを判定

    メインのワーキングツリーではなく、git worktree addで作成された
    ワークツリーかどうかを判定する。

    Args:
        path: 対象パス

    Returns:
        ワークツリーならTrue
    """
    git_path = path / ".git"
    # .gitがファイルの場合はワークツリー
    # 内容は "gitdir: /path/to/.git/worktrees/name" のような形式
    return git_path.is_file()


def is_git_repository(path: Path) -> bool:
    """パスがGitリポジトリ内かどうかを判定

    Args:
        path: 対象パス

    Returns:
        Gitリポジトリ内ならTrue
    """
    return get_git_root(path) is not None


def sanitize_branch_name(branch: str) -> str:
    """ブランチ名をファイル名/プロジェクト名として使用可能な形式に変換

    Args:
        branch: ブランチ名

    Returns:
        サニタイズされた名前
    """
    # スラッシュをハイフンに置換
    sanitized = branch.replace("/", "-")
    # その他の特殊文字を削除
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in "-_")
    return sanitized
