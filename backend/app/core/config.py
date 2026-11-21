"""Cấu hình khi chạy. Bí mật lấy từ biến môi trường hoặc bên gọi, không lưu trong Git."""

from __future__ import annotations

import base64
import binascii
import os
from dataclasses import dataclass, field

PRODUCT_TIMEZONE = "Asia/Ho_Chi_Minh"
LEARNING_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


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
    question_model_timeout_seconds: float = 30.0
    question_max_tokens: int = 2048
    question_max_input_chars: int = 24000
    question_max_context_chunks: int = 12
    question_max_response_bytes: int = 128 * 1024
    learning_grounding_threshold: float = 0.78
    learning_model_timeout_seconds: float = 30.0
    learning_max_tokens: int = 1024
    learning_max_response_bytes: int = 64 * 1024
    learning_context_recent_turns: int = 6

    def __post_init__(self):
        if not self.supabase_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("supabase_url must be https (or a loopback URL for local development)")
        if self.supabase_jwt_algorithm not in ("ES256", "RS256", "EdDSA"):
            raise ValueError("supabase_jwt_algorithm must be an asymmetric algorithm")
        if len(self.signing_secret) < 32:
            raise ValueError("rpc_signing_secret_base64 must decode to at least 32 bytes")
        if self.default_timezone != PRODUCT_TIMEZONE:
            raise ValueError(f"default_timezone must be {PRODUCT_TIMEZONE}")
        if not (0 < self.question_model_timeout_seconds <= 120.0):
            raise ValueError("question_model_timeout_seconds must be within (0, 120]")
        if not (256 <= self.question_max_tokens <= 8192):
            raise ValueError("question_max_tokens must be between 256 and 8192")
        if not (1000 <= self.question_max_input_chars <= 100000):
            raise ValueError("question_max_input_chars must be between 1000 and 100000")
        if not (1 <= self.question_max_context_chunks <= 20):
            raise ValueError("question_max_context_chunks must be between 1 and 20")
        if not (4096 <= self.question_max_response_bytes <= 1024 * 1024):
            raise ValueError("question_max_response_bytes must be between 4096 and 1048576")
        if not (-1.0 <= self.learning_grounding_threshold <= 1.0):
            raise ValueError("learning_grounding_threshold must be within [-1.0, 1.0]")
        if not (0 < self.learning_model_timeout_seconds <= 120.0):
            raise ValueError("learning_model_timeout_seconds must be within (0, 120]")
        if not (128 <= self.learning_max_tokens <= 4096):
            raise ValueError("learning_max_tokens must be between 128 and 4096")
        if not (4096 <= self.learning_max_response_bytes <= 1024 * 1024):
            raise ValueError("learning_max_response_bytes must be between 4096 and 1048576")
        if not (1 <= self.learning_context_recent_turns <= 20):
            raise ValueError("learning_context_recent_turns must be between 1 and 20")

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
            question_model_timeout_seconds=float(env.get("QUESTION_MODEL_TIMEOUT_SECONDS", "30.0")),
            question_max_tokens=int(env.get("QUESTION_MAX_TOKENS", "2048")),
            question_max_input_chars=int(env.get("QUESTION_MAX_INPUT_CHARS", "24000")),
            question_max_context_chunks=int(env.get("QUESTION_MAX_CONTEXT_CHUNKS", "12")),
            question_max_response_bytes=int(env.get("QUESTION_MAX_RESPONSE_BYTES", str(128 * 1024))),
            learning_grounding_threshold=float(env.get("LEARNING_GROUNDING_THRESHOLD", "0.78")),
            learning_model_timeout_seconds=float(env.get("LEARNING_MODEL_TIMEOUT_SECONDS", "30.0")),
            learning_max_tokens=int(env.get("LEARNING_MAX_TOKENS", "1024")),
            learning_max_response_bytes=int(env.get("LEARNING_MAX_RESPONSE_BYTES", str(64 * 1024))),
            learning_context_recent_turns=int(env.get("LEARNING_CONTEXT_RECENT_TURNS", "6")),
        )
