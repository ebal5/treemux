---
tags:
  - research/approved
  - priority/high
  - research/technical
  - docker
  - docker-compose
  - networking
created_at: 2026-01-07
updated_at: 2026-01-07
---

# docker compose複数インスタンス同時実行アプローチ調査

## 調査目的

docker composeで固定ポートを使用しているプロジェクトで、複数インスタンスを同時実行するためのアプローチを比較検討。

---

## 1. 仮想化を使わないアプローチ

### 1.1 環境変数によるポート動的割り当て

```yaml
ports:
  - "${HOST_PORT:-8080}:${CONTAINER_PORT:-3000}"
```

| 評価項目 | 評価 |
|---------|------|
| 実装の簡潔さ | ✅ 高い |
| 管理の複雑さ | ⚠️ 手動管理必要 |
| スケーラビリティ | ⚠️ 中程度 |

**メリット**:
- 実装が簡潔で最小限の設定
- 単一ホストでの開発環境に最適
- .envファイルで設定管理が容易

**デメリット**:
- ポート番号を手動で管理する必要
- CI/CDでポート競合の管理が複雑
- 設定ミスで容易にポート衝突

---

### 1.2 docker network 分離

```yaml
networks:
  app1:
    driver: bridge
  app2:
    driver: bridge
```

| 評価項目 | 評価 |
|---------|------|
| 隔離度 | ✅ 高い |
| 設定の複雑さ | ⚠️ 中程度 |
| ポート競合対策 | ❌ 別途必要 |

**メリット**:
- インスタンス間を完全に分離
- 内部通信時にポート公開が不要
- セキュリティが高い

**デメリット**:
- インスタンス間通信が必要な場合は外部ネットワークが必須
- 設定が複雑化する傾向
- ホストからのアクセスには別途ポート設定必要

---

### 1.3 Traefik/NGINX リバースプロキシ

