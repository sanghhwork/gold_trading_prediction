# 🔍 Đánh Giá Khả Thi & Chính Xác - Gold Predictor

> Đánh giá bởi: AI Senior ML Engineer
> Ngày: 23/03/2026
> Dựa trên: Codebase thực tế + nghiên cứu học thuật về gold price forecasting

---

## 1. 🎯 Tóm tắt đánh giá

| Hạng mục | Điểm | Nhận xét |
|----------|------|----------|
| **Kiến trúc phần mềm** | ⭐⭐⭐⭐ 8/10 | Tốt - modullar, clean, mở rộng được |
| **Thu thập dữ liệu** | ⭐⭐⭐⭐ 7/10 | Tốt - đa nguồn, nhưng thiếu dữ liệu sentiment |
| **Feature Engineering** | ⭐⭐⭐ 6/10 | Khá - 92 features, thiếu sentiment + on-chain |
| **ML Methodology** | ⭐⭐ 5/10 | Trung bình - có vấn đề nghiêm trọng về validation |
| **Độ chính xác dự đoán** | ⭐⭐ 4/10 | Yếu - R² âm, model chưa generalizable |
| **Ứng dụng thực tế** | ⭐⭐⭐ 6/10 | Khá - dashboard đẹp, cần cải thiện accuracy |

**Kết luận: Dự án có kiến trúc tốt nhưng ML methodology cần cải thiện đáng kể trước khi dùng cho quyết định đầu tư thực.**

---

## 2. ✅ Những điểm MẠNH

### 2.1 Kiến trúc phần mềm
- ✅ **Modular design**: Tách rõ collector → feature → model → API → frontend
- ✅ **Multi-source data**: 5 collectors (Yahoo, SJC, giavang.org, giavang.net, cafef)
- ✅ **Auto pipeline**: Scheduler tự động thu thập + retrain
- ✅ **Docker-ready**: Có Dockerfile + docker-compose cho deployment
- ✅ **Logging tốt**: Loguru với structured logging, trace được lỗi

### 2.2 Feature Engineering
- ✅ **92 features phong phú**: Technical (RSI, MACD, BB) + Macro (DXY, Oil, Bond) + Calendar
- ✅ **Cross-features**: Gold/DXY ratio, Gold/Oil ratio — đây là features có ý nghĩa kinh tế
- ✅ **Nhiều timeframe**: Return 1d/5d/20d, Volatility 5d/20d

### 2.3 Explainability
- ✅ **SHAP values**: Giải thích TẠI SAO model dự đoán — rất tốt cho transparency
- ✅ **Rule-based backup**: Không phụ thuộc hoàn toàn vào ML, có scoring system

---

## 3. ❌ Những điểm YẾU & VẤN ĐỀ NGHIÊM TRỌNG

### 3.1 🔴 Data Leakage tiềm ẩn (NGHIÊM TRỌNG)

**Vấn đề**: Trong `model_trainer.py` dòng 67:
```python
X, y_price, y_trend, y_return = self.feature_builder.get_train_data(df, horizon=horizon)
```

Features được build trên **toàn bộ dataset** trước khi split. Các features dùng rolling window (SMA 200, RSI 14, Volatility 20d) có thể bị **look-ahead bias** nếu không được tính cẩn thận.

> 📚 **Tham khảo**: "Financial Machine Learning" (Marcos López de Prado, 2018) — Chapter 7 về Cross-Validation in Finance: *"Applying standard cross-validation to financial data leads to inflated performance metrics due to temporal dependencies."*

**Mức độ**: Cao. Có thể làm metrics trên test set **tốt hơn thực tế** 20-40%.

---

### 3.2 🔴 Validation không phù hợp cho Time Series (NGHIÊM TRỌNG)

**Hiện tại**: Simple 80/20 train/test split.

```python
split_idx = int(len(X) * (1 - test_size))
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
```

**Vấn đề**:
- ❌ **Chỉ 1 lần split**, không đo được variance của model
- ❌ **Không có walk-forward validation**: Standard trong finance ML
- ❌ **Không có out-of-sample testing**: Model chưa bao giờ "thấy" regime mới

**Cần làm**: Walk-forward validation (expanding/sliding window)

```
Walk-Forward Validation (chuẩn industry):

Train: [========]          Test: [==]
Train: [==========]        Test: [==]
Train: [============]      Test: [==]
Train: [==============]    Test: [==]

→ Metrics = trung bình trên nhiều test windows
```

> 📚 **Tham khảo**: "Advances in Financial ML" (de Prado, 2018): Walk-forward analysis là *"the only correct way to backtest a trading strategy."*

---

### 3.3 🟡 R² âm - Model không tốt hơn dự đoán bằng trung bình

