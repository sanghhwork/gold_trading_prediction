---
name: vn-gold-prediction
description: Dự đoán giá vàng Việt Nam (SJC) từ XAU/USD + tỷ giá + premium analysis
---

# 🇻🇳 Skill: Dự đoán Giá Vàng Việt Nam

## Mục đích
Dự đoán giá vàng SJC/DOJI/PNJ trong nước từ giá vàng thế giới (XAU/USD), tỷ giá USD/VND, và premium lịch sử.

## Công thức cơ bản
```
SJC (VND/lượng) = XAU/USD × USD/VND × (37.5 / 31.1035) + premium
```

Trong đó:
- `37.5g` = 1 lượng vàng Việt Nam
- `31.1035g` = 1 troy ounce (đơn vị quốc tế)
- `premium` = phần chênh lệch SJC so với thế giới (thường 5-15 triệu VND)

## Cách sử dụng

### 1. Phân tích giá VN hiện tại
```bash
GET http://localhost:8001/api/v1/gold/vn
```
Trả về:
- Giá XAU/USD mới nhất
- Giá SJC quy đổi từ thế giới
- Giá SJC thực tế (nếu có)
- Premium analysis (% chênh lệch)

### 2. Dự đoán giá SJC
```bash
GET http://localhost:8001/api/v1/gold/vn/predict?horizon=7d
```
Trả về:
- Giá XAU/USD dự đoán (từ ML model)
- Giá SJC buy/sell dự kiến (VND/lượng)
- Premium ước lượng
- Công thức quy đổi

### 3. Giải thích dự đoán
```bash
GET http://localhost:8001/api/v1/predictions/7d/explain
```
Trả về:
- Top 8 yếu tố ảnh hưởng (SHAP values)
- Mỗi yếu tố: tên, giá trị, hướng tác động (tăng/giảm), mức độ
- Context giải thích (vd: "DXY giảm → USD yếu → vàng tăng")

## Nguồn dữ liệu SJC

| Nguồn | Vai trò | Endpoint |
|-------|---------|----------|
| sjc.com.vn | Primary | `POST /GoldPrice/Services/PriceService.ashx` |
| giavang.net | Fallback | `GET api2.giavang.net/v1/gold/last-price` |

## Files liên quan

| File | Mô tả |
|------|--------|
| `backend/app/services/models/vn_gold_predictor.py` | VN gold price converter + predictor |
| `backend/app/services/data_collector/sjc_collector.py` | SJC price scraper (2 nguồn) |
| `backend/app/services/ai_reasoning/prediction_explainer.py` | SHAP-based explanation |
| `backend/app/api/routes/gold_routes.py` | API endpoints |

## Lưu ý quan trọng

> ⚠️ Premium SJC biến động mạnh (5-20 triệu VND) tùy cung-cầu nội địa, chính sách NHNN.
> Model hiện tại ước lượng premium từ dữ liệu gần nhất, chưa predict premium riêng.

## Mở rộng tương lai
- [ ] ML model riêng cho premium prediction
- [ ] Thêm DOJI, PNJ, Bảo Tín price sources
- [ ] Historical premium trend analysis
- [ ] NHNN policy impact analysis