#### Traefik設定例
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.app.rule=Host(`instance1.local`)"
```

#### NGINX設定例
```nginx
upstream backend {
  server app:5000;
  server app:5000;
}
```

| 評価項目 | 評価 |
|---------|------|
| ポート効率 | ✅ 1ポートで複数インスタンス |
| 動的スケーリング | ✅ 対応 |
| 追加コンポーネント | ⚠️ 必要 |

**メリット**:
- ホストポート1つで複数インスタンスを管理
- 自動ロードバランシング
- 動的スケーリングに対応
- Traefikは SSL/TLS証明書自動化

**デメリット**:
- 追加コンポーネント（リバースプロキシ）が必須
- 設定が複雑化
- レイテンシが増加（リバースプロキシ経由）

---

### 1.4 docker compose --project-name 活用

```bash
docker compose --project-name app-instance-1 up
docker compose --project-name app-instance-2 up
```

| 評価項目 | 評価 |
|---------|------|
| 完全隔離 | ✅ ネットワーク・ボリューム分離 |
| 設定の簡潔さ | ✅ 高い |
| ポート管理 | ⚠️ 明示的指定必要 |

**メリット**:
- 異なるポートで独立実行が容易
- プロジェクト完全隔離（ボリューム、ネットワーク、コンテナ）
- 本番環境に近い構成テストが可能

**デメリット**:
- インスタンス間通信時に外部ネットワーク設定が必須
- 各インスタンスで異なるポートを明示的に指定
- 大規模スケーリングには手動が多い

---

## 2. 仮想化を使うアプローチ

### 2.1 Firecracker 軽量VM

**特徴**:
- 125msでVM起動（docker runより遅い）
- メモリoverhead: <5MB/VM
- 同一ホストで4000+ VM実行可能

| 評価項目 | 評価 |
|---------|------|
| セキュリティ隔離 | ✅ VM レベル |
| 起動速度 | ⚠️ docker より遅い |
| セットアップ | ❌ 複雑 |

**メリット**:
- dockerより強力なセキュリティ隔離
- リソース制限が容易（VM単位）
- オーバーサブスクリプション対応

**デメリット**:
- dockerより起動が遅い（数百ms）
- セットアップが複雑（/dev/kvm, /dev/net/tun必須）
- docker compose統合はIgniteかfirecracker-in-dockerのみ
- **Windows非対応**

---

### 2.2 各VMでdocker compose独立実行

| 評価項目 | 評価 |
|---------|------|
| 隔離度 | ✅ 完全 |
| リソース効率 | ❌ 低い |
| 管理負荷 | ❌ 高い |

**メリット**:
- インスタンス間の完全隔離
- 異なるOS/バージョンでのテスト可能
- ネットワーク設定が明確

**デメリット**:
- リソース効率が低い（VMごとのoverhead）
- スケーリングが困難
- 管理負荷が高い

---

## 3. ネットワークドライバの選択

| ドライバ | 用途 | ポート競合対策 | 隔離度 | マルチホスト対応 |
|---------|------|-------------|------|-----------------|
| **Bridge** | 単一ホスト開発 | リバースプロキシ必須 | 中程度 | ✗ |
| **Overlay** | Docker Swarm/マルチホスト | 自動 (routing mesh) | 高 | ✓ |
| **Host** | 高パフォーマンス | ✗（ポート共有） | 低 | N/A |

---

## 4. 推奨アプローチ（用途別）

### 開発環境（単一ホスト）

```yaml
# 推奨: --project-name + 環境変数
# 理由: 設定簡潔、完全隔離、追加コンポーネント不要
```

```bash
# 使用例
GWT_WEB_PORT=8001 docker compose --project-name myapp-wt1 up
GWT_WEB_PORT=8002 docker compose --project-name myapp-wt2 up
```

### テスト環境（複数インスタンス隔離テスト）

```bash
# 推奨: --project-name + 環境変数
# 理由: 完全隔離、ポート管理が容易
```

### 本番環境（マルチホスト）

```yaml
# 推奨: Docker Swarm + Overlay ネットワーク
# 理由: 自動ロードバランシング、マルチホスト対応、routing mesh
```

### セキュリティ重視

```yaml
# 推奨: Firecracker MicroVM（Linux環境のみ）
# 理由: VMレベルの隔離、リソース制限が厳格
```

---

## 5. 本プロジェクトでの採用アプローチ

**採用**: `--project-name + 環境変数 + オーバーライドファイル`

### 理由
1. 追加コンポーネント不要
2. 既存compose.ymlの変更最小
3. クロスプラットフォーム対応
4. CLIツールで自動化しやすい

### 実装方針
```bash
# gwt up feature-branch 実行時の内部動作
docker compose \
  --project-name myproject-feature-branch \
  -f docker-compose.yml \
  -f docker-compose.override.gwt.yml \
  up -d

# 環境変数でポートを動的指定
GWT_WEB_PORT=8001 \
GWT_API_PORT=8101 \
docker compose ...
```

---

## 参考資料

- [Docker Compose Port Mapping](https://www.warp.dev/terminus/docker-compose-port-mapping)
- [Multiple Docker Compose Instances](https://forums.docker.com/t/multiple-instances-of-docker-compose-on-a-single-server-that-listen-on-different-ports/137757)
- [Docker Project Name Isolation](https://www.kubeblogs.com/how-to-avoid-issues-with-docker-compose-due-to-same-folder-names-project-isolation-best-practices/)
- [Running Multiple Instances of Docker Compose](https://www.essamamdani.com/running-multiple-instances-of-a-single-docker-compose-application)
- [Docker Networking Guide](https://docs.docker.com/compose/how-tos/networking/)
- [Traefik Documentation](https://www.ssdnodes.com/blog/traefik-as-a-reverse-proxy-for-multiple-hosts-docker-compose/)
- [NGINX Load Balancing](https://ecostack.dev/posts/load-balancing-docker-compose-replicas-using-nginx/)
- [Firecracker MicroVMs Overview](https://firecracker-microvm.github.io/)
- [Environment Variables Best Practices](https://docs.docker.com/compose/how-tos/environment-variables/best-practices/)
- [Docker Network Drivers Comparison](https://www.datacamp.com/tutorial/docker-networking)
