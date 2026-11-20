"""Unit tests for Daily Learning material extraction, chunking, and CPU embedding."""

from __future__ import annotations

import importlib.util
import math
import subprocess
import time
import unittest
from unittest.mock import patch

from backend.app.core.config import LEARNING_EMBEDDING_MODEL
from backend.app.ingestion.document import read_document_pages
from backend.app.learning import (
    IndexDocumentResult,
    IndexingError,
    IndexTimeoutError,
    IndexUnavailableError,
    InvalidDocumentError,
    chunk_f2_pages,
    chunk_f3_page,
    chunk_f3_pages,
    clear_embedding_cache,
    count_passage_tokens,
    embed_passages,
    index_document,
    set_cached_model,
)
from backend.app.orchestrator.workflow_ports import WorkflowError


class FakeTokenizer:
    """Deterministic tokenizer simulator for testing token budgets without external model files."""

    def __init__(self, chars_per_token: int = 4, special_tokens: int = 2):
        self.chars_per_token = chars_per_token
        self.special_tokens = special_tokens

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        count = math.ceil(len(text) / self.chars_per_token)
        if add_special_tokens:
            count += self.special_tokens
        return list(range(count))


class DenseFakeTokenizer:
    """Tokenizer where each character is a token (simulates dense Asian languages / token limits)."""

    def __init__(self, special_tokens: int = 2):
        self.special_tokens = special_tokens

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        count = len(text) + (self.special_tokens if add_special_tokens else 0)
        return list(range(count))


class FakeEmbeddingModel:
    """Deterministic CPU embedding model returning finite, normalized 384-d vectors."""

    def __init__(self, dim: int = 384, return_invalid: str | None = None, delay: float = 0.0):
        self.dim = dim
        self.tokenizer = FakeTokenizer()
        self.return_invalid = return_invalid
        self.delay = delay
        self.call_count = 0
        self.batches_received: list[list[str]] = []

    def encode(
        self,
        sentences: list[str],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False,
        batch_size: int = 16,
    ) -> list[list[float]]:
        if self.delay > 0:
            time.sleep(self.delay)

        self.call_count += 1
        self.batches_received.append(list(sentences))

        if self.return_invalid == "dim_mismatch":
            return [[0.1] * 128 for _ in sentences]
        if self.return_invalid == "nan":
            return [[float("nan")] * self.dim for _ in sentences]
        if self.return_invalid == "zeros":
            return [[0.0] * self.dim for _ in sentences]

        results = []
        for s in sentences:
            val = 1.0 / math.sqrt(self.dim)
            results.append([val] * self.dim)
        return results


