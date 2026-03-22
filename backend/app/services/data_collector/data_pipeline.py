"""
Gold Predictor - Data Pipeline Runner
Orchestrate toàn bộ quá trình thu thập dữ liệu.

Dùng để chạy tất cả collectors cùng lúc hoặc riêng lẻ.
"""

from datetime import date, datetime
from typing import Optional

from app.services.data_collector.xau_collector import XAUCollector
from app.services.data_collector.sjc_collector import SJCCollector
from app.services.data_collector.macro_collector import MacroCollector
from app.services.data_collector.news_collector import NewsCollector
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataPipeline:
    """
    Orchestrator cho tất cả data collectors.
    
    Điểm mở rộng tương lai:
    - Thêm parallel collection (asyncio)
    - Thêm retry failed collectors
    - Thêm notification khi collection hoàn thành
    """

    def __init__(self):
        self.xau_collector = XAUCollector()
        self.sjc_collector = SJCCollector()
        self.macro_collector = MacroCollector()
        self.news_collector = NewsCollector()
        self.logger = get_logger("data_pipeline")

    def run_all(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """
        Chạy tất cả collectors và trả về summary.
        
        Returns:
            dict với keys là tên collector, values là số records đã lưu.
        """
        self.logger.info("=" * 60)
        self.logger.info("🥇 BẮT ĐẦU THU THẬP DỮ LIỆU")
        self.logger.info(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)

        results = {}

        # 1. XAU/USD
        try:
            results["xau_usd"] = self.xau_collector.collect_and_store(start_date, end_date)
        except Exception as e:
            self.logger.error(f"❌ XAU/USD collector failed: {e}")
            results["xau_usd"] = -1

        # 2. SJC
        try:
            results["sjc"] = self.sjc_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"❌ SJC collector failed: {e}")
            results["sjc"] = -1

        # 3. Macro Indicators
        try:
            results["macro"] = self.macro_collector.collect_and_store(start_date, end_date)
        except Exception as e:
            self.logger.error(f"❌ Macro collector failed: {e}")
            results["macro"] = -1

        # 4. News
        try:
            results["news"] = self.news_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"❌ News collector failed: {e}")
            results["news"] = -1

        # Summary
        self.logger.info("=" * 60)
        self.logger.info("📊 KẾT QUẢ THU THẬP DỮ LIỆU:")
        for name, count in results.items():
            status = "✅" if count >= 0 else "❌"
            self.logger.info(f"  {status} {name}: {count} records")
        self.logger.info("=" * 60)

        return results

    def run_gold_only(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Chỉ thu thập giá vàng (XAU + SJC)."""
        results = {}

        try:
            results["xau_usd"] = self.xau_collector.collect_and_store(start_date, end_date)
        except Exception as e:
            self.logger.error(f"XAU/USD failed: {e}")
            results["xau_usd"] = -1

        try:
            results["sjc"] = self.sjc_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"SJC failed: {e}")
            results["sjc"] = -1

        return results

    def run_macro_only(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Chỉ thu thập macro indicators."""
        try:
            count = self.macro_collector.collect_and_store(start_date, end_date)
            return {"macro": count}
        except Exception as e:
            self.logger.error(f"Macro failed: {e}")
            return {"macro": -1}


# Convenience function để chạy từ CLI
def collect_all():
    """Entry point để chạy từ command line."""
    pipeline = DataPipeline()
    results = pipeline.run_all()
    return results


if __name__ == "__main__":
    collect_all()
