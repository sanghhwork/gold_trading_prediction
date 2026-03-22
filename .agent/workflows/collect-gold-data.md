---
description: Thu thập dữ liệu giá vàng XAU/USD, SJC và macro indicators
---

# /collect-gold-data

Workflow thu thập dữ liệu giá vàng từ tất cả nguồn.

// turbo-all

## Các bước thực hiện

1. Activate virtual environment
```powershell
.\venv\Scripts\Activate.ps1
```

2. Thu thập XAU/USD + Macro từ yfinance
```powershell
python -c "from app.services.data_collector.xau_collector import XAUCollector; XAUCollector().collect_and_store()"
```

3. Thu thập giá SJC
```powershell
python -c "from app.services.data_collector.sjc_collector import SJCCollector; SJCCollector().collect_and_store()"
```

4. Thu thập Macro indicators
```powershell
python -c "from app.services.data_collector.macro_collector import MacroCollector; MacroCollector().collect_and_store()"
```

5. Validate dữ liệu
```powershell
python -c "from app.services.data_collector.base_collector import validate_all_data; validate_all_data()"
```

6. Báo cáo kết quả
- Kiểm tra số rows được thêm mới
- Kiểm tra có missing data không
- Kiểm tra data freshness (last date)
