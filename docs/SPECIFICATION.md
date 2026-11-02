# BẢN ĐẶC TẢ KỸ THUẬT (PRD & TECHNICAL SPECIFICATION)
**Tên dự án:** Hệ thống Tự động hóa Khảo sát Thông minh & Sinh dữ liệu Nghiên cứu (Smart Survey Auto-Filler & SPSS Data Generator)  
**Kiến trúc:** Full-stack Web Application + Async High-Concurrency Worker  
**Đối tượng đọc tài liệu:** AI Coding Assistant (Claude / Cursor) & Developer  

> Bản sao nguyên văn từ người dùng (2026-11-02). Yêu cầu bổ sung sau này nằm trong `CLAUDE.md` và `docs/dev-notes/spec.md`.

---

## 1. HƯỚNG DẪN DÀNH CHO AI CODING ASSISTANT (SYSTEM PROMPT FOR CLAUDE)
Khi bạn (Claude) đọc tài liệu này để viết code cho dự án, hãy tuân thủ nghiêm ngặt các nguyên tắc sau:
1. **Không viết code giả (No Placeholders):** Luôn viết code hoàn chỉnh, xử lý đầy đủ ngoại lệ (`try/except`), có Type Hints rõ ràng (Pydantic v2 cho Python, TypeScript Interfaces cho React).
2. **Tuân thủ Bất đồng bộ (Async-First):** Toàn bộ I/O (Database, HTTP Request bắn form, Playwright, Redis) bắt buộc dùng `async/await` để đạt hiệu năng hàng nghìn phản hồi.
3. **Chính xác tuyệt đối về Google Form Reverse Engineering:** Tuân thủ đúng cấu trúc mảng `FB_PUBLIC_LOAD_DATA_` và quy tắc đóng gói payload `entry.<id>`, `pageHistory`, `fbzx` được mô tả ở Mục 5.
4. **Sử dụng SDK mới nhất:** Sử dụng `google-genai` (SDK mới của Google Gemini), `SQLAlchemy 2.0 (Async)`, `FastAPI`, `httpx`, và `Playwright Async API`.

---

## 2. TỔNG QUAN HỆ THỐNG & TECH STACK

