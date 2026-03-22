"""
Gold Predictor - News Collector
Thu thập tin tức liên quan đến vàng cho AI sentiment analysis.

Nguồn: cafef.vn, kitco.com (scraping headlines)

Điểm mở rộng tương lai:
- Thêm Google News API
- Thêm RSS feed parsing
- Thêm full article content extraction
"""

from datetime import date, datetime
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import NewsArticle
from app.utils.logger import get_logger

logger = get_logger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}


class NewsCollector(BaseCollector):
    """Thu thập tin tức vàng từ nhiều nguồn."""

    def __init__(self):
        super().__init__("news")

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Fetch tin tức từ tất cả nguồn."""
        all_news = []

        # Thu thập từ cafef.vn
        cafef_news = self._fetch_cafef()
        if cafef_news:
            all_news.extend(cafef_news)

        if not all_news:
            self.logger.warning("Không thu thập được tin tức nào")
            return pd.DataFrame()

        df = pd.DataFrame(all_news)
        self.logger.info(f"Đã thu thập {len(df)} tin tức")
        return df

    def _fetch_cafef(self) -> list[dict]:
        """Scrape headlines tin tức vàng từ cafef.vn."""
        url = "https://cafef.vn/vang.chn"
        self.logger.info(f"Đang scrape tin tức từ {url}...")

        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            articles = []

            # Tìm các article items
            # cafef.vn thường dùng class tlitem, knswli-item, box-category-item
            news_items = soup.select(".tlitem, .knswli-item, .box-category-item, .item-news")

            for item in news_items[:20]:  # Lấy tối đa 20 tin mới nhất
                try:
                    # Lấy title
                    title_tag = item.select_one("h3 a, h2 a, .knswli-title a, a.title")
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue

                    # Lấy URL
                    href = title_tag.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"https://cafef.vn{href}"

                    # Lấy summary/description (nếu có)
                    summary_tag = item.select_one(".knswli-sapo, .sapo, p.summary")
                    summary = summary_tag.get_text(strip=True) if summary_tag else None

                    articles.append({
                        "published_at": datetime.now(),
                        "source": "cafef",
                        "title": title[:500],
                        "url": href[:1000] if href else None,
                        "summary": summary[:2000] if summary else None,
                    })

                except Exception as e:
                    self.logger.warning(f"Lỗi parse cafef article: {e}")
                    continue

            self.logger.info(f"cafef.vn: {len(articles)} tin tức")
            return articles

        except requests.RequestException as e:
            self.logger.error(f"Lỗi kết nối cafef.vn: {e}")
            return []

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate tin tức - loại bỏ duplicate titles."""
        if df.empty:
            return df

        original_len = len(df)
        df = df.drop_duplicates(subset=["title"], keep="first")

        dropped = original_len - len(df)
        if dropped > 0:
            self.logger.info(f"Loại bỏ {dropped} tin trùng title")

        return df

    def store_data(self, df: pd.DataFrame, db: Session) -> int:
        """Lưu tin tức vào bảng news_articles (skip duplicate)."""
        if df.empty:
            return 0

        count = 0
        for _, row in df.iterrows():
            # Kiểm tra đã có tin tức cùng title + source chưa
            existing = db.query(NewsArticle).filter(
                NewsArticle.title == row["title"],
                NewsArticle.source == row["source"],
            ).first()

            if not existing:
                record = NewsArticle(
                    published_at=row["published_at"],
                    source=row["source"],
                    title=row["title"],
                    url=row.get("url"),
                    summary=row.get("summary"),
                )
                db.add(record)
                count += 1

        return count
