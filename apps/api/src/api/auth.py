"""Keycloak が発行した JWT アクセストークンの検証。"""

import os
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ISSUER = os.environ.get("KEYCLOAK_ISSUER", "http://localhost:8080/realms/demo")
JWKS_URL = os.environ.get(
    "KEYCLOAK_JWKS_URL",
    f"{ISSUER}/protocol/openid-connect/certs",
)
AUDIENCE = os.environ.get("AUTH_AUDIENCE", "api")

_jwks_client = jwt.PyJWKClient(JWKS_URL)
_bearer = HTTPBearer(auto_error=False)


def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, Any]:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(credentials.credentials)
        return jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
    except jwt.PyJWTError as e:
        raise unauthorized from e