### 2.1. Mục tiêu hệ thống
Xây dựng nền tảng Web cho phép người dùng nhập bất kỳ đường link Google Form công khai nào (không yêu cầu đăng nhập Gmail) để:
1. Tự động phân tích câu hỏi, đáp án, thang đo Likert và luồng rẽ nhánh nhiều trang.
2. Cấu hình tỷ lệ phần trăm (%) cho từng đáp án hoặc gom nhóm câu hỏi tương quan chuẩn **SPSS / SmartPLS** (đảm bảo hệ số Cronbach's Alpha > 0.7).
3. Hỗ trợ sinh câu trả lời tự luận thông minh bằng **Gemini API** (cơ chế Batch Pre-generation) hoặc nạp dữ liệu từ file **Excel/CSV**.
4. Thực thi chiến dịch từ 50 đến hàng nghìn phản hồi với chế độ **Bắn tốc độ cao (Burst)** hoặc **Rải thời gian tự nhiên (Human-like Poisson Jitter)** qua hệ thống **Dual Engine (HTTPX + Proxy Pool -> Playwright Fallback)**.

### 2.2. Công nghệ sử dụng (Tech Stack)
* **Backend Framework:** Python 3.11+ & **FastAPI**
* **Database & Caching:** **PostgreSQL** (lưu trữ bền vững với `SQLAlchemy 2.0 Async` + `asyncpg`) & **Redis** (quản lý hàng đợi tác vụ, trạng thái chiến dịch real-time, cache câu trả lời AI).
* **Data Science & SPSS Engine:** `numpy`, `scipy`, `pandas`, `openpyxl`.
* **Execution Engine:** `httpx` (hỗ trợ HTTP/2 & Async Proxy) + `playwright` (Chromium Headless Fallback).
* **AI Integration:** `google-genai` (Model: `gemini-2.5-flash` với Structured Outputs).
* **Frontend Framework:** **React 18+ (Vite + TypeScript)**, **TailwindCSS**, **Shadcn/UI**, **Recharts** (biểu đồ phân phối), **Zustand** (State Management), **Lucide React** (Icons).

---

## 3. KIẾN TRÚC THƯ MỤC DỰ ÁN (MONOREPO STRUCTURE)

```text
auto-form-system/
├── backend/
│   ├── app/
│   │   ├── main.py                    # Entrypoint FastAPI, cấu hình CORS, Lifespan, WebSocket
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic BaseSettings đọc file .env
│   │   │   ├── database.py            # AsyncEngine, AsyncSessionLocal (PostgreSQL)
│   │   │   ├── redis_client.py        # Kết nối Redis Async
│   │   │   └── security.py            # JWT Token (python-jose) & Password Hashing (passlib/bcrypt)
│   │   ├── models/                    # SQLAlchemy 2.0 Declarative Models
│   │   │   ├── user.py
│   │   │   ├── form.py
│   │   │   ├── campaign.py
│   │   │   ├── question_rule.py
│   │   │   └── submission_log.py
│   │   ├── schemas/                   # Pydantic v2 Schemas (Request / Response DTOs)
│   │   │   ├── auth_schema.py
│   │   │   ├── form_schema.py
│   │   │   └── campaign_schema.py
│   │   ├── api/                       # API Routers
│   │   │   ├── deps.py                # Dependency Injection (get_db, get_current_user)
│   │   │   ├── auth_router.py
│   │   │   ├── form_router.py
│   │   │   ├── ai_router.py
│   │   │   ├── campaign_router.py
│   │   │   └── ws_router.py           # WebSocket bắn tiến độ real-time về React
│   │   ├── services/                  # Business Logic & Algorithms
│   │   │   ├── form_parser.py         # Bóc tách FB_PUBLIC_LOAD_DATA_ từ Google Form HTML
│   │   │   ├── spss_generator.py      # Thuật toán Numpy/Scipy sinh dữ liệu tương quan & trọng số
│   │   │   ├── excel_mapper.py        # Đọc Excel/CSV và ánh xạ cột vào entry_id
│   │   │   └── gemini_service.py      # Sinh hàng loạt câu trả lời tự luận (Batch Pre-generation)
│   │   └── workers/                   # Background Execution & Scheduling
│   │       ├── campaign_runner.py     # Điều phối chiến dịch, Poisson Jitter Scheduler
│   │       ├── http_submitter.py      # Bắn POST /formResponse bằng httpx + Proxy rotation
│   │       └── playwright_fallback.py # Mở trình duyệt Chromium điền form khi HTTP bị chặn
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── api/                       # Axios instances & API calls
    │   ├── components/
    │   │   ├── layout/                # Sidebar, Navbar, ProtectedRoute
    │   │   ├── form-config/           # ProbabilitySlider, SpssGroupModal, AiPoolPreview, ExcelUploader
    │   │   └── campaign/              # LiveProgressCard, SubmissionLogTable, DistributionChart
    │   ├── pages/
    │   │   ├── AuthPage.tsx           # Login / Register
    │   │   ├── DashboardPage.tsx      # Thống kê tổng quan & Danh sách chiến dịch
    │   │   ├── FormWorkspacePage.tsx  # Phân tích link Form, chỉnh tỷ lệ %, gom nhóm SPSS, cấu hình AI
    │   │   └── CampaignDetailPage.tsx # Màn hình theo dõi chạy Real-time qua WebSocket
    │   ├── store/                     # Zustand stores (authStore, formConfigStore)
    │   ├── types/                     # TypeScript interfaces khớp 100% với Pydantic Schemas
    │   └── App.tsx
    ├── package.json
    └── vite.config.ts
```

---

## 4. THIẾT KẾ CƠ SỞ DỮ LIỆU (POSTGRESQL SCHEMA)

Sử dụng `SQLAlchemy 2.0` với kiểu dữ liệu `JSONB` của PostgreSQL để lưu trữ linh hoạt cấu trúc Form và cấu hình xác suất.

### Bảng 1: `users` (Quản lý tài khoản)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `UUID` | PK, Default `uuid4` | Mã định danh người dùng |
| `email` | `VARCHAR(255)` | UNIQUE, NOT NULL, Index | Email đăng nhập |
| `password_hash` | `VARCHAR(255)` | NOT NULL | Mật khẩu mã hóa Bcrypt |
| `full_name` | `VARCHAR(100)` | NULLABLE | Tên hiển thị |
| `gemini_api_key` | `VARCHAR(255)` | NULLABLE | API Key cá nhân (nếu muốn ghi đè key hệ thống) |
| `created_at` | `TIMESTAMPTZ` | Default `now()` | Thời gian tạo |

### Bảng 2: `forms` (Lưu trữ Google Form đã phân tích)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `UUID` | PK | Mã định danh Form |
| `user_id` | `UUID` | FK (`users.id`), CASCADE | Người sở hữu |
| `title` | `VARCHAR(500)` | NOT NULL | Tiêu đề Google Form |
| `view_url` | `TEXT` | NOT NULL | Link `/viewform` gốc |
| `submit_url` | `TEXT` | NOT NULL | Link `/formResponse` để bắn POST |
| `parsed_structure` | `JSONB` | NOT NULL | Toàn bộ cấu trúc trang, câu hỏi, `entry_id`, rẽ nhánh |
| `created_at` | `TIMESTAMPTZ` | Default `now()` | Thời gian phân tích |

### Bảng 3: `campaigns` (Chiến dịch điền Form)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `UUID` | PK | Mã chiến dịch |
| `user_id` | `UUID` | FK (`users.id`) | Người tạo chiến dịch |
| `form_id` | `UUID` | FK (`forms.id`), CASCADE | Form mục tiêu |
| `name` | `VARCHAR(255)` | NOT NULL | Tên chiến dịch |
| `data_source` | `VARCHAR(50)` | `PROBABILITY` \| `EXCEL` | Nguồn sinh dữ liệu |
| `status` | `VARCHAR(50)` | `IDLE` \| `RUNNING` \| `PAUSED` \| `COMPLETED` \| `FAILED` | Trạng thái |
| `total_target` | `INTEGER` | NOT NULL | Tổng số form cần điền (VD: 500, 2000) |
| `completed_count`| `INTEGER` | Default `0` | Số form đã điền thành công |
| `failed_count` | `INTEGER` | Default `0` | Số form thất bại |
| `schedule_config`| `JSONB` | NOT NULL | `{"mode": "BURST" \| "SCHEDULED", "duration_minutes": 120, "concurrency": 20}` |
| `spss_groups` | `JSONB` | Default `[]` | Danh sách nhóm tương quan: `[{"group_id": "g1", "name": "Sự hài lòng", "mean": 4.1, "std": 0.6, "alpha_target": 0.8, "entries": ["111", "222"]}]` |
| `excel_data` | `JSONB` | NULLABLE | Dữ liệu các dòng đã đọc từ file Excel (nếu dùng mode `EXCEL`) |
| `proxy_list` | `JSONB` | Default `[]` | Danh sách chuỗi Proxy `http://user:pass@ip:port` |
| `use_playwright_fallback` | `BOOLEAN` | Default `True` | Cho phép bật Playwright khi HTTP lỗi |
| `created_at` | `TIMESTAMPTZ` | Default `now()` | Thời gian tạo |

### Bảng 4: `question_rules` (Luật sinh dữ liệu cho từng câu hỏi)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `UUID` | PK | Mã luật |
| `campaign_id` | `UUID` | FK (`campaigns.id`), CASCADE | Thuộc chiến dịch nào |
| `entry_id` | `VARCHAR(50)` | NOT NULL | Mã `entry.<id>` của Google Form (chỉ lưu phần số, VD: `"123456789"`) |
| `question_type` | `INTEGER` | NOT NULL | Mã loại câu hỏi của Google Form (0, 1, 2, 3, 4, 5, 7) |
| `config_json` | `JSONB` | NOT NULL | Lưu tỷ lệ % từng đáp án, nhóm tương quan SPSS, hoặc cấu hình AI |
| `cached_ai_pool` | `JSONB` | Default `[]` | Mảng các câu trả lời tự luận do Gemini sinh sẵn |

### Bảng 5: `submission_logs` (Lịch sử nộp từng phản hồi)
| Tên cột | Kiểu dữ liệu | Ràng buộc | Mô tả |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | Mã log tự tăng |
| `campaign_id` | `UUID` | FK (`campaigns.id`), INDEX | Thuộc chiến dịch nào |
| `sequence_number`| `INTEGER` | NOT NULL | Thứ tự mẫu (1 -> N) |
| `engine_used` | `VARCHAR(30)` | `HTTPX` \| `PLAYWRIGHT` | Công cụ đã thực thi |
| `status_code` | `INTEGER` | NOT NULL | HTTP Status (200 = Thành công) |
| `is_success` | `BOOLEAN` | NOT NULL | Trạng thái thành công |
| `payload_sent` | `JSONB` | NOT NULL | Dữ liệu thực tế đã gửi đi (phục vụ xuất CSV đối chiếu) |
| `error_detail` | `TEXT` | NULLABLE | Chi tiết lỗi nếu thất bại |
| `executed_at` | `TIMESTAMPTZ` | Default `now()` | Thời điểm nộp |

---

## 5. ĐẶC TẢ CHI TIẾT CÁC MODULE CỐT LÕI (CORE ENGINE SPECS)

### 5.1. Module 1: Bộ bóc tách Google Form (`services/form_parser.py`)

#### A. Cơ chế lấy dữ liệu
1. Nhận URL từ người dùng (có thể là link rút gọn `forms.gle/...` hoặc `docs.google.com/forms/d/e/.../viewform`).
2. Dùng `httpx.AsyncClient(follow_redirects=True)` tải nội dung HTML.
3. Trích xuất URL cuối cùng sau khi redirect, thay thế hậu tố `/viewform.*` bằng `/formResponse` để làm `submit_url`.
4. Trích xuất token bảo mật `fbzx` từ thẻ `<input type="hidden" name="fbzx" value="...">` (nếu có).
5. Dùng Regex trích xuất biến JavaScript `FB_PUBLIC_LOAD_DATA_`:
   ```python
   pattern = re.compile(r'var\s+FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);\s*</script>', re.DOTALL)
   ```
6. Parse chuỗi vừa tìm được bằng `json.loads()`.

#### B. Quy tắc giải mã mảng `FB_PUBLIC_LOAD_DATA_`
* Tiêu đề Form nằm tại: `raw_data[1][8]` hoặc `raw_data[3]`.
* Danh sách toàn bộ các phần tử (câu hỏi & tiêu đề trang) nằm tại mảng: `items = raw_data[1][1]`.
* Duyệt qua từng `item` trong `items`:
  * `item_id = item[0]`
  * `title = item[1]` (Tên câu hỏi hoặc tên Trang/Section)
  * `description = item[2]`
  * `type_id = item[3]` (Mã loại phần tử)

#### C. Bảng ánh xạ `type_id` của Google Form
* **`type_id == 8` (Page Break / Section Header):** Đánh dấu bắt đầu một trang mới (`page_index += 1`). Mặc định Form bắt đầu ở `page_index = 0`.
* **`type_id in [0, 1, 2, 3, 4, 5, 7]` (Các câu hỏi cần điền):**
  * Dữ liệu chi tiết câu hỏi nằm trong `question_meta = item[4]`.
  * **Lưu ý đặc biệt với Grid (`type_id == 7`):** `item[4]` chứa nhiều phần tử con, mỗi phần tử con là 1 hàng (row) trong bảng Grid và có `entry_id` riêng tại `sub_item[0]`.
  * **Với các câu hỏi thông thường (`0, 1, 2, 3, 4, 5`):**
    * `entry_id = str(item[4][0][0])`
    * `is_required = bool(item[4][0][2])` (1 là bắt buộc, 0 là không bắt buộc)
    * Danh sách lựa chọn (nếu có) nằm tại `raw_options = item[4][0][1]`:
      * Mỗi `opt` trong `raw_options` có:
        * `opt_value = opt[0]` (Giá trị chữ của đáp án, nếu `opt[0] == ""` và có `opt[4] == 1` thì đó là ô **"Mục khác / Other"**).
        * `go_to_page_action = opt[2]` (Nếu khác `None`, đây là luật rẽ nhánh khi chọn đáp án này: `-2` là Nộp biểu mẫu ngay, `-1` là Sang trang tiếp theo, hoặc một số nguyên dương là `item_id` của Section `type_id == 8` cần nhảy tới).

#### D. Cấu trúc JSON chuẩn hóa đầu ra của `form_parser.py`
```json
{
  "title": "Khảo sát hành vi tiêu dùng sinh viên",
  "view_url": "https://docs.google.com/forms/d/e/1FAIpQL.../viewform",
  "submit_url": "https://docs.google.com/forms/d/e/1FAIpQL.../formResponse",
  "fbzx": "-48291049281920",
  "total_pages": 3,
  "sections": [
    {
      "page_index": 0,
      "section_item_id": null,
      "title": "Trang mở đầu",
      "navigation_action": "NEXT_PAGE"
    },
    {
      "page_index": 1,
      "section_item_id": 987654321,
      "title": "Phần 2: Đánh giá chi tiết",
      "navigation_action": "NEXT_PAGE"
    }
  ],
  "questions": [
    {
      "item_id": 11223344,
      "entry_id": "123456789",
      "title": "Bạn thuộc giới tính nào?",
      "description": null,
      "type_id": 2,
      "type_name": "MULTIPLE_CHOICE",
      "page_index": 0,
      "is_required": true,
      "options": [
        {"label": "Nam", "value": "Nam", "is_other": false, "jump_to_section_id": null},
        {"label": "Nữ", "value": "Nữ", "is_other": false, "jump_to_section_id": 987654321}
      ]
    }
  ]
}
```

---

### 5.2. Module 2: Thuật toán Sinh dữ liệu & Tương quan SPSS (`services/spss_generator.py`)

Module này chịu trách nhiệm sinh ra một danh sách `N` bộ câu trả lời hoàn chỉnh trước hoặc trong khi bắn.

#### A. Xử lý câu hỏi độc lập theo Trọng số phần trăm (`Weighted Probability`)
1. **Radio (`type_id = 2`), Dropdown (`type_id = 3`), Linear Scale (`type_id = 5`):**
   * Người dùng cấu hình mảng trọng số $W = [w_1, w_2, \dots, w_k]$ (tổng bằng 100).
   * Chuẩn hóa xác suất $P_i = \frac{w_i}{\sum w}$ và dùng `numpy.random.choice(options, p=P)` để lấy 1 đáp án.
2. **Checkbox - Chọn nhiều đáp án (`type_id = 4`):**
   * Người dùng cấu hình xác suất xuất hiện độc lập cho từng ô Checkbox (từ 0% đến 100%) và giới hạn `[min_checked, max_checked]`.
   * Với mỗi lựa chọn $i$, sinh số ngẫu nhiên $u \sim U(0, 100)$, nếu $u \le w_i$ thì chọn đáp án đó. Nếu số lượng chọn chưa đạt `min_checked` (hoặc câu hỏi `is_required=True` mà có 0 lựa chọn), tự động lấy bù theo trọng số cao nhất.

#### B. Thuật toán Tương quan Nhóm câu hỏi chuẩn SPSS / SmartPLS (Multivariate Normal Latent Factor)
Để dữ liệu khi đưa vào phần mềm **SPSS** chạy kiểm định độ tin cậy **Cronbach's Alpha đạt $\ge 0.75$** và phân tích nhân tố khám phá **EFA** hội tụ chuẩn:
1. Người dùng gom $m$ câu hỏi thang đo Likert (ví dụ từ $1$ đến $5$) vào một nhóm nhân tố $G$, thiết lập Điểm trung bình mục tiêu $\mu \in [1.0, 5.0]$, Độ lệch chuẩn $\sigma \in [0.4, 1.2]$ và Hệ số tương quan kỳ vọng giữa các biến quan sát $r \in [0.60, 0.85]$.
2. Xây dựng vector kỳ vọng $\boldsymbol{\mu} = [\mu, \mu, \dots, \mu]^T$ kích thước $m$.
3. Xây dựng ma trận hiệp phương sai $\boldsymbol{\Sigma}$ kích thước $m \times m$:
   $$\Sigma_{ij} = \begin{cases} \sigma^2 & \text{nếu } i = j \\ r \cdot \sigma^2 & \text{nếu } i \neq j \end{cases}$$
4. Sinh đồng thời $N$ mẫu bằng phân phối chuẩn nhiều chiều:
   ```python
   raw_samples = np.random.multivariate_normal(mean=mean_vec, cov=cov_matrix, size=N)
   # Giới hạn biên [scale_min, scale_max] và làm tròn thành số nguyên
   likert_samples = np.clip(np.round(raw_samples), scale_min, scale_max).astype(int)
   ```
5. Tính thử hệ số **Cronbach's Alpha** ngay trong Python để hiển thị lên UI Preview cho người dùng xem trước khi bấm chạy:
   $$\alpha = \frac{m}{m - 1} \left( 1 - \frac{\sum_{i=1}^{m} \text{Var}(X_i)}{\text{Var}\left(\sum_{i=1}^{m} X_i\right)} \right)$$

#### C. Thuật toán Tính toán Đường đi Rẽ nhánh (`pageHistory` Builder)
Với mỗi mẫu phản hồi thứ $k$:
1. Bắt đầu tại `current_page = 0`, khởi tạo danh sách `visited_pages = [0]`.
2. Chỉ lấy dữ liệu các câu hỏi thuộc `current_page`.
3. Kiểm tra xem trong các câu hỏi trắc nghiệm thuộc `current_page`, đáp án vừa được chọn có thuộc tính `jump_to_section_id` khác `None` hay không:
   * Nếu `jump_to_section_id == -2` (Submit Form): Dừng vòng lặp ngay lập tức, xóa bỏ mọi câu trả lời ở các trang sau để tránh gửi dữ liệu thừa bất hợp lệ.
   * Nếu `jump_to_section_id > 0`: Tìm `page_index` tương ứng với `section_item_id == jump_to_section_id`, gán `current_page = target_page_index`.
   * Nếu không có lệnh rẽ nhánh: Tăng `current_page += 1`.
4. Thêm `current_page` vào `visited_pages` và lặp lại cho đến khi hết trang.
5. Ghép chuỗi `pageHistory = ",".join(map(str, visited_pages))` (Ví dụ: `"0,1,3"`).

---

### 5.3. Module 3: Tích hợp Gemini AI sinh Tự luận (`services/gemini_service.py`)

**Nguyên tắc tối ưu:** Tuyệt đối KHÔNG gọi Gemini API trực tiếp trong từng request bắn form để tránh nghẽn cổ chai và lỗi Rate Limit `429`. Sử dụng cơ chế **Batch Pre-generation**.

```python
from google import genai
from google.genai import types
from pydantic import BaseModel

class GeneratedAnswersResponse(BaseModel):
    answers: list[str]

async def generate_answer_pool(
    question_title: str,
    survey_context: str,
    sample_count: int = 50,
    persona_hint: str = "Sinh viên đại học tại Việt Nam, trả lời tự nhiên, đa dạng độ dài từ 5 đến 25 từ"
) -> list[str]:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = f"""
    Bạn đang tham gia điền một khảo sát có chủ đề: "{survey_context}".
    Câu hỏi tự luận là: "{question_title}".
    Phong cách người điền: {persona_hint}.
    Hãy sinh ra đúng {sample_count} câu trả lời hoàn toàn khác nhau, tự nhiên như người thật gõ (có câu ngắn gọn, câu chi tiết, không dùng văn phong liệt kê máy móc của AI).
    """
    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=GeneratedAnswersResponse,
            temperature=0.9,
        ),
    )
    parsed: GeneratedAnswersResponse = response.parsed
    return parsed.answers
```
* **Biến thể hóa khi bắn hàng nghìn form:** Nếu chiến dịch cần điền 2.000 form mà Pool chỉ có 100 câu, hệ thống bốc ngẫu nhiên từ Pool và áp dụng hàm **Micro-Mutation** (ngẫu nhiên viết hoa/thường chữ cái đầu, bỏ dấu chấm cuối câu, hoặc trộn 2 vế câu ngắn) để không bị trùng lặp 100%.

---

### 5.4. Module 4: Bộ Lập lịch & Thực thi Kép (`workers/`)

#### A. Đóng gói Payload chuẩn Google Form (`http_submitter.py`)
Khi gửi POST tới `submit_url` (`/formResponse`), header phải có `Content-Type: application/x-www-form-urlencoded`. Do câu hỏi Checkbox (`type_id = 4`) có nhiều đáp án trùng khóa `entry.<id>`, bắt buộc truyền vào `httpx` dưới dạng **danh sách các tuple `list[tuple[str, str]]`**:
```python
payload_tuples: list[tuple[str, str]] = [
    ("entry.123456789", "Nam"),
    ("entry.987654321", "Lựa chọn Checkbox 1"),
    ("entry.987654321", "Lựa chọn Checkbox 2"),
    ("fvv", "1"),
    ("pageHistory", "0,1,2"),
    ("fbzx", fbzx_token),
]
```
* Nếu chọn đáp án **"Mục khác (Other)"**, gửi cặp tuple:
  * `("entry.123456789", "__other_option__")`
  * `("entry.123456789.other_option_response", "Nội dung tự điền vào ô Other")`

#### B. Thuật toán Rải thời gian tự nhiên (`Poisson Jitter Scheduler`)
Khi người dùng chọn chế độ `SCHEDULED` (Ví dụ: Điền $N = 500$ form trong $T = 120$ phút = $7200$ giây):
1. Khoảng nghỉ trung bình: $\lambda = \frac{7200}{500} = 14.4$ giây.
2. Sinh mảng thời gian chờ giữa các lần nộp bằng phân phối mũ:
   ```python
   delays = np.random.exponential(scale=14.4, size=N)
   # Chuẩn hóa lại để tổng thời gian khớp chính xác 7200 giây
   delays = delays * (7200.0 / np.sum(delays))
   ```
3. Trước mỗi lần bắn mẫu thứ $i$, worker thực hiện `await asyncio.sleep(delays[i])`, đồng thời kiểm tra cờ trạng thái trong Redis xem người dùng có bấm **Tạm dừng (Pause)** hoặc **Hủy (Cancel)** không.

#### C. Luồng Chuyển đổi dự phòng (`HTTPX` -> `Proxy Rotation` -> `Playwright Fallback`)
1. **Bước 1:** Gửi bằng `httpx.AsyncClient` (với `User-Agent` xoay vòng ngẫu nhiên và Proxy nếu có). Kiểm tra `response.status_code == 200` và nội dung trả về không chứa chuỗi báo lỗi xác thực.
2. **Bước 2:** Nếu gặp lỗi `429 Too Many Requests`, `403 Forbidden`, hoặc `400 Bad Request` (do form có validation JS phức tạp), thử lại tối đa 2 lần với IP Proxy mới.
3. **Bước 3 (Playwright Fallback):** Nếu vẫn thất bại và `use_playwright_fallback == True`, gọi `playwright_fallback.py`:
   * Mở `browser.new_context()` với `playwright.async_api`.
   * Truy cập `view_url`.
   * Ở mỗi trang, tìm câu hỏi theo thuộc tính `data-params` (chứa `entry_id` hoặc `item_id`), thực hiện click/fill đáp án tương ứng.
   * Bấm nút `"Tiếp"` (`Next`) hoặc `"Gửi"` (`Submit`) và chờ URL chuyển hướng sang `/formResponse` để xác nhận thành công.

---

## 6. ĐẶC TẢ RESTFUL API & WEBSOCKET (FASTAPI ENDPOINTS)

### 6.1. Nhóm Xác thực (`auth_router.py`)
* `POST /api/v1/auth/register`: Đăng ký tài khoản mới.
* `POST /api/v1/auth/login`: Trả về `access_token` (JWT).
* `GET /api/v1/auth/me`: Lấy thông tin user hiện tại và cấu hình Gemini API Key.

### 6.2. Nhóm Phân tích Form & AI (`form_router.py` & `ai_router.py`)
* `POST /api/v1/forms/parse`:
  * **Input:** `{"url": "https://docs.google.com/forms/..."}`
  * **Output:** Bản ghi `Form` kèm toàn bộ `parsed_structure` (danh sách trang, câu hỏi, `entry_id`, các lựa chọn).
* `POST /api/v1/ai/generate-pool`:
  * **Input:** `{"question_title": "...", "survey_context": "...", "count": 50, "persona": "..."}`
  * **Output:** `{"answers": ["Câu 1", "Câu 2", ...]}`
* `POST /api/v1/forms/{form_id}/parse-excel`:
  * **Input:** `UploadFile` (`.xlsx` hoặc `.csv`).
  * **Output:** Danh sách tên cột trong Excel và gợi ý ghép cặp tự động (Auto-mapping) với `entry_id` dựa trên độ giống nhau của tiêu đề câu hỏi.

### 6.3. Nhóm Quản lý & Thực thi Chiến dịch (`campaign_router.py`)
* `POST /api/v1/campaigns`: Tạo chiến dịch mới cùng toàn bộ `question_rules` và `spss_groups`.
* `POST /api/v1/campaigns/preview-spss`:
  * **Input:** Cấu hình `spss_groups` và `question_rules`.
  * **Output:** Chạy thử 200 mẫu trong RAM, tính toán và trả về chỉ số **Cronbach's Alpha dự kiến**, trung bình (Mean), độ lệch chuẩn (SD) để hiển thị ngay trên giao diện trước khi chạy thật.
* `POST /api/v1/campaigns/{id}/start`: Đẩy chiến dịch vào Background Task (`asyncio.create_task`) và bắt đầu chạy.
* `POST /api/v1/campaigns/{id}/pause` & `POST /api/v1/campaigns/{id}/resume`: Tạm dừng / Tiếp tục chiến dịch.
* `GET /api/v1/campaigns/{id}/export-csv`: Xuất toàn bộ dữ liệu đã gửi (`payload_sent` từ bảng `submission_logs`) ra file CSV/Excel để người dùng có thể mở đối chiếu trực tiếp trên SPSS.

### 6.4. WebSocket Real-time (`ws_router.py`)
* `WS /ws/campaigns/{campaign_id}`:
  * Mỗi khi một phản hồi được gửi xong, Worker bắn một message JSON qua WebSocket:
    ```json
    {
      "event": "SUBMISSION_UPDATE",
      "campaign_id": "...",
      "sequence_number": 142,
      "completed_count": 140,
      "failed_count": 2,
      "engine_used": "HTTPX",
      "status_code": 200,
      "next_delay_seconds": 8.4,
      "timestamp": "2026-11-02T14:05:22Z"
    }
    ```

---

## 7. ĐẶC TẢ GIAO DIỆN NGƯỜI DÙNG (REACT FRONTEND WORKFLOW)

Giao diện được thiết kế theo phong cách **Modern SaaS Dashboard (Dark/Light Mode)** với 3 màn hình chính:

### Màn hình 1: Không gian Cấu hình Khảo sát (`FormWorkspacePage.tsx`)
1. **Thanh nhập URL:** Ô dán link Google Form + Nút `"Phân tích cấu trúc Form"`.
2. **Chuyển đổi chế độ nguồn dữ liệu (Tabs):**
   * **Tab 1 - Ma trận Trọng số & SPSS:**
     * Hiển thị từng câu hỏi theo từng Trang (Section).
     * Với câu hỏi Trắc nghiệm / Likert: Hiển thị các thanh trượt (`Slider`) chỉnh tỷ lệ % cho từng đáp án + các nút Preset nhanh: `"Phân phối đều"`, `"Phân phối chuẩn (Hình chuông)"`, `"Nghiêng về Đồng ý (4-5 điểm)"`.
     * Với câu hỏi Tự luận: Ô nhập ngữ cảnh + Nút `"Dùng Gemini sinh 50 câu trả lời"` + Bảng xem trước & chỉnh sửa các câu AI đã sinh.
   * **Tab 2 - Trình quản lý Nhóm tương quan SPSS (`SpssGroupModal`):**
     * Cho phép tích chọn nhiều câu hỏi Likert (VD: `HD1, HD2, HD3, HD4`), đặt tên nhân tố, chọn điểm trung bình mục tiêu (VD: `4.2`), hệ số tương quan (`0.75`) và bấm `"Kiểm tra thử Cronbach's Alpha"`.
   * **Tab 3 - Điền từ File Excel/CSV (`ExcelUploader`):**
     * Kéo thả file `.xlsx`, hiển thị bảng nối Cột Excel $\leftrightarrow$ Câu hỏi Google Form và xem trước 5 dòng đầu tiên.
3. **Panel Cài đặt Thực thi (Bên phải):**
   * Nhập số lượng mẫu cần điền (VD: `500`).
   * Chọn chế độ: **Tốc độ tối đa (Burst)** hoặc **Rải đều tự nhiên (Scheduled Jitter - nhập số phút)**.
   * Ô nhập danh sách Proxy (tùy chọn) và nút gạt bật/tắt **Playwright Fallback**.

### Màn hình 2: Trung tâm Giám sát Chiến dịch Real-time (`CampaignDetailPage.tsx`)
1. **4 Thẻ KPI:** Tiến độ hoàn thành (`140 / 500` - `28%`), Tỷ lệ thành công (`98.6%`), Tốc độ trung bình / Thời gian còn lại (ETA), Số lần kích hoạt Playwright Fallback.
2. **Thanh Progress Bar động & Nút điều khiển:** Tạm dừng (Pause), Tiếp tục (Resume), Xuất dữ liệu đã điền ra CSV.
3. **Biểu đồ Real-time (`Recharts`):** Biểu đồ cột hiển thị phân phối đáp án thực tế đang được gửi đi và đường thời gian nộp bài.
4. **Live Terminal Log:** Bảng cuộn tự động hiển thị từng mẫu vừa nộp (`#142 - [HTTPX] - 200 OK - Thời gian nghỉ tiếp theo: 6.2s`).

---

## 8. KẾ HOẠCH TRIỂN KHAI TỪNG BƯỚC CHO CLAUDE (IMPLEMENTATION PHASES)

Khi bạn đưa file này cho Claude, hãy yêu cầu Claude code lần lượt theo **4 Phase** dưới đây để kiểm soát chất lượng tốt nhất:

* **Phase 1 (Core Engine & Database):** Viết `config.py`, `database.py`, 5 Models SQLAlchemy, `form_parser.py` (bóc tách `FB_PUBLIC_LOAD_DATA_`) và `spss_generator.py` (thuật toán trọng số, tương quan SPSS, tính toán `pageHistory`).
* **Phase 2 (AI, Excel & Dual Execution Workers):** Viết `gemini_service.py`, `excel_mapper.py`, `http_submitter.py`, `playwright_fallback.py` và `campaign_runner.py` (Poisson Jitter Scheduler + Redis state).
* **Phase 3 (FastAPI Routers & WebSocket):** Hoàn thiện toàn bộ REST API endpoints, JWT Auth và WebSocket `/ws/campaigns/{id}` cùng file `main.py` và `requirements.txt`.
* **Phase 4 (React Frontend):** Khởi tạo khung Vite + TypeScript + TailwindCSS và xây dựng các trang `AuthPage`, `FormWorkspacePage`, `CampaignDetailPage` kết nối đầy đủ API và WebSocket.
