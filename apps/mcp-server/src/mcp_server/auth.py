"""Keycloak が発行した JWT アクセストークンの検証 (MCP の TokenVerifier 実装)。"""

import asyncio
import os

import httpx2
import jwt
from mcp.server.auth.provider import AccessToken

ISSUER = os.environ.get("KEYCLOAK_ISSUER", "http://localhost:8080/realms/demo")
JWKS_URL = os.environ.get(
    "KEYCLOAK_JWKS_URL",
    f"{ISSUER}/protocol/openid-connect/certs",
)
AUDIENCE = os.environ.get("AUTH_AUDIENCE", "mcp-server")
RESOURCE_URL = os.environ.get("MCP_RESOURCE_URL", "http://localhost:8001")


TOKEN_URL = os.environ.get(
    "KEYCLOAK_TOKEN_URL",
    f"{ISSUER}/protocol/openid-connect/token",
)
CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "mcp-server")
CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
API_AUDIENCE = os.environ.get("API_AUDIENCE", "api")


async def exchange_token(subject_token: str) -> str:
    """受け取ったユーザートークンを API 向けのトークンに交換する (RFC 8693)。"""
    async with httpx2.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "subject_token": subject_token,
                "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
                "audience": API_AUDIENCE,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]


class KeycloakTokenVerifier:
    def __init__(self) -> None:
        self._jwks_client = jwt.PyJWKClient(JWKS_URL)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            # JWKS の取得はブロッキング I/O なのでスレッドに逃がす
            signing_key = await asyncio.to_thread(
                self._jwks_client.get_signing_key_from_jwt, token
            )
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=AUDIENCE,
                issuer=ISSUER,
            )
        except jwt.PyJWTError:
            return None
        return AccessToken(
            token=token,
            client_id=claims.get("azp", ""),
            scopes=claims.get("scope", "").split(),
            expires_at=claims.get("exp"),
            resource=RESOURCE_URL,
            subject=claims.get("sub"),
            claims=claims,
        )
