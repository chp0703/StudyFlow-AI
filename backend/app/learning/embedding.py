"""CPU embedding model loader, cache, and batch encoding for Daily Learning."""

from __future__ import annotations

import math
import threading
import time
from typing import Any

from ..core.config import LEARNING_EMBEDDING_MODEL
from .exceptions import IndexTimeoutError, IndexUnavailableError, InvalidDocumentError

EMBEDDING_DIM = 384
DEFAULT_BATCH_SIZE = 16
E5_PREFIX = "passage: "

_MODEL_CACHE: dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()


def check_deadline(deadline: float | None) -> None:
    """Raise IndexTimeoutError if monotonic deadline has passed."""
    if deadline is not None and time.monotonic() >= deadline:
        raise IndexTimeoutError("Quá thời gian xử lý tài liệu.")


def resolve_deadline(
    deadline: float | None = None,
    timeout_seconds: float | None = None,
) -> float | None:
    """Normalize deadline parameter into a monotonic timestamp."""
    if timeout_seconds is not None:
        return time.monotonic() + max(0.0, float(timeout_seconds))
    if deadline is None:
        return None
    return float(deadline)


def get_embedding_model(model_name: str = LEARNING_EMBEDDING_MODEL) -> Any:
    """Lazily load and cache the CPU SentenceTransformer model."""
    if model_name in _MODEL_CACHE:
        return _MODEL_CACHE[model_name]
    with _CACHE_LOCK:
        if model_name in _MODEL_CACHE:
            return _MODEL_CACHE[model_name]
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(model_name, device="cpu")
            _MODEL_CACHE[model_name] = model
            return model
        except ImportError as exc:
            raise IndexUnavailableError(
                f"Chưa cài đặt thư viện sentence-transformers: {exc}"
            ) from exc
        except Exception as exc:
            raise IndexUnavailableError(
                f"Không thể khởi tạo mô hình embedding {model_name}: {exc}"
            ) from exc


def set_cached_model(model_name: str, model: Any) -> None:
    """Register pre-instantiated or fake model/tokenizer into the cache."""
    with _CACHE_LOCK:
        _MODEL_CACHE[model_name] = model


def clear_embedding_cache() -> None:
    """Clear cached models and tokenizers (useful in tests)."""
    with _CACHE_LOCK:
        _MODEL_CACHE.clear()


def embed_passages(
    passages: list[str],
    *,
    model: Any = None,
    model_name: str = LEARNING_EMBEDDING_MODEL,
    batch_size: int = DEFAULT_BATCH_SIZE,
    deadline: float | None = None,
    prefix: str = E5_PREFIX,
) -> list[list[float]]:
    """Batch encode passages on CPU with literal prefix and L2 normalization."""
    if not passages:
        return []

    check_deadline(deadline)

    if model is None:
        model = get_embedding_model(model_name)

    prefixed_inputs = [f"{prefix}{p}" for p in passages]
    results: list[list[float]] = []

    for i in range(0, len(prefixed_inputs), batch_size):
        check_deadline(deadline)
        batch = prefixed_inputs[i : i + batch_size]

        if hasattr(model, "encode"):
            try:
                embeddings = model.encode(
                    batch,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    batch_size=len(batch),
                )
            except TypeError:
                try:
                    embeddings = model.encode(batch, normalize_embeddings=True)
                except TypeError:
                    embeddings = model.encode(batch)
        elif callable(model):
            embeddings = model(batch)
        else:
            raise IndexUnavailableError(f"Mô hình embedding không hợp lệ: {type(model)}")

        if hasattr(embeddings, "tolist"):
            batch_vectors = embeddings.tolist()
        elif isinstance(embeddings, list):
            batch_vectors = embeddings
        else:
            batch_vectors = list(embeddings)

        for vec in batch_vectors:
            if hasattr(vec, "tolist"):
                vec = vec.tolist()
            float_vec = [float(x) for x in vec]

            if len(float_vec) != EMBEDDING_DIM:
                raise InvalidDocumentError(
                    f"Kích thước vector không đúng: {len(float_vec)} != {EMBEDDING_DIM}"
                )
            if not all(math.isfinite(x) for x in float_vec):
                raise InvalidDocumentError("Vector embedding chứa giá trị không hợp lệ (NaN hoặc Inf).")

            norm = math.sqrt(sum(x * x for x in float_vec))
            if norm == 0.0 or not math.isfinite(norm):
                raise InvalidDocumentError("Vector embedding không được là vector không.")

            if abs(norm - 1.0) > 1e-4:
                float_vec = [x / norm for x in float_vec]

            results.append(float_vec)

    check_deadline(deadline)
    return results
