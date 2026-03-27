"""
Gold Predictor - News Collector (V2 - Resilient)
Thu thập tin tức liên quan đến vàng cho AI sentiment analysis.

Chain: cafef.vn → Google News RSS → Kitco RSS

Nguồn:
1. cafef.vn - Tin tức vàng VN (primary)
2. Google News RSS - Tìm kiếm "giá vàng" (fallback)
3. Kitco RSS - Tin tức vàng quốc tế (fallback)

Điểm mở rộng tương lai:
- Thêm full article content extraction
- Thêm VnExpress RSS
- Thêm Bloomberg RSS
"""

import xml.etree.ElementTree as ET
from datetime import date, datetime
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.services.data_collector.base_collector import BaseCollector
from app.db.models import NewsArticle
from app.utils.logger import get_logger

logger = get_logger(__name__)


class NewsCollector(BaseCollector):
    """Thu thập tin tức vàng từ nhiều nguồn với fallback."""

    def __init__(self):
        super().__init__("news")

    def fetch_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """Fetch tin tức từ tất cả nguồn với fallback chain."""
        all_news = []

        # Nguồn 1: cafef.vn (primary)
        cafef_news = self._fetch_cafef()
        if cafef_news:
            all_news.extend(cafef_news)
            self.logger.info(f"cafef.vn: {len(cafef_news)} tin tức")

        # Nguồn 2: Google News RSS (fallback / bổ sung)
        google_news = self._fetch_google_news_rss()
        if google_news:
            all_news.extend(google_news)
            self.logger.info(f"Google News RSS: {len(google_news)} tin tức")

        # Nguồn 3: Kitco RSS (tin quốc tế)
        kitco_news = self._fetch_kitco_rss()
        if kitco_news:
            all_news.extend(kitco_news)
            self.logger.info(f"Kitco RSS: {len(kitco_news)} tin tức")

        if not all_news:
            self.logger.warning("Không thu thập được tin tức nào từ bất kỳ nguồn")
            return pd.DataFrame()

        df = pd.DataFrame(all_news)
        self.logger.info(f"Tổng thu thập: {len(df)} tin tức từ {len(set(n['source'] for n in all_news))} nguồn")
        return df

    def _fetch_cafef(self) -> list[dict]:
        """
        Scrape headlines tin tức vàng từ cafef.vn.
        URL đã cập nhật: cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn
        """
        try:
            from app.utils.constants import NEWS_SOURCES
            url = NEWS_SOURCES.get("cafef", "https://cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn")
        except ImportError:
            url = "https://cafef.vn/du-lieu/gia-vang-hom-nay/trong-nuoc.chn"
        
        self.logger.info(f"Đang scrape tin tức từ {url}...")

        try:
            session = self._get_session()
            response = session.get(
                url,
                headers={
                    "Referer": "https://cafef.vn/",
                },
                timeout=15,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            articles = []

            # CSS selectors cho trang dữ liệu giá vàng cafef
            # Trang mới có structure khác → dùng nhiều selectors
            news_items = soup.select(
                ".tlitem, .knswli-item, .box-category-item, "
                ".item-news, .news-item, .article-item, "
                "article, .list-news li"
            )

            for item in news_items[:20]:
                try:
                    # Tìm title với nhiều selectors
                    title_tag = item.select_one(
                        "h3 a, h2 a, .knswli-title a, a.title, "
                        ".titleNews a, .box-title a, a[title]"
                    )
                    if not title_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    if not title or len(title) < 10:
                        continue

                    # Lấy URL
                    href = title_tag.get("href", "")
                    if href and not href.startswith("http"):
                        href = f"https://cafef.vn{href}"

                    # Lấy summary/description
                    summary_tag = item.select_one(
                        ".knswli-sapo, .sapo, p.summary, "
                        ".box-des, .des, .description"
                    )
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

        except Exception as e:
            self.logger.error(f"Lỗi kết nối cafef.vn: {e}")
            return []

    def _fetch_google_news_rss(self) -> list[dict]:
        """
        Fetch tin tức từ Google News RSS.
        URL: https://news.google.com/rss/search?q=giá+vàng&hl=vi&gl=VN
        Không cần key, không bị block (RSS public).
        """
        url = "https://news.google.com/rss/search?q=gi%C3%A1+v%C3%A0ng&hl=vi&gl=VN"
        self.logger.info("Đang fetch Google News RSS về giá vàng...")

        try:
            session = self._get_session()
            response = session.get(url, timeout=15)
            response.raise_for_status()

            articles = []
            root = ET.fromstring(response.content)
            
            # RSS format: <channel><item><title>...<link>...<pubDate>...
            for item in root.findall(".//item")[:15]:
                try:
                    title = item.findtext("title", "").strip()
                    if not title or len(title) < 10:
                        continue

                    link = item.findtext("link", "")
                    pub_date_str = item.findtext("pubDate", "")
                    
                    # Parse pubDate (RFC 2822 format)
                    pub_date = datetime.now()
                    if pub_date_str:
                        try:
                            from email.utils import parsedate_to_datetime
                            pub_date = parsedate_to_datetime(pub_date_str)
                        except Exception:
                            pass

                    articles.append({
                        "published_at": pub_date,
                        "source": "google_news",
                        "title": title[:500],
                        "url": link[:1000] if link else None,
                        "summary": None,
                    })

                except Exception as e:
                    self.logger.warning(f"Lỗi parse Google News item: {e}")
                    continue

            return articles

        except Exception as e:
            self.logger.error(f"Lỗi fetch Google News RSS: {e}")
            return []

    def _fetch_kitco_rss(self) -> list[dict]:
        """
        Fetch tin tức từ Kitco RSS.
        URL: https://www.kitco.com/rss/gold.xml
        Tin tức vàng quốc tế.
        """
        url = "https://www.kitco.com/rss/gold.xml"
        self.logger.info("Đang fetch Kitco RSS...")

        try:
            session = self._get_session()
            response = session.get(url, timeout=15)
            response.raise_for_status()

            articles = []
            root = ET.fromstring(response.content)
            
            for item in root.findall(".//item")[:10]:
                try:
                    title = item.findtext("title", "").strip()
                    if not title or len(title) < 10:
                        continue

                    link = item.findtext("link", "")
                    description = item.findtext("description", "")
                    pub_date_str = item.findtext("pubDate", "")

                    pub_date = datetime.now()
                    if pub_date_str:
                        try:
                            from email.utils import parsedate_to_datetime
                            pub_date = parsedate_to_datetime(pub_date_str)
                        except Exception:
                            pass

                    # Clean HTML từ description
                    if description:
                        description = BeautifulSoup(description, "html.parser").get_text(strip=True)

                    articles.append({
                        "published_at": pub_date,
                        "source": "kitco",
                        "title": title[:500],
                        "url": link[:1000] if link else None,
                        "summary": description[:2000] if description else None,
                    })

                except Exception as e:
                    self.logger.warning(f"Lỗi parse Kitco item: {e}")
                    continue

            return articles

        except Exception as e:
            self.logger.error(f"Lỗi fetch Kitco RSS: {e}")
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
