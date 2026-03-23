# PLAN: Chuyển text giao diện sang tiếng Việt có dấu

## Mục tiêu

- Chuyển **toàn bộ** text hiển thị trên giao diện web (frontend) từ tiếng Việt không dấu → **có dấu đầy đủ**
- Chuyển text response trong backend API (trend labels, error messages) sang tiếng Việt có dấu
- Cập nhật `<title>` và `lang` trong `index.html`

## Non-goals

- Không thay đổi logic code, chỉ thay đổi string literals
- Không dịch các thuật ngữ tiếng Anh chuyên ngành (SHAP, RSI, MACD, XAU/USD, SJC, VaR...)
- Không thay đổi code comments
- Không thay đổi CSS class names hay variable names

## Bối cảnh hiện trạng

Text hiện tại viết tiếng Việt **không dấu** để tránh encoding issues. Nhưng codebase đã dùng UTF-8 đúng, React/Vite hỗ trợ Unicode tốt, nên hoàn toàn có thể dùng tiếng Việt có dấu.

---

## Các thay đổi dự kiến

### 1. [MODIFY] `frontend/index.html`

| Dòng | Cũ | Mới |
|------|-----|-----|
| 2 | `<html lang="en">` | `<html lang="vi">` |
| 7 | `<title>eworkfinancetradingfrontend</title>` | `<title>Gold Predictor - Dự đoán giá vàng</title>` |

---

### 2. [MODIFY] `frontend/src/App.jsx` — Text mapping

#### Header & Loading/Error
| Vị trí | Cũ (không dấu) | Mới (có dấu) |
|--------|----------------|---------------|
| L97 | `SJC Ban` | `SJC Bán` |
| L99 | `Mua:` | `Mua:` (✅ OK) |
| L109 | `Du lieu trong DB` | `Dữ liệu trong DB` |
| L120 | `Bieu do gia vang XAU/USD (1 nam)` | `Biểu đồ giá vàng XAU/USD (1 năm)` |
| L121 | `Lam moi` | `Làm mới` |
| L130 | `Du doan` | `Dự đoán` |
| L132 | `Dang chay...` / `Cap nhat` / `Chay du doan` | `Đang chạy...` / `Cập nhật` / `Chạy dự đoán` |
| L136 | `Dang train ML models...` | `Đang huấn luyện ML models...` |
| L142-143 | `Bam "Chay du doan" de khoi chay ML models` / `(lan dau mat ~30 giay)` | `Bấm "Chạy dự đoán" để khởi chạy ML models` / `(lần đầu mất ~30 giây)` |
| L153 | `Vang Viet Nam (SJC)` | `Vàng Việt Nam (SJC)` |
| L157 | `Phan tich Premium SJC` | `Phân tích Premium SJC` |
| L163 | `Du doan gia SJC` | `Dự đoán giá SJC` |
| L169 | `Bam "Chay du doan" o tren` | `Bấm "Chạy dự đoán" ở trên` |
| L181 | `Tai sao model du doan nhu vay? (SHAP)` | `Tại sao model dự đoán như vậy? (SHAP)` |
| L192 | `Loi khuyen dau tu` | `Lời khuyên đầu tư` |
| L199 | `Chi bao ky thuat` | `Chỉ báo kỹ thuật` |
| L210 | `Phan tich thi truong` | `Phân tích thị trường` |
| L222 | `V2 Dashboard` | `Bảng điều khiển V2` |
| L248 | `System Online` | `Hệ thống hoạt động` |
| L257 | `Dang tai du lieu...` | `Đang tải dữ liệu...` |
| L267 | `Thu lai` | `Thử lại` |

#### Component PremiumPanel
| Vị trí | Cũ | Mới |
|--------|-----|-----|
| L354 | `Khong co du lieu SJC` | `Không có dữ liệu SJC` |
| L366 | `Gia the gioi quy doi` | `Giá thế giới quy đổi` |
| L372 | `SJC thuc te (Ban)` | `SJC thực tế (Bán)` |
| L392 | `Premium cao bat thuong (binh thuong 3-8%)` | `Premium cao bất thường (bình thường 3-8%)` |

#### Component VNPredictPanel
| Vị trí | Cũ | Mới |
|--------|-----|-----|
| L416 | `Du doan {horizon}` | `Dự đoán {horizon}` |
| L421 | `SJC Mua (du doan)` | `SJC Mua (dự đoán)` |
| L427 | `SJC Ban (du doan)` | `SJC Bán (dự đoán)` |

#### Component AdvisorPanel
| Vị trí | Cũ | Mới |
|--------|-----|-----|
| L513 | `Do tin cay` | `Độ tin cậy` |

#### Error message trong loadData
| Vị trí | Cũ | Mới |
|--------|-----|-----|
| L41 | `Khong the tai du lieu. Hay dam bao backend dang chay.` | `Không thể tải dữ liệu. Hãy đảm bảo backend đang chạy.` |

---

### 3. [MODIFY] `backend/app/api/routes/gold_routes.py` — API responses

| Dòng | Cũ | Mới |
|------|-----|-----|
| L87 | `Khong co du lieu cho {source}` | `Không có dữ liệu cho {source}` |
| L139 | `trend_map = {0: "Giam", 1: "Sideway", 2: "Tang"}` | `trend_map = {0: "Giảm", 1: "Đi ngang", 2: "Tăng"}` |
| L167 | `trend_map = {0: "Giam", ...}` (lặp) | `trend_map = {0: "Giảm", 1: "Đi ngang", 2: "Tăng"}` |
| L198 | `Khong co du lieu de phan tich` | `Không có dữ liệu để phân tích` |
| L301 | `Khong lay duoc du lieu giavang.org` | `Không lấy được dữ liệu giavang.org` |
| L339 | `trend_map = {0: "Giam", ...}` (lặp) | `trend_map = {0: "Giảm", 1: "Đi ngang", 2: "Tăng"}` |

---

## Rủi ro / Edge cases

| Risk | Mức độ | Giải pháp |
|------|--------|-----------|
| Frontend trend_probabilities keys (`giam`, `tang`) đến từ backend | 🟡 | Keys giữ nguyên (internal), chỉ đổi display labels |
| SHAP direction value `tang` dùng trong SHAPPanel | 🟢 | Giữ nguyên key, chỉ đổi UI text |
| CSS class names `trend-giam`, `trend-tang` | 🟢 | Giữ nguyên, đây là class names |
| Backend log messages | 🟢 | Không đổi (chỉ đổi user-facing text) |

---

## Test plan

### Manual Verification

1. Mở browser tại `http://localhost:5173`
2. Kiểm tra tab title = `Gold Predictor - Dự đoán giá vàng`
3. Kiểm tra **tất cả** text có dấu trên trang chính
4. Bấm "Chạy dự đoán" → kiểm tra text loading + prediction labels
5. Kiểm tra trend labels hiện `Giảm` / `Đi ngang` / `Tăng`

### Automated

```bash
cd backend && python -m pytest tests/ -v --tb=short
cd frontend && npx vite build
```

---

## Những điểm dễ thay đổi tương lai

- **Nên tách text thành file i18n riêng** nếu muốn hỗ trợ đa ngôn ngữ
- **trend_map** có thể đưa vào constants.py để reuse
