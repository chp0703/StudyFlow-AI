# Đánh giá truy hồi Daily Learning (F3 M5)

Bộ đo kiểm tra hai việc: câu hỏi trong tài liệu có tìm đúng trang không, và câu hỏi ngoài tài liệu có bị chặn trước khi gọi model không. Kết quả dùng để chọn ngưỡng căn cứ τ (`LEARNING_GROUNDING_THRESHOLD`).

## Chạy

Cài `backend/requirements-embedding.txt` (xem `contracts/LEARNING.md`), rồi chạy từ thư mục gốc:

```
python backend/scripts/evaluate_learning.py > docs/features/daily-learning/evaluation/results/retrieval-dev.json
```

Dữ liệu: `backend/tests/fixtures/learning_eval/corpus_vi.json` gồm 6 trang Toán rời rạc, 30 câu có trang đúng và 10 câu ngoài tài liệu.

## Chỉ số

| Chỉ số | Ý nghĩa |
|---|---|
| hit@k | Trang đúng nằm trong k chunk gần nhất |
| refusal | Tỉ lệ câu ngoài tài liệu có điểm cosine tốt nhất dưới τ |
| coverage | Tỉ lệ câu trong tài liệu vượt τ |
| fabrication | Câu vượt τ nhưng trang đúng không nằm trong top-k |

τ đề xuất là ngưỡng nhỏ nhất đạt refusal ≥ 0.9.

## Kết quả (bộ dev, `retrieval-dev.json`)

| τ | refusal | coverage | fabrication (k=6) |
|---|---|---|---|
| 0.78 (mặc định cũ) | 0.4 | 1.0 | 0.0 |
| 0.80 | 0.7 | 1.0 | 0.0 |
| **0.82 (mặc định mới)** | **0.9** | **1.0** | **0.0** |
| 0.84 | 1.0 | 0.97 | 0.0 |

- hit@1 = 0.93, hit@6 = 1.0. Tài liệu chỉ có 7 chunk nên hit@6 gần như hiển nhiên; hit@1 phản ánh chất lượng tốt hơn.
- Điểm cosine tốt nhất: câu trong tài liệu 0.839–0.911, câu ngoài tài liệu 0.728–0.838. Hai khoảng chồng lên nhau ở khoảng 0.84, nên không có τ nào vừa chặn hết câu ngoài tài liệu vừa giữ hết câu trong tài liệu.

## Giới hạn

- Corpus do nhóm tự soạn, nhỏ và đã dùng để chọn τ. Cần thêm bộ held-out từ tài liệu môn học thật trước khi coi τ là ổn định.
- Runner chỉ dùng cosine top-k; truy hồi trong DB có thêm FTS gộp RRF, nên hit@k ở đây là cận dưới. Cổng τ dùng cùng điểm cosine tốt nhất như `has_sufficient_grounding`, nên ngưỡng áp dụng nguyên vẹn.
- Không đo chất lượng câu trả lời của DeepSeek, chỉ đo bước truy hồi và cổng chặn.
