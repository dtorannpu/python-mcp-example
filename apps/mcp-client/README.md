# mcp-client

Keycloak で保護された MCP サーバー (`apps/mcp-server`) を呼び出す CLI クライアント。
Authorization Code + PKCE でブラウザログインし、取得したトークンで MCP サーバーを呼びます。

## 使い方

事前に `docker compose up -d --build` でサーバー群を起動してください。

```sh
uv run --package mcp-client mcp-client tools
uv run --package mcp-client mcp-client call add --args '{"a": 1, "b": 2}'
```

初回はブラウザが開くので `demo` / `demo` でログインします (DCR クライアントは同意画面も表示されます)。
トークンはメモリ上のみで、実行ごとにログインが必要です。

## 設定

| 環境変数 / オプション | 既定値 | 説明 |
|---|---|---|
| `MCP_SERVER_URL` / `--url` | `http://localhost:8001/mcp` | MCP サーバー URL |
| `MCP_CLIENT_ID` / `--client-id` | (未指定) | 指定すると DCR せず事前登録クライアント (例: `mcp-client`) を使う |

- リダイレクト URI は `http://localhost:3030/callback` (ローカルで一時 HTTP サーバーを起動して認可コードを受け取る)
- 未指定の場合は Dynamic Client Registration (RFC 7591) で自動登録します
