# python-mcp-example

MCP サーバー (`apps/mcp-server`) と API (`apps/api`) を Keycloak で保護するサンプル。

## 起動

```sh
docker compose up -d --build
```

| サービス | URL |
|---|---|
| MCP サーバー | http://localhost:8001/mcp |
| API | http://localhost:8000 |
| Keycloak | http://localhost:8080 (admin / admin) |
| Jaeger UI | http://localhost:16686 |

## 認証

MCP サーバーと API は Resource Server で、Keycloak (`demo` realm) が発行した JWT (Bearer) を検証するだけです。
PKCE (Authorization Code + PKCE, S256) を行うのは MCP クライアント側です。

### エンドポイント (Keycloak)

| 用途 | URL |
|---|---|
| 認可 URL | `http://localhost:8080/realms/demo/protocol/openid-connect/auth` |
| アクセストークン URL | `http://localhost:8080/realms/demo/protocol/openid-connect/token` |
| JWKS | `http://localhost:8080/realms/demo/protocol/openid-connect/certs` |
| メタデータ | `http://localhost:8080/realms/demo/.well-known/openid-configuration` |

MCP クライアントは `http://localhost:8001/.well-known/oauth-protected-resource` から issuer を辿って自動検出します。
Inspector など手動設定のクライアントでは上記の認可 URL / トークン URL を入力してください。

### クライアント設定 (`keycloak/demo-realm.json`)

| 項目 | 値 |
|---|---|
| Client ID (MCP クライアント用) | `mcp-client` (公開クライアント、PKCE S256 必須) |
| Redirect URI | 任意 (`*` 許可。デモ用) |
| アクセストークンの `aud` | `mcp-server` |
| ユーザー | `demo` / `demo` |

`mcp-server` クライアント (機密) は token exchange (RFC 8693) 用で、受け取ったトークンを `aud=api` のトークンに交換して API を呼びます。

### フロー

1. クライアントが `/mcp` を呼ぶと 401 と `resource_metadata` が返る
2. クライアントが Keycloak で Authorization Code + PKCE を実行しトークン取得
3. `Authorization: Bearer <token>` を付けて `/mcp` を呼ぶ
4. MCP サーバーが署名・`iss`・`aud=mcp-server` を検証
5. `add` ツールは token exchange で API 用トークンに交換して API の `/add` を呼ぶ

## 注意

認証関連のコードを変更したら、`docker compose up -d --build` で再ビルドしてください。古いイメージのままだと変更が反映されません。
