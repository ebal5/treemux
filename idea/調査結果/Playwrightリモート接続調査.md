---
tags:
  - research/approved
  - priority/medium
  - research/technical
  - playwright
  - browser-automation
  - testing
created_at: 2026-01-07
updated_at: 2026-01-07
---

# Playwrightリモートブラウザ接続調査

## 調査目的

Worktree並列開発環境でPlaywright + Claude Codeによる動作確認を実現するため、リモートブラウザ接続の方法を調査。

---

## 1. browserType.connect() によるリモート接続

### 概要
Playwright独自プロトコルを使用した高信頼度接続

### サーバー側（ブラウザサーバー起動）
```javascript
const { chromium } = require('playwright');

const browserServer = await chromium.launchServer({
  host: '0.0.0.0',  // 外部からの接続を許可
  port: 3000        // 任意のポート
});
const wsEndpoint = browserServer.wsEndpoint();
console.log(`Browser server running at: ${wsEndpoint}`);
```

### クライアント側（リモート接続）
```javascript
const { chromium } = require('playwright');

const browser = await chromium.connect('ws://192.168.1.100:3000/...');
const page = await browser.newPage();
await page.goto('http://localhost:8001');
```

### 重要な制約
- **バージョン互換性が必須**: メジャー・マイナーバージョンが一致する必要がある
- 接続パラメータ: `timeout`、`slowMo`、`headers`、`exposeNetwork`をサポート

### 評価
| 項目 | 評価 |
|------|------|
| 信頼度 | ✅ 高い |
| 機能サポート | ✅ 全機能 |
| バージョン制約 | ⚠️ 厳格 |

---

## 2. CDP (Chrome DevTools Protocol) 経由の接続

### 概要
Chromium系ブラウザの低レベルプロトコル接続

### ブラウザ起動（リモートデバッグ有効化）
```bash
# Chrome/Chromium起動時
chrome --remote-debugging-port=9222

# または既存プロファイルで
chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

### Playwright側での接続
```javascript
const { chromium } = require('playwright');

// HTTP URLで接続
const browser = await chromium.connectOverCDP('http://localhost:9222');

// または WebSocket URIで接続
const browser = await chromium.connectOverCDP('ws://127.0.0.1:9222/devtools/browser/[ID]');

// 既存のコンテキストとページを取得
const defaultContext = browser.contexts()[0];
const page = defaultContext.pages()[0];
```

### 特徴
- **Chromium系ブラウザのみ対応**（Firefox/WebKitは非対応）
- HTTPエンドポイント例: `http://localhost:9222/`
- WebSocketエンドポイント例: `ws://127.0.0.1:9222/devtools/browser/[ID]`

### 評価
| 項目 | 評価 |
|------|------|
| 対応ブラウザ | ⚠️ Chromiumのみ |
| 信頼度 | ⚠️ connect()より低い |
| 既存ブラウザ接続 | ✅ 可能 |

---

## 3. VM内ブラウザとホストからの接続構成

### 推奨アーキテクチャ

```
┌─────────────────────────────────────┐
│ リモートVM / コンテナ               │
│ ┌────────────────────────────────┐ │
│ │ ブラウザサーバー起動           │ │
│ │ chromium.launchServer()        │ │
│ │ WebSocketエンドポイント公開    │ │
│ │ ws://0.0.0.0:3000/...          │ │
│ └────────────────────────────────┘ │
└─────────────────────────────────────┘
           ↑ WebSocket接続 (WSS推奨)
           │
┌─────────────────────────────────────┐
│ ホストマシン                        │
│ chromium.connect(wsEndpoint)        │
│ テストスクリプト実行                │
└─────────────────────────────────────┘
```

### ネットワーク設定
- **WebSocketホスト指定**: デフォルトはIPv6 (::) またはIPv4 (0.0.0.0)
- **ポート設定**: デフォルト0（自動割り当て）、固定も可能
- **セキュリティ**: 特定インターフェースにバインドして保護

### CI/CD統合例
```bash
# 環境変数で接続先を指定
PW_TEST_CONNECT_WS_ENDPOINT=ws://127.0.0.1:3000/ npx playwright test
```

---

## 4. 認証情報・セッション管理

### ストレージ状態の保存・復元

