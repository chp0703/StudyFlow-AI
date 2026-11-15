"""Cấu hình khi chạy. Bí mật lấy từ biến môi trường hoặc bên gọi, không lưu trong Git."""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass, field

PRODUCT_TIMEZONE = "Asia/Ho_Chi_Minh"


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_publishable_key: str
    rpc_signing_key_id: str
    rpc_signing_secret_base64: str
    supabase_jwt_audience: str = "authenticated"
    supabase_jwt_algorithm: str = "ES256"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    ingestion_model: str = "deepseek-flash"
    cors_origins: list[str] = field(default_factory=list)
    default_timezone: str = PRODUCT_TIMEZONE
    default_locale: str = "vi-VN"
    rpc_timeout_seconds: float = 10.0
    max_body_bytes: int = 64 * 1024

    def __post_init__(self):
        if not self.supabase_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("supabase_url must be https (or a loopback URL for local development)")
        if self.supabase_jwt_algorithm not in ("ES256", "RS256", "EdDSA"):
            raise ValueError("supabase_jwt_algorithm must be an asymmetric algorithm")
        if len(self.signing_secret) < 32:
            raise ValueError("rpc_signing_secret_base64 must decode to at least 32 bytes")
        if self.default_timezone != PRODUCT_TIMEZONE:
            raise ValueError(f"default_timezone must be {PRODUCT_TIMEZONE}")

    @property
    def signing_secret(self) -> bytes:
        try:
            return base64.b64decode(self.rpc_signing_secret_base64, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("rpc_signing_secret_base64 is not valid base64") from None

    @property
    def issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @classmethod
    def from_env(cls) -> "Settings":
        env = os.environ
        origins = [o.strip() for o in env.get("CORS_ORIGINS", "").split(",") if o.strip()]
        return cls(
            supabase_url=env["SUPABASE_URL"].rstrip("/"),
            supabase_publishable_key=env["SUPABASE_PUBLISHABLE_KEY"],
            rpc_signing_key_id=env["RPC_SIGNING_KEY_ID"],
            rpc_signing_secret_base64=env["RPC_SIGNING_SECRET_BASE64"],
            supabase_jwt_audience=env.get("SUPABASE_JWT_AUDIENCE", "authenticated"),
            supabase_jwt_algorithm=env.get("SUPABASE_JWT_ALGORITHM", "ES256"),
            deepseek_api_key=env.get("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            deepseek_model=env.get("DEEPSEEK_MODEL", "deepseek-chat"),
            ingestion_model=env.get("INGESTION_MODEL", "deepseek-flash"),
            cors_origins=origins,
        )
