"""Xác minh JWT bằng bộ khóa JWKS của Supabase."""

from __future__ import annotations

import threading
from datetime import datetime
from uuid import UUID

import httpx
import jwt

from .config import Settings

_JWKS_REFETCH_SECONDS = 30


class AuthError(Exception):
    """Lỗi khiến bearer token không được chấp nhận; không bao giờ chứa nội dung token."""


class AuthUnavailable(AuthError):
    """Không tải được khóa ký; bên gọi có thể thử lại."""


class JwtVerifier:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None, clock):
        self._settings = settings
        self._clock = clock
        self._http = httpx.Client(transport=transport, timeout=settings.rpc_timeout_seconds)
        self._lock = threading.Lock()
        self._keys: dict[str, dict] = {}
        self._fetched_at: datetime | None = None

    def _refresh(self, force: bool) -> None:
        now = self._clock()
        if self._fetched_at is not None and (not force or (now - self._fetched_at).total_seconds() < _JWKS_REFETCH_SECONDS):
            return
        response = self._http.get(f"{self._settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")
        response.raise_for_status()
        self._keys = {k["kid"]: k for k in response.json().get("keys", []) if k.get("kid")}
        self._fetched_at = now

    def _key_for(self, kid: str):
        with self._lock:
            try:
                self._refresh(force=False)
                if kid not in self._keys:
                    self._refresh(force=True)  # xoay vòng khóa: tải lại nhưng không tải cho mọi token lỗi
            except (httpx.HTTPError, ValueError):
                raise AuthUnavailable("signing keys unavailable") from None
            jwk = self._keys.get(kid)
        if jwk is None:
            raise AuthError("unknown signing key")
        return jwt.PyJWK(jwk).key

    def verify(self, authorization: str | None) -> str:
        """Trả subject đã xác minh (ID người dùng) hoặc ném AuthError."""
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthError("missing bearer token")
        token = authorization[len("Bearer "):].strip()
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != self._settings.supabase_jwt_algorithm or not isinstance(header.get("kid"), str):
                raise AuthError("algorithm or key id not allowed")
            claims = jwt.decode(
                token, self._key_for(header["kid"]), algorithms=[self._settings.supabase_jwt_algorithm],
                audience=self._settings.supabase_jwt_audience, issuer=self._settings.issuer,
                options={"require": ["exp", "sub", "iss", "aud"], "verify_exp": False, "verify_iat": False, "verify_nbf": False},
            )
        except jwt.PyJWTError:
            raise AuthError("invalid token") from None
        now = self._clock().timestamp()
        # Kiểm tra thời gian bằng đồng hồ được truyền vào để test và môi trường thật dùng cùng quy tắc.
        if not isinstance(claims["exp"], (int, float)) or claims["exp"] <= now or claims.get("nbf", 0) > now:
            raise AuthError("token expired")
        try:
            return str(UUID(str(claims["sub"])))
        except ValueError:
            raise AuthError("invalid subject") from None
