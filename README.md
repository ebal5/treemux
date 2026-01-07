# treemux

Git Worktree並列開発でdocker composeのポート競合を解決するCLIツール。

## 概要

複数のGit Worktreeで同時に開発を行う際、docker composeが固定ポートを使用していると、複数のワークツリーで同時にコンテナを起動できません。treemuxは各ワークツリーに異なるポートを自動で割り当て、この問題を解決します。

## インストール

```bash
# uvxで実行（推奨）
uvx treemux --help

# または pip でインストール
pip install treemux
```

## 使い方

### 初期設定

```bash
cd your-project
treemux init
```

`.treemux/config.yml` が作成されます。サービスのポート設定を編集してください。

### 環境の起動

```bash
# 現在のブランチ名で起動
treemux up

# 名前を指定して起動
treemux up feature-branch
```

### 環境の停止

```bash
treemux down
```

### 稼働中の環境一覧

```bash
treemux list
```

### URLの取得

```bash
# 全サービスのURL
treemux url

# 特定のサービス
treemux url feature-branch web
```

### Playwright用情報

```bash
treemux playwright
```

## 設定ファイル

`.treemux/config.yml`:

```yaml
version: "1"
project_name: my-project
services:
  web:
    container_port: 3000
    base_host_port: 8000
  api:
    container_port: 5000
    base_host_port: 8100
```

## ライセンス

MIT