def small_pdf(stream: bytes) -> bytes:
    """Generate a minimal valid 1-page PDF containing the provided stream content."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data, offsets = b"%PDF-1.4\n", []
    for number, value in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{number} 0 obj\n".encode() + value + b"\nendobj\n"
    start = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    data += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n" + str(start).encode() + b"\n%%EOF\n"
    return data


class TestF3Chunking(unittest.TestCase):
    def test_chunk_f3_page_target_and_overlap(self):
        # 1600 characters of English text with space separators
        words = ["word" for _ in range(320)]
        text = " ".join(words)
        self.assertGreater(len(text), 1500)

        chunks = chunk_f3_page(text, 1, target_chars=800, overlap_chars=100)
        self.assertGreaterEqual(len(chunks), 2)
        for c in chunks:
            self.assertLessEqual(len(c), 850)
            self.assertGreater(len(c), 0)

        # Overlap check: ending words of chunk 0 should overlap with beginning of chunk 1
        tail_words = set(chunks[0].split()[-5:])
        head_words = set(chunks[1].split()[:15])
        self.assertTrue(tail_words.intersection(head_words))

    def test_chunk_f3_page_no_whitespace(self):
        # 2500 characters with no whitespace
        text = "A" * 2500
        chunks = chunk_f3_page(text, 1, target_chars=800, overlap_chars=100)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 800)
        # Advance with overlap: next start is 700
        self.assertEqual(chunks[0][700:], chunks[1][:100])

    def test_chunk_f3_page_unicode_whitespace(self):
        # Unicode whitespace: non-breaking space \u00a0 and ideographic space \u3000
        text = ("Đoạn\u00a0văn\u00a0thử\u3000nghiệm\u3000tiếng\u00a0Việt. " * 30).strip()
        chunks = chunk_f3_page(text, 1, target_chars=800, overlap_chars=100)
        self.assertGreaterEqual(len(chunks), 1)
        for c in chunks:
            self.assertFalse(c.startswith(" "))
            self.assertFalse(c.endswith(" "))

    def test_chunk_f3_page_final_tail_and_empty_fragments(self):
        # Small tail at end should be preserved as final chunk
        text = ("Alpha beta gamma delta epsilon. " * 26) + "Final tail piece."
        chunks = chunk_f3_page(text, 1, target_chars=800, overlap_chars=100)
        self.assertIn("Final tail piece.", chunks[-1])

        # Whitespace-only page returns empty list
        self.assertEqual(chunk_f3_page("   \n\t  ", 1), [])

    def test_chunk_f3_tokenizer_constraint_no_truncation(self):
        # Dense tokenizer: 1 char = 1 token. With prefix "passage: " (9 chars) and 2 special tokens = 11 tokens overhead.
        # Max tokens = 50. Candidate ~100 chars must shrink to fit <= 50 tokens.
        tok = DenseFakeTokenizer(special_tokens=2)
        text = "Hello world this is a test text designed to verify token budget shrinking without truncation. " * 3
        chunks = chunk_f3_page(text, 1, tokenizer=tok, target_chars=800, overlap_chars=50, max_tokens=50)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            token_count = count_passage_tokens(c, tok)
            self.assertLessEqual(token_count, 50)

    def test_chunk_f3_pages_page_boundaries_and_contiguous_index(self):
        pages = [
            "Page one content with sufficient length to test chunking.",
            "Page two content also with text.",
            "Page three content.",
        ]
        records = chunk_f3_pages(pages, target_chars=800, overlap_chars=100)
        self.assertEqual(len(records), 3)
        for idx, rec in enumerate(records):
            self.assertEqual(rec["chunk_index"], idx)
            self.assertEqual(rec["page_start"], idx + 1)
            self.assertEqual(rec["page_end"], idx + 1)
            self.assertEqual(rec["text"], pages[idx])


class TestF2ProjectionChunking(unittest.TestCase):
    def test_chunk_f2_pages_assessment_shape(self):
        pages = ["P1 text content.", "P2 text content."]
        chunks = chunk_f2_pages(pages, max_chunk_size=2000, max_rows=500)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], {"page": 1, "chunk_index": 0, "text": "P1 text content."})
        self.assertEqual(chunks[1], {"page": 2, "chunk_index": 1, "text": "P2 text content."})

    def test_chunk_f2_pages_row_limit_exceeded(self):
        pages = [f"Page {i} content" for i in range(505)]
        with self.assertRaises(InvalidDocumentError) as err:
            chunk_f2_pages(pages, max_chunk_size=2000, max_rows=500)
        self.assertEqual(err.exception.code, "INVALID_DOCUMENT")


class TestEmbeddingBatchAndValidation(unittest.TestCase):
    def setUp(self):
        clear_embedding_cache()

    def tearDown(self):
        clear_embedding_cache()

    def test_embed_passages_normalizes_and_prefixes(self):
        model = FakeEmbeddingModel(dim=384)
        passages = ["Học phần Giải tích 1", "Đại số tuyến tính"]
        vectors = embed_passages(passages, model=model, batch_size=2)

        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), 384)
        norm = math.sqrt(sum(x * x for x in vectors[0]))
        self.assertAlmostEqual(norm, 1.0, places=5)
        # Check prefix
        self.assertEqual(model.batches_received[0], ["passage: Học phần Giải tích 1", "passage: Đại số tuyến tính"])

    def test_embed_passages_dimension_mismatch(self):
        model = FakeEmbeddingModel(return_invalid="dim_mismatch")
        with self.assertRaises(InvalidDocumentError) as err:
            embed_passages(["Test text"], model=model)
        self.assertEqual(err.exception.code, "INVALID_DOCUMENT")

    def test_embed_passages_non_finite_rejected(self):
        model = FakeEmbeddingModel(return_invalid="nan")
        with self.assertRaises(InvalidDocumentError) as err:
            embed_passages(["Test text"], model=model)
        self.assertEqual(err.exception.code, "INVALID_DOCUMENT")

    def test_embed_passages_zero_vector_rejected(self):
        model = FakeEmbeddingModel(return_invalid="zeros")
        with self.assertRaises(InvalidDocumentError) as err:
            embed_passages(["Test text"], model=model)
        self.assertEqual(err.exception.code, "INVALID_DOCUMENT")

    def test_embed_passages_deadline_exceeded(self):
        model = FakeEmbeddingModel(delay=0.1)
        deadline = time.monotonic() - 1.0  # Already expired
        with self.assertRaises(IndexTimeoutError) as err:
            embed_passages(["Test text"], model=model, deadline=deadline)
        self.assertEqual(err.exception.code, "INDEX_TIMEOUT")

    def test_model_cache_reused(self):
        model = FakeEmbeddingModel()
        set_cached_model(LEARNING_EMBEDDING_MODEL, model)
        # When model is None, it should resolve from cache without error
        vectors = embed_passages(["Cached invocation"])
        self.assertEqual(len(vectors), 1)
        self.assertEqual(model.call_count, 1)


class TestIndexDocument(unittest.TestCase):
    def setUp(self):
        clear_embedding_cache()
        self.fake_model = FakeEmbeddingModel()
        self.fake_tokenizer = FakeTokenizer()

    def test_index_plaintext_document(self):
        raw = "Chương 1: Khái niệm cơ bản về lập trình Python.\nNội dung bài học ngắn gọn.".encode("utf-8")
        result = index_document(raw, "text/plain", model=self.fake_model, tokenizer=self.fake_tokenizer)

        self.assertEqual(result.page_count, 1)
        self.assertEqual(result.char_count, len(raw.decode("utf-8")))
        self.assertEqual(result.pages, 1)
        self.assertEqual(result["page_count"], 1)
        self.assertEqual(result.raw_char_count, result.char_count)

        self.assertGreaterEqual(len(result.f3_chunks), 1)
        f3 = result.f3_chunks[0]
        self.assertEqual(f3["chunk_index"], 0)
        self.assertEqual(f3["page_start"], 1)
        self.assertEqual(f3["page_end"], 1)
        self.assertIn("Python", f3["text"])
        self.assertEqual(len(f3["vector"]), 384)
        self.assertEqual(f3["embedding_model"], LEARNING_EMBEDDING_MODEL)

        self.assertGreaterEqual(len(result.f2_chunks), 1)
        f2 = result.f2_chunks[0]
        self.assertEqual(f2["page"], 1)
        self.assertEqual(f2["chunk_index"], 0)
        self.assertNotIn("vector", f2)

    def test_index_markdown_document(self):
        content = "# Markdown Header\n\n- Mục 1\n- Mục 2\n\nNội dung chi tiết markdown.".encode("utf-8")
        result = index_document(content, "text/markdown", model=self.fake_model, tokenizer=self.fake_tokenizer)
        self.assertEqual(result.page_count, 1)
        self.assertIn("Markdown Header", result.f3_chunks[0]["text"])

    def test_index_document_result_dictionary_and_dataclass_access(self):
        content = b"Simple document text for testing."
        res = index_document(content, "text/plain", model=self.fake_model)
        self.assertEqual(res.page_count, 1)
        self.assertEqual(res["page_count"], 1)
        self.assertEqual(res["pages"], 1)
        self.assertEqual(res.get("page_count"), 1)
        self.assertIsNone(res.get("non_existent_key"))
        d = res.to_dict()
        self.assertIn("f3_chunks", d)
        self.assertIn("f2_chunks", d)

    def test_pre_deadline_exceeded_raises_index_timeout(self):
        past_deadline = time.monotonic() - 5.0
        with self.assertRaises(IndexTimeoutError) as err:
            index_document(b"Hello", "text/plain", deadline=past_deadline, model=self.fake_model)
        self.assertEqual(err.exception.code, "INDEX_TIMEOUT")

    def test_index_uses_the_loaded_models_tokenizer(self):
        model = FakeEmbeddingModel()
        model.tokenizer = DenseFakeTokenizer()
        result = index_document(b"A" * 1800, "text/plain", model=model)
        self.assertGreater(len(result.f3_chunks), 3)
        self.assertTrue(all(count_passage_tokens(chunk["text"], model.tokenizer) <= 512
                            for chunk in result.f3_chunks))

    def test_invalid_mime_type_raises_invalid_document(self):
        with self.assertRaises(InvalidDocumentError) as err:
            index_document(b"Some text", "image/png", model=self.fake_model)
        self.assertEqual(err.exception.code, "INVALID_DOCUMENT")

    def test_binary_garbage_in_plaintext_raises_invalid_document(self):
        with self.assertRaises(InvalidDocumentError) as err:
            index_document(b"Valid text \x00 binary null", "text/plain", model=self.fake_model)
        self.assertEqual(err.exception.code, "INVALID_DOCUMENT")

    def test_oversize_text_raises_invalid_document(self):
        huge_text = ("A" * 200_005).encode("utf-8")
        with self.assertRaises(InvalidDocumentError) as err:
            index_document(huge_text, "text/plain", max_text=200_000, model=self.fake_model)
        self.assertEqual(err.exception.code, "INVALID_DOCUMENT")

    def test_missing_dependencies_raises_index_unavailable(self):
        # When no model is provided and sentence_transformers is not found
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            clear_embedding_cache()
            with self.assertRaises(IndexUnavailableError) as err:
                index_document(b"Document text", "text/plain", model=None)
            self.assertEqual(err.exception.code, "INDEX_UNAVAILABLE")

    def test_pdf_timeout_distinguished_as_index_timeout(self):
        # Simulate subprocess.TimeoutExpired during PDF extraction
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pdf_worker", timeout=5.0)):
            with self.assertRaises(IndexTimeoutError) as err:
                index_document(b"%PDF-1.4 mock", "application/pdf", model=self.fake_model)
            self.assertEqual(err.exception.code, "INDEX_TIMEOUT")

    def test_pdf_dependency_missing_distinguished_as_index_unavailable(self):
        mock_output = subprocess.CompletedProcess(args=[], returncode=1, stdout=b'{"error": "DEPENDENCY_MISSING"}')
        with patch("subprocess.run", return_value=mock_output):
            with self.assertRaises(IndexUnavailableError) as err:
                index_document(b"%PDF-1.4 mock", "application/pdf", model=self.fake_model)
            self.assertEqual(err.exception.code, "INDEX_UNAVAILABLE")

    def test_pdf_corrupt_distinguished_as_invalid_document(self):
        mock_output = subprocess.CompletedProcess(args=[], returncode=1, stdout=b'{"error": "INVALID_PDF"}')
        with patch("subprocess.run", return_value=mock_output):
            with self.assertRaises(InvalidDocumentError) as err:
                index_document(b"%PDF-1.4 mock", "application/pdf", model=self.fake_model)
            self.assertEqual(err.exception.code, "INVALID_DOCUMENT")


class TestPreserveF1F2Behavior(unittest.TestCase):
    def test_read_document_pages_preserves_f1_f2_exceptions_when_not_typed(self):
        # Default typed_errors=False should raise WorkflowError('INVALID_PARAMETER')
        with self.assertRaises(WorkflowError) as err:
            read_document_pages(b"Invalid \x00 binary", "text/plain")
        self.assertEqual(err.exception.code, "INVALID_PARAMETER")

        # Unsupported mime raises default invalid() -> INVALID_PARAMETER
        with self.assertRaises(WorkflowError) as err:
            read_document_pages(b"data", "audio/mp3")
        self.assertEqual(err.exception.code, "INVALID_PARAMETER")


@unittest.skipUnless(importlib.util.find_spec("pypdf"), "pypdf is installed in CI or embedding env")
class TestActualPdfIndexing(unittest.TestCase):
    def setUp(self):
        self.fake_model = FakeEmbeddingModel()

    def test_extract_and_index_actual_pdf(self):
        data = small_pdf(b"BT /F1 12 Tf 10 100 Td (StudyFlow AI Lesson 1) Tj ET")
        res = index_document(data, "application/pdf", model=self.fake_model)
        self.assertEqual(res.page_count, 1)
        self.assertIn("StudyFlow AI Lesson 1", res.f3_chunks[0]["text"])


if __name__ == "__main__":
    unittest.main()
