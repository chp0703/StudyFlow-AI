export type QuizQuestion = {
  id: number

  course: string

  question: string

  hint?: string

  options: string[]

  correctIndex: number

  explanation: string
}

export const quizQuestions: QuizQuestion[] = [
  {
    id: 1,

    course: "Giải tích",

    question:
      "Nếu hàm số f(x, y) = x²y + 3xy², đạo hàm riêng ∂f/∂x bằng bao nhiêu?",

    hint: "Giữ y không đổi khi lấy đạo hàm theo biến x.",

    options: ["2xy + 3y²", "x² + 6xy", "2xy + 6xy", "2x + 6y"],

    correctIndex: 0,

    explanation:
      "Khi lấy đạo hàm riêng theo biến x, coi y là hằng số: d/dx(x²y) = 2xy và d/dx(3xy²) = 3y². Do đó ∂f/∂x = 2xy + 3y².",
  },

  {
    id: 2,

    course: "Mạng máy tính",

    question:
      "Trong mô hình OSI 7 tầng, tầng nào chịu trách nhiệm định tuyến (routing) gói tin giữa các mạng?",

    hint: "Tầng này hoạt động dựa trên địa chỉ IP logic.",

    options: [
      "Tầng Mạng (Network Layer - Tầng 3)",

      "Tầng Liên kết dữ liệu (Data Link - Tầng 2)",

      "Tầng Giao vận (Transport - Tầng 4)",

      "Tầng Phiên (Session - Tầng 5)",
    ],

    correctIndex: 0,

    explanation:
      "Tầng Mạng (Layer 3) chịu trách nhiệm đánh địa chỉ logic (IP) và tìm đường đi (định tuyến) tối ưu cho gói tin qua các mạng khác nhau.",
  },

  {
    id: 3,

    course: "Kỹ thuật phần mềm",

    question:
      "Nguyên lý nào trong SOLID quy định một lớp chỉ nên có một lý do duy nhất để thay đổi?",

    hint: "Tập trung vào tính đơn nhiệm của từng module/class.",

    options: [
      "Single Responsibility Principle (SRP)",

      "Open/Closed Principle (OCP)",

      "Liskov Substitution Principle (LSP)",

      "Dependency Inversion Principle (DIP)",
    ],

    correctIndex: 0,

    explanation:
      "Single Responsibility Principle (SRP) khẳng định mỗi lớp chỉ nên đảm nhận một trách nhiệm duy nhất để giảm độ phụ thuộc và dễ bảo trì.",
  },

  {
    id: 4,

    course: "Cơ sở dữ liệu",

    question:
      "Mệnh đề SQL nào được sử dụng để loại bỏ các hàng trùng lặp trong tập kết quả truy vấn?",

    hint: "Đặt ngay sau từ khóa SELECT.",

    options: [
      "SELECT DISTINCT",

      "SELECT UNIQUE",

      "GROUP BY ALL",

      "FILTER DUPLICATES",
    ],

    correctIndex: 0,

    explanation:
      "Từ khóa DISTINCT trong câu lệnh 'SELECT DISTINCT' dùng để loại bỏ các bản ghi trùng lặp và chỉ trả về các giá trị phân biệt.",
  },

  {
    id: 5,

    course: "Cấu trúc dữ liệu & Giải thuật",

    question:
      "Độ phức tạp thời gian trung bình (average-case) của thuật toán sắp xếp nhanh (QuickSort) là gì?",

    hint: "Dựa trên chiến lược chia để trị (Divide and Conquer).",

    options: ["O(n log n)", "O(n²)", "O(n)", "O(log n)"],

    correctIndex: 0,

    explanation:
      "Thuật toán QuickSort trong trường hợp trung bình chia đôi mảng qua mỗi bước phân hoạch, đạt độ phức tạp O(n log n). Trường hợp xấu nhất mới là O(n²).",
  },
]