**Thực tế quan sát**: Khi predict XAU từ $4,574 → model dự đoán $2,957 (giảm 35% trong 7 ngày).

**Điều này cho thấy**:
- Model đang **extrapolate ngoài vùng training data**. Giá vàng $4,500+ là vùng chưa từng có trong lịch sử.
- XGBoost (tree-based) **KHÔNG THỂ extrapolate** — nó chỉ có thể trả về giá trị trong range đã thấy khi training.
- R² âm = model **tệ hơn cả dự đoán bằng giá trung bình**.

> 📚 **Nghiên cứu**: "Why do tree-based models fail on time series forecasting?" (Godahewa et al., 2021) — *"Tree-based models struggle with out-of-distribution samples because they can only interpolate, not extrapolate."*

**Giải pháp**: Dùng **return prediction** thay vì **price prediction**, hoặc dùng models biết extrapolate (LSTM, Transformer).

---

### 3.4 🟡 Thiếu dữ liệu quan trọng

| Dữ liệu thiếu | Tầm quan trọng | Lý do |
|---------------|----------------|-------|
| **Sentiment tin tức** | 🔴 Rất cao | Chiến tranh, Fed decisions, khủng hoảng → biến động mạnh |
| **Fear & Greed Index** | 🔴 Cao | Tâm lý thị trường = driver chính giá vàng ngắn hạn |
| **ETF flows (GLD, IAU)** | 🟡 Cao | Dòng vốn vào/ra ETF vàng = supply/demand thực |
| **CFTC CoT Reports** | 🟡 Cao | Net speculative positions → sentiment institutional |
| **CPI / Inflation data** | 🟡 Cao | Vàng là hedge inflation, CPI surprise → biến động lớn |
| **Fed rate expectations** | 🟡 Cao | Fed Funds Futures → expected rate path |
| **Rupee, Yuan exchange rates** | 🟠 Trung bình | Ấn Độ + Trung Quốc = 50% demand vàng vật chất |
| **Mining production data** | 🟠 Thấp | Supply side, thay đổi chậm |

> 📚 **Nghiên cứu**: "Determinants of Gold Prices" (Baur & McDermott, 2010, Journal of International Money and Finance): Vàng chịu ảnh hưởng bởi: **(1) USD strength, (2) Real interest rates, (3) Geopolitical risk, (4) Inflation expectations, (5) Central bank demand.** Hiện tại dự án chỉ cover được (1) và (2) một phần.

---

### 3.5 🟡 Ensemble chỉ có 1 model

```python
ensemble_price.add_model(xgb_price, weight=1.0)  # Chỉ 1 model!
```

Đây **không phải ensemble thực sự**. Ensemble cần tối thiểu 2-3 models khác biệt:
- XGBoost (tree-based)
- LSTM/GRU (sequential deep learning)
- Linear model (Ridge/Lasso) — làm baseline

> 📚 **Tham khảo**: "No Free Lunch Theorem" — Không model nào tốt nhất cho mọi trường hợp. Ensemble nhiều loại models khác nhau → robust hơn.

---

### 3.6 🟡 Thiếu Risk Management Layer

Dự án đưa ra lời khuyên BUY/SELL nhưng **không có**:
- ❌ Position sizing (nên mua bao nhiêu?)
- ❌ Stop-loss levels
- ❌ Value at Risk (VaR)
- ❌ Maximum drawdown tracking
- ❌ Backtesting returns trên dữ liệu lịch sử

> ⚠️ **Cảnh báo**: Theo nghiên cứu "The performance of technical analysis in gold market" (Narayan et al., 2015): *"Technical analysis alone can generate false signals in trending markets, leading to significant losses without proper risk management."*

---

## 4. 📊 So sánh với nghiên cứu học thuật

### 4.1 Accuracy benchmarks trong gold price forecasting

| Nghiên cứu | Model | Accuracy/R² | Features |
|-------------|-------|-------------|----------|
| Đề tài này | XGBoost | R² âm (~-0.5) | 92 technical+macro |
| Livieris et al. (2020) | LSTM ensemble | R² = 0.89 | Price + Sentiment |
| Mudassir et al. (2020) | CNN-LSTM | Accuracy 65% (trend) | Technical + News |
| Jianwei et al. (2019) | GRU + Attention | R² = 0.92 | Multi-source |
| Ismail et al. (2020) | XGBoost + LSTM | R² = 0.85 | Technical + Macro |

> 💡 **Kết luận từ nghiên cứu**: Các paper đạt accuracy cao thường:
> 1. Dùng **Deep Learning** (LSTM, GRU, Transformer) cho giá tuyệt đối
> 2. Dùng **XGBoost** cho xu hướng (classification) — phù hợp hơn
> 3. **Kết hợp sentiment** (NLP trên news) → cải thiện 5-15%
> 4. **Walk-forward validation** cho metrics đáng tin cậy

