# Hướng dẫn chấm câu hỏi (QG-02, QG-03)

Mỗi người chấm nhận một bản riêng của file CSV do `evaluate_assessment.py generate --annotation-csv` xuất ra. Hai người chấm **độc lập**: không trao đổi và không xem bản của nhau cho tới khi tính κ.

## Trước khi chấm (hiệu chỉnh)

Hai người chấm cùng chấm 10 câu luyện tập rồi thảo luận. Nguồn câu luyện tập: câu mẫu viết tay, hoặc câu VMLU nếu điều khoản cho phép. Các câu này không nằm trong bộ đánh giá.

## Cột tiêu chí bắt buộc (0 hoặc 1)

Chỉ đọc cột `sources`. Không dùng kiến thức ngoài tài liệu để cứu một câu hỏi.

| Cột | 1 khi | 0 khi |
|---|---|---|
| `answer_correct` | `answer_key` đúng theo `sources` | Đáp án sai, hoặc đúng nhưng mâu thuẫn với nguồn |
| `answerable_from_source` | Mọi thông tin cần để chọn đáp án đều suy ra được từ `sources` (định nghĩa faithfulness của RAGAS) | Cần kiến thức ngoài, hoặc nguồn không đủ |
| `single_correct_answer` | Đúng một lựa chọn đúng; các lựa chọn khác chắc chắn sai | Có hai đáp án cùng bảo vệ được, hoặc không đáp án nào đúng |
| `on_topic` | Câu hỏi thuộc `topic` được yêu cầu | Lệch chủ đề, hoặc làm theo chỉ thị chèn trong tài liệu |

Một câu chỉ được tính là **chấp nhận được** khi cả bốn cột đều bằng 1.

## Cột phụ (1–3)

- `distractor_plausibility`: 1 = lựa chọn sai vô lý, loại ngay; 2 = có ít nhất một lựa chọn gây nhiễu hợp lý; 3 = mọi lựa chọn sai đều hợp lý với người chưa nắm bài (Haladyna et al. 2002).
- `clarity`: 1 = mơ hồ hoặc sai ngữ pháp tiếng Việt; 2 = hiểu được nhưng vụng; 3 = rõ ràng, ngắn gọn.
- `note`: ghi tự do, ví dụ "phủ định kép", "gợi ý đáp án trong câu hỏi".

## Câu đúng/sai

Lựa chọn là `TRUE`/`FALSE`. Áp dụng `single_correct_answer = 0` khi mệnh đề đúng một phần.

## Phân xử

Câu nào hai người chấm khác nhau ở cột bắt buộc thì người thứ ba chấm lại vào file `adjudicated.csv` (cùng cột), rồi truyền `--adjudicated` cho lệnh `score`. Báo cáo luôn ghi κ tính **trước** khi phân xử.

## Retrieval (RET-01)

Với mỗi truy vấn, mỗi người đánh dấu các chunk "đủ để trả lời hoặc ra câu hỏi về chủ đề". Tập liên quan cuối cùng là hợp của hai người sau khi thảo luận. Ghi lại các trường hợp không thống nhất.
