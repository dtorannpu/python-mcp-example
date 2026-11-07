#!/bin/bash
# DCR で登録されたクライアントのトークンに aud=mcp-server を付与するため、
# aud マッパー付きのクライアントスコープを作成し、realm のデフォルトスコープに追加する。
# (realm JSON の clientScopes に書くと標準スコープ(basic 等)が作られなくなるため kcadm で行う)
set -eu
KCADM=/opt/keycloak/bin/kcadm.sh
REALM=demo
SCOPE=mcp-server-audience

until $KCADM config credentials --server http://keycloak:8080 --realm master \
  --user "$KC_ADMIN" --password "$KC_ADMIN_PASSWORD" >/dev/null 2>&1; do
  echo "waiting for keycloak..."; sleep 3
done

# 完全一致で既存スコープの ID を探す (JSON 出力で "id" の次の行が "name")
SCOPE_ID=$($KCADM get client-scopes -r $REALM --fields id,name \
  | tr -d ' \r' | grep -B1 "\"name\":\"$SCOPE\"" | grep -o '[0-9a-f-]\{36\}' || true)

if [ -z "$SCOPE_ID" ]; then
  SCOPE_ID=$($KCADM create client-scopes -r $REALM -i \
    -s name=$SCOPE -s protocol=openid-connect \
    -s 'attributes."include.in.token.scope"=false' \
    -s 'attributes."display.on.consent.screen"=false')
  $KCADM create client-scopes/$SCOPE_ID/protocol-mappers/models -r $REALM \
    -s name=audience-mcp-server -s protocol=openid-connect \
    -s protocolMapper=oidc-audience-mapper \
    -s 'config."included.custom.audience"=mcp-server' \
    -s 'config."access.token.claim"=true' \
    -s 'config."id.token.claim"=false'
fi
# 既にデフォルトスコープに追加済みの場合は 409 (conflict) になるので無視する
$KCADM update default-default-client-scopes/$SCOPE_ID -r $REALM -n 2>&1 | grep -v "Duplicate resource" || true
echo "DCR init done"
