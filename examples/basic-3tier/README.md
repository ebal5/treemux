# treemux サンプル: 3層構成

web + api + db の典型的な3層構成サンプルです。

## サービス構成

| サービス | イメージ | 説明 |
|----------|----------|------|
| web | nginx:alpine | フロントエンド（リバースプロキシ） |
| api | httpbin | APIサーバー（HTTPエコー） |
| db | postgres:16-alpine | データベース |

## 使い方

treemuxはGitルートで設定を管理します。このサンプルを使用するには、ファイルをプロジェクトルートにコピーしてください。

### 0. セットアップ

```bash
# プロジェクトルートで実行
cp examples/basic-3tier/docker-compose.yml .
cp examples/basic-3tier/nginx.conf .
cp -r examples/basic-3tier/.treemux .
```

### 1. 起動

```bash
uv run treemux up
```

### 2. 状態確認

```bash
uv run treemux list
```

### 3. アクセス確認

```bash
# URL確認
uv run treemux url --all

# webサービス確認
curl http://localhost:8000

# apiサービス直接確認
curl http://localhost:8100/get

# web経由でapi確認
curl http://localhost:8000/api/get
```

### 4. 停止

```bash
uv run treemux down -v
```

## ポート割り当て

treemuxはワークツリーごとに異なるポートを割り当てます：

| インデックス | web | api |
|--------------|-----|-----|
| 0 | 8000 | 8100 |
| 1 | 8001 | 8101 |
| 2 | 8002 | 8102 |
| ... | ... | ... |

## Playwright連携

```bash
uv run treemux playwright
```