### 4.2 Tại sao dự đoán giá vàng khó?

```
Efficient Market Hypothesis (EMH):
  - Nếu thị trường hiệu quả, giá đã phản ánh mọi thông tin
  - Không model nào vượt trội bền vững qua thời gian

Random Walk Theory:
  - Giá tài sản tài chính = random walk + drift
  - Dự đoán ngắn hạn (1d) gần như bất khả thi
  - Dự đoán trung hạn (30d) khả thi hơn nếu bắt đúng trend
```

> ⚠️ **Thực tế**: Ngay cả các quỹ hedge fund lớn nhất cũng chỉ đạt Sharpe ratio 1.5-2.0. Dự đoán chính xác 55-60% xu hướng đã là **rất tốt** cho trading system.

---

## 5. 🛠️ Đề xuất cải thiện (Ưu tiên cao → thấp)

### 🔴 Ưu tiên 1: Fix ML Methodology

| # | Cải thiện | Effort | Impact |
|---|-----------|--------|--------|
| 1 | **Predict return thay vì price** | 2h | 🔴 Rất cao |
| 2 | **Walk-forward validation** | 4h | 🔴 Rất cao |
| 3 | **Purge & embargo** (tránh data leakage) | 3h | 🔴 Cao |
| 4 | **Hyperparameter tuning** (Optuna/RandomSearch) | 4h | 🟡 Trung bình |

### 🟡 Ưu tiên 2: Thêm Data Sources

| # | Cải thiện | Effort | Impact |
|---|-----------|--------|--------|
| 5 | **News sentiment** (NLP trên tin tức cafef/vnexpress) | 8h | 🔴 Cao |
| 6 | **Fear & Greed Index** (alternative.me API) | 2h | 🟡 Trung bình |
| 7 | **ETF flows data** (GLD holdings) | 3h | 🟡 Trung bình |
| 8 | **CPI/Inflation data** (FRED API) | 3h | 🟡 Trung bình |

### 🟢 Ưu tiên 3: Thêm Models

| # | Cải thiện | Effort | Impact |
|---|-----------|--------|--------|
| 9 | **LSTM/GRU** cho price prediction (extrapolation) | 6h | 🔴 Cao |
| 10 | **LightGBM/CatBoost** cho ensemble đa dạng | 3h | 🟡 Trung bình  |
| 11 | **Transformer** (attention mechanism) | 8h | 🟡 Trung bình |

### 🔵 Ưu tiên 4: Risk & Backtesting

| # | Cải thiện | Effort | Impact |
|---|-----------|--------|--------|
| 12 | **Backtesting framework** (equity curve, Sharpe) | 6h | 🔴 Cao |
| 13 | **Position sizing** (Kelly criterion) | 2h | 🟡 Trung bình |
| 14 | **Stop-loss integration** | 2h | 🟡 Trung bình |

---

## 6. 📌 Kết luận cuối cùng

### Dự án có sử dụng được cho đầu tư thực không?

> ⚠️ **CHƯA NÊN dùng cho quyết định đầu tư thực** ở trạng thái hiện tại vì:
> 1. R² âm — model tệ hơn cả random
> 2. Không có walk-forward validation — metrics có thể bị inflate
> 3. XGBoost không extrapolate được → sai lầm ở vùng giá mới

### Dự án có khả thi không?

> ✅ **CÓ**, nhưng cần:
> - Fix methodology (return prediction + walk-forward) → R² có thể đạt 0.3-0.5
> - Thêm LSTM cho price prediction → R² có thể đạt 0.6-0.8
> - Thêm sentiment → accuracy trend có thể đạt 60-65%
> - Khi achieve accuracy **>55% trend** với walk-forward → **bắt đầu có lợi nhuận kỳ vọng dương**

### Dự án thiếu gì quan trọng nhất?

```
Top 5 thiếu quan trọng nhất:

1. 🔴 Walk-forward validation     → Không biết model có thực sự tốt không
2. 🔴 Return-based prediction     → XGBoost không extrapolate được giá
3. 🔴 News sentiment analysis     → Bỏ lỡ 30-40% thông tin thị trường
4. 🟡 Deep Learning models (LSTM) → Cần cho price series prediction
5. 🟡 Backtesting framework       → Không biết strategy có profitable không
```

---

> 📚 **Tham khảo chính**:
> - López de Prado, M. (2018). "Advances in Financial Machine Learning"
> - Livieris et al. (2020). "Gold price forecasting using CNN-LSTM Ensemble"
> - Baur & McDermott (2010). "Determinants of Gold Prices"
> - Narayan et al. (2015). "Technical Analysis in Gold Market"
> - Godahewa et al. (2021). "Tree-based Models in Time Series"
