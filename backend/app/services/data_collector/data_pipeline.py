"""
Gold Predictor - Data Pipeline Runner V2
Orchestrate toàn bộ quá trình thu thập dữ liệu.

V2 Changes:
- Thêm Fear & Greed Index collector
- Thêm FRED collector (CPI, Inflation, Fed Rate)
- Thêm Sentiment Analyzer (post-collection)
- GLD ETF tự động qua macro_collector (đã thêm vào constants)

Dùng để chạy tất cả collectors cùng lúc hoặc riêng lẻ.
"""

from datetime import date, datetime
from typing import Optional

from app.services.data_collector.xau_collector import XAUCollector
from app.services.data_collector.sjc_collector import SJCCollector
from app.services.data_collector.giavang_org_collector import GiavangOrgCollector
from app.services.data_collector.macro_collector import MacroCollector
from app.services.data_collector.news_collector import NewsCollector
from app.services.data_collector.fear_greed_collector import FearGreedCollector
from app.services.data_collector.fred_collector import FREDCollector
from app.services.data_collector.sentiment_analyzer import SentimentAnalyzer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataPipeline:
    """
    Orchestrator cho tất cả data collectors V2.
    
    Pipeline order:
    1. Gold prices (XAU, SJC, Giavang.org)
    2. Macro indicators (DXY, Oil, Treasury, S&P500, GLD)
    3. Fear & Greed Index
    4. FRED data (CPI, Inflation, Fed Rate)
    5. News collection
    6. Sentiment analysis (post-processing news)
    """

    def __init__(self):
        self.xau_collector = XAUCollector()
        self.sjc_collector = SJCCollector()
        self.giavang_org_collector = GiavangOrgCollector()
        self.macro_collector = MacroCollector()
        self.news_collector = NewsCollector()
        self.fear_greed_collector = FearGreedCollector()
        self.fred_collector = FREDCollector()
        self.sentiment_analyzer = SentimentAnalyzer()
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
        self.logger.info("🥇 BẮT ĐẦU THU THẬP DỮ LIỆU (V2)")
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

        # 3. Giavang.org (SJC/PNJ/DOJI)
        try:
            results["giavang_org"] = self.giavang_org_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"❌ Giavang.org collector failed: {e}")
            results["giavang_org"] = -1

        # 4. Macro Indicators (DXY, Oil, Treasury, S&P500, GLD)
        try:
            results["macro"] = self.macro_collector.collect_and_store(start_date, end_date)
        except Exception as e:
            self.logger.error(f"❌ Macro collector failed: {e}")
            results["macro"] = -1

        # 5. Fear & Greed Index
        try:
            results["fear_greed"] = self.fear_greed_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"❌ Fear & Greed collector failed: {e}")
            results["fear_greed"] = -1

        # 6. FRED Data (CPI, Inflation, Fed Rate)
        try:
            results["fred"] = self.fred_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"❌ FRED collector failed: {e}")
            results["fred"] = -1

        # 7. News
        try:
            results["news"] = self.news_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"❌ News collector failed: {e}")
            results["news"] = -1

        # 8. Sentiment Analysis (post-processing)
        try:
            results["sentiment"] = self.sentiment_analyzer.analyze_unanalyzed_articles()
        except Exception as e:
            self.logger.error(f"❌ Sentiment analysis failed: {e}")
            results["sentiment"] = -1

        # Summary
        self.logger.info("=" * 60)
        self.logger.info("📊 KẾT QUẢ THU THẬP DỮ LIỆU (V2):")
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

        try:
            results["giavang_org"] = self.giavang_org_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"Giavang.org failed: {e}")
            results["giavang_org"] = -1

        return results

    def run_macro_only(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Thu thập macro indicators + Fear & Greed + FRED."""
        results = {}

        try:
            results["macro"] = self.macro_collector.collect_and_store(start_date, end_date)
        except Exception as e:
            self.logger.error(f"Macro failed: {e}")
            results["macro"] = -1

        try:
            results["fear_greed"] = self.fear_greed_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"Fear & Greed failed: {e}")
            results["fear_greed"] = -1

        try:
            results["fred"] = self.fred_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"FRED failed: {e}")
            results["fred"] = -1

        return results

    def run_sentiment_only(self) -> dict:
        """Thu thập news + chạy sentiment analysis."""
        results = {}

        try:
            results["news"] = self.news_collector.collect_and_store()
        except Exception as e:
            self.logger.error(f"News failed: {e}")
            results["news"] = -1

        try:
            results["sentiment"] = self.sentiment_analyzer.analyze_unanalyzed_articles()
        except Exception as e:
            self.logger.error(f"Sentiment failed: {e}")
            results["sentiment"] = -1

        return results


# Convenience function để chạy từ CLI
def collect_all():
    """Entry point để chạy từ command line."""
    pipeline = DataPipeline()
    results = pipeline.run_all()
    return results


if __name__ == "__main__":
    collect_all()