```javascript
// セッション状態を保存
const storageState = await context.storageState();
// 含まれるもの: Cookie、LocalStorage、IndexedDB

// JSONファイルに保存
await context.storageState({ path: 'auth.json' });

// 新しいコンテキストで復元
const newContext = await browser.newContext({
  storageState: 'auth.json'
});
```

### Cookie管理

```javascript
// Cookie取得
const cookies = await context.cookies(['https://example.com']);

// Cookie追加
await context.addCookies([{
  name: 'session',
  value: 'abc123',
  domain: 'example.com',
  path: '/'
}]);

// Cookie削除
await context.clearCookies();
```

### セッション保護ベストプラクティス

1. **リモートデバッグポートのセキュリティ**
   - 共有ネットワークや本番環境での公開は避ける
   - IPホワイトリスト設定
   - SSH トンネルの使用推奨

2. **セッション隔離**
   - テストごとに独立したブラウザコンテキストを作成
   - ログイン情報の漏洩防止

3. **認証フローの最適化**
   - ローカルストレージの保存・復元で反復的なログイン回避
   - `storageState()`で認証状態をJSON形式で永続化

### 永続コンテキストの活用

```javascript
// リモートVMで永続的なユーザーデータを保持
const context = await browser.launchPersistentContext(userDataDir, {
  // オプション
});
// Cookie、セッション、認証情報が自動的に保持される
```

---

## 5. 接続方法の選択基準

| 方法 | 対応ブラウザ | 信頼度 | 用途 |
|------|----------|------|------|
| `browserType.connect()` | Chromium/Firefox/WebKit | 高 | 本番環境、CI/CDパイプライン |
| `connectOverCDP()` | Chromium系のみ | 中 | デバッグ、既存ブラウザ接続 |

---

## 6. 本プロジェクトでの適用方針

### 推奨構成

**ホスト側でブラウザを起動し、コンテナのサービスにアクセス**

```
┌─────────────────────────────────────────────────────────────┐
│ ホスト (Windows / WSL2)                                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Playwright テスト                                    │   │
│  │ - ブラウザをローカルで起動                           │   │
│  │ - http://localhost:8001 にアクセス                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                         ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ docker compose (worktree-1)                          │  │
│  │ - web: localhost:8001                                │  │
│  │ - api: localhost:8101                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 理由
1. 仮想化不要でシンプル
2. ブラウザのセットアップ不要（ホストのPlaywrightがインストール済み）
3. ポートベースのルーティングと相性が良い

### gwt playwright コマンドの出力例

```bash
$ gwt playwright feature-branch

# Playwright環境変数
export BASE_URL=http://localhost:8001
export API_URL=http://localhost:8101

# playwright.config.ts での使用例
# use: {
#   baseURL: process.env.BASE_URL || 'http://localhost:3000',
# }

# テスト実行例
BASE_URL=http://localhost:8001 npx playwright test
```

---

## 将来の拡張: リモートブラウザサーバー

必要に応じて、コンテナ内でブラウザサーバーを起動する構成も可能:

```yaml
# docker-compose.override.gwt.yml に追加
services:
  playwright-server:
    image: mcr.microsoft.com/playwright:v1.40.0-jammy
    command: npx playwright run-server --port 3000 --host 0.0.0.0
    ports:
      - "${GWT_PLAYWRIGHT_PORT:-3000}:3000"
```

```javascript
// ホストからの接続
const browser = await chromium.connect(`ws://localhost:${GWT_PLAYWRIGHT_PORT}/`);
```

---

## 参考資料

- [BrowserType | Playwright](https://playwright.dev/docs/api/class-browsertype)
- [Connecting Playwright to an Existing Browser | BrowserStack](https://www.browserstack.com/guide/playwright-connect-to-existing-browser)
- [How to use Playwright with external/existing Chrome - DEV Community](https://dev.to/sonyarianto/how-to-use-playwright-with-externalexisting-chrome-4nf1)
- [BrowserContext | Playwright](https://playwright.dev/docs/api/class-browsercontext)
- [Managing Cookies using Playwright | BrowserStack](https://www.browserstack.com/guide/playwright-cookies)
- [Authentication | Playwright](https://playwright.dev/docs/auth)
