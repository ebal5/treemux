# treemux 開発ガイド

## プロジェクト概要

Git Worktree並列開発でdocker composeのポート競合を解決するCLIツール。
ccmanagerと連携し、ccmanagerがworktreeを管理、treemuxがdocker composeのポートを管理する。

## 技術スタック

- **Python**: 3.11+
- **CLI**: typer + rich
- **YAML**: ruamel.yaml（コメント保持）
- **バリデーション**: Pydantic v2
- **パッケージング**: hatchling + uv

## コマンド

```bash
# 依存関係インストール
uv sync

# 開発モードで実行
uv run treemux --help

# テスト実行
uv run pytest

# Lint/Format
uv run ruff check --fix
uv run ruff format

# 型チェック
uv run mypy src/treemux
```

## ディレクトリ構造

```
src/treemux/
├── cli.py       # CLIエントリーポイント（typer app）
├── config.py    # .treemux/config.yml 操作
├── state.py     # .treemux/state.json 操作
├── port.py      # ポート割り当てロジック
├── compose.py   # docker compose操作（subprocess）
├── worktree.py  # git worktree検出
└── models.py    # Pydanticモデル
```

## 設計方針

1. **既存compose.ymlを変更しない**: オーバーライドファイルで対応
2. **状態はJSONで管理**: 人間可読、シンプル
3. **ポートベース分離**: 追加コンポーネント不要
4. **クロスプラットフォーム**: Windows/macOS/Linux対応

## テスト

- `tests/` ディレクトリにpytestテストを配置
- 実際のdockerコマンドを呼ぶテストは `@pytest.mark.integration` でマーク
- モックを使った単体テストを優先

## 設計資料

詳細な設計は `idea/設計計画.md` を参照。
