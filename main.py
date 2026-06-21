import html
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import requests


NEWS_WINDOW_HOURS = 6

RSS_FEEDS = [
    {
        "section": "US Stock Market",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20%28stocks%20OR%20Wall%20Street%20OR%20Nasdaq%20OR%20S%26P%20500%20OR%20Fed%20OR%20earnings%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "US Stock Market",
        "source": "CNBC",
        "url": "https://news.google.com/rss/search?q=site%3Acnbc.com%20%28stocks%20OR%20markets%20OR%20Wall%20Street%20OR%20Nasdaq%20OR%20earnings%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "US Stock Market",
        "source": "MarketWatch",
        "url": "https://news.google.com/rss/search?q=site%3Amarketwatch.com%20%28stocks%20OR%20markets%20OR%20Wall%20Street%20OR%20Nasdaq%20OR%20Treasury%20yields%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "US Stock Market",
        "source": "Yahoo Finance",
        "url": "https://news.google.com/rss/search?q=site%3Afinance.yahoo.com%20%28stocks%20OR%20markets%20OR%20earnings%20OR%20Nasdaq%20OR%20S%26P%20500%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "US Stock Market",
        "source": "Bloomberg",
        "url": "https://news.google.com/rss/search?q=site%3Abloomberg.com%20%28stocks%20OR%20markets%20OR%20Wall%20Street%20OR%20Treasury%20yields%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "US Stock Market",
        "source": "Financial Times",
        "url": "https://news.google.com/rss/search?q=site%3Aft.com%20%28markets%20OR%20stocks%20OR%20Wall%20Street%20OR%20central%20banks%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "US Stock Market",
        "source": "Wall Street Journal",
        "url": "https://news.google.com/rss/search?q=site%3Awsj.com%20%28markets%20OR%20stocks%20OR%20Wall%20Street%20OR%20economy%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20%28AI%20OR%20artificial%20intelligence%20OR%20Nvidia%20OR%20TSMC%20OR%20semiconductor%20OR%20chips%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI",
        "source": "CNBC",
        "url": "https://news.google.com/rss/search?q=site%3Acnbc.com%20%28AI%20OR%20artificial%20intelligence%20OR%20Nvidia%20OR%20semiconductor%20OR%20chips%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI",
        "source": "Yahoo Finance",
        "url": "https://news.google.com/rss/search?q=site%3Afinance.yahoo.com%20%28AI%20OR%20Nvidia%20OR%20AMD%20OR%20Broadcom%20OR%20TSMC%20OR%20Micron%20OR%20semiconductor%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI",
        "source": "MarketWatch",
        "url": "https://news.google.com/rss/search?q=site%3Amarketwatch.com%20%28AI%20OR%20Nvidia%20OR%20AMD%20OR%20semiconductor%20OR%20chips%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Crypto",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20%28Bitcoin%20OR%20Ethereum%20OR%20crypto%20OR%20stablecoin%20OR%20Coinbase%20OR%20ETF%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Crypto",
        "source": "CNBC",
        "url": "https://news.google.com/rss/search?q=site%3Acnbc.com%20%28Bitcoin%20OR%20Ethereum%20OR%20crypto%20OR%20stablecoin%20OR%20Coinbase%20OR%20ETF%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Crypto",
        "source": "Yahoo Finance",
        "url": "https://news.google.com/rss/search?q=site%3Afinance.yahoo.com%20%28Bitcoin%20OR%20Ethereum%20OR%20crypto%20OR%20stablecoin%20OR%20Coinbase%20OR%20ETF%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Crypto",
        "source": "MarketWatch",
        "url": "https://news.google.com/rss/search?q=site%3Amarketwatch.com%20%28Bitcoin%20OR%20Ethereum%20OR%20crypto%20OR%20stablecoin%20OR%20Coinbase%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Macro / Rates",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20%28CPI%20OR%20PPI%20OR%20jobs%20OR%20GDP%20OR%20FOMC%20OR%20Fed%20OR%20Treasury%20yields%20OR%20dollar%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Macro / Rates",
        "source": "Investing.com",
        "url": "https://news.google.com/rss/search?q=site%3Ainvesting.com%20%28economic%20calendar%20OR%20CPI%20OR%20Fed%20OR%20dollar%20OR%20Treasury%20yields%20OR%20interest%20rates%29&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Macro / Rates",
        "source": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
    },
    {
        "section": "Macro / Rates",
        "source": "BEA",
        "url": "https://apps.bea.gov/rss/rss.xml",
    },
]

TRUSTED_SOURCES = (
    "Reuters",
    "CNBC",
    "MarketWatch",
    "Yahoo Finance",
    "Investing.com",
    "Bloomberg",
    "Financial Times",
    "Wall Street Journal",
    "Federal Reserve",
    "BEA",
)

SECTION_LABELS = {
    "US Stock Market": "미국주식 영향 뉴스",
    "AI": "AI 뉴스",
    "Crypto": "크립토 영향 뉴스",
    "Macro / Rates": "매크로 / 금리 뉴스",
}

MAX_ITEMS_PER_SECTION = 5
MAX_TOTAL_ITEMS = 24
TELEGRAM_LIMIT = 4096


@dataclass(frozen=True)
class NewsItem:
    section: str
    title: str
    source: str
    link: str
    published: str
    published_at: datetime


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def normalize_title(title: str) -> str:
    title = html.unescape(title).lower()
    title = re.sub(r"\s+-\s+[^-]+$", "", title)
    title = re.sub(r"[^a-z0-9가-힣 ]+", " ", title)
    return re.sub(r"\s+", " ", title).strip()


def split_google_news_title(title: str, fallback_source: str) -> tuple[str, str]:
    title = html.unescape(title).strip()
    if " - " not in title:
        return title, fallback_source
    headline, source = title.rsplit(" - ", 1)
    return headline.strip(), source.strip() or fallback_source


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def is_recent(published_at: datetime) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_WINDOW_HOURS)
    return published_at >= cutoff


def item_text(item: ET.Element, names: list[str]) -> str:
    for name in names:
        value = item.findtext(name, default="").strip()
        if value:
            return value
    return ""


def fetch_rss(feed_url: str) -> list[dict[str, str]]:
    response = requests.get(
        feed_url,
        headers={"User-Agent": "daily-economy-news-bot/1.0"},
        timeout=20,
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    items = []
    for item in root.findall("./channel/item"):
        items.append(
            {
                "title": item_text(item, ["title"]),
                "link": item_text(item, ["link"]),
                "published": item_text(item, ["pubDate", "date", "updated", "published"]),
            }
        )
    return items


def is_trusted_source(source: str, fallback_source: str) -> bool:
    return any(trusted in source or trusted in fallback_source for trusted in TRUSTED_SOURCES)


def collect_news() -> list[NewsItem]:
    grouped: dict[str, list[NewsItem]] = defaultdict(list)
    seen_titles: set[str] = set()

    for feed in RSS_FEEDS:
        section = feed["section"]
        feed_url = feed["url"]
        fallback_source = feed["source"]
        try:
            raw_items = fetch_rss(feed_url)
        except Exception as exc:
            print(f"Skipping RSS feed after fetch error: {feed_url} ({exc})", file=sys.stderr)
            continue

        for raw_item in raw_items:
            published_at = parse_datetime(raw_item["published"])
            if published_at is None or not is_recent(published_at):
                continue

            if "news.google.com" in feed_url:
                headline, source = split_google_news_title(raw_item["title"], fallback_source)
            else:
                headline = html.unescape(raw_item["title"]).strip()
                source = fallback_source

            if not is_trusted_source(source, fallback_source):
                continue

            normalized = normalize_title(headline)
            if not headline or normalized in seen_titles:
                continue

            seen_titles.add(normalized)
            grouped[section].append(
                NewsItem(
                    section=section,
                    title=headline,
                    source=source,
                    link=raw_item["link"],
                    published=raw_item["published"],
                    published_at=published_at,
                )
            )

    selected: list[NewsItem] = []
    for section in SECTION_LABELS:
        selected.extend(rank_items(grouped.get(section, []))[:MAX_ITEMS_PER_SECTION])

    return rank_items(selected)[:MAX_TOTAL_ITEMS]


def rank_items(items: list[NewsItem]) -> list[NewsItem]:
    def score(item: NewsItem) -> tuple[int, datetime]:
        trusted = 1 if is_trusted_source(item.source, item.source) else 0
        return (trusted, item.published_at)

    return sorted(items, key=score, reverse=True)


def why_it_matters(section: str) -> str:
    if section == "US Stock Market":
        return "미국 증시, 실적, 금리, 달러 흐름은 한국 증시 외국인 수급과 성장주 투자심리에 직접 영향을 줍니다."
    if section == "AI":
        return "AI 뉴스는 엔비디아 밸류체인, 반도체 수요, 삼성전자와 SK하이닉스 투자심리에 연결됩니다."
    if section == "Crypto":
        return "크립토 뉴스는 위험자산 선호, 유동성 심리, 관련 미국 상장주와 성장주 분위기에 영향을 줄 수 있습니다."
    if section == "Macro / Rates":
        return "물가, 고용, GDP, FOMC, 금리 뉴스는 미국주식 밸류에이션과 원달러 환율에 영향을 줍니다."
    return "한국 투자자는 글로벌 자금 흐름과 업종별 영향을 함께 확인할 필요가 있습니다."


def format_age(published_at: datetime) -> str:
    delta = datetime.now(timezone.utc) - published_at
    total_minutes = max(0, int(delta.total_seconds() // 60))
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}시간 {minutes}분 전"
    return f"{minutes}분 전"


def build_briefing(items: list[NewsItem]) -> str:
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    today = now_kst.strftime("%Y-%m-%d %H:%M KST")
    if not items:
        return (
            f"해외 경제 뉴스 브리핑\n{today}\n\n"
            f"최근 {NEWS_WINDOW_HOURS}시간 이내 수집된 공신력 있는 지정 소스 뉴스가 없습니다."
        )

    grouped: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        grouped[item.section].append(item)

    lines = [
        "해외 경제 뉴스 브리핑",
        today,
        f"원칙: 서울 07:30 / 최근 {NEWS_WINDOW_HOURS}시간 / 공신력 있는 해외 소스 / 미국주식·AI·크립토·매크로 중심",
        "",
    ]

    for section in SECTION_LABELS:
        section_items = grouped.get(section, [])[:3]
        if not section_items:
            continue

        lines.append(f"[{SECTION_LABELS[section]}]")
        for idx, item in enumerate(section_items, start=1):
            lines.extend(
                [
                    f"{idx}. {item.title}",
                    f"Source: {item.source} / {format_age(item.published_at)}",
                    f"Link: {item.link}",
                    f"Why it matters: {why_it_matters(item.section)}",
                    "",
                ]
            )

    lines.extend(
        [
            "[Korea Market Impact]",
            "오늘 한국 시장에서는 미국주식 선물, 반도체 대형주, 원달러 환율, 미국 금리 기대, 크립토 위험선호를 함께 확인하세요.",
            "",
            "[X Post Ideas]",
            "1. 최근 6시간 해외 뉴스만 봐도 장전 체크리스트가 선명해진다",
            "2. 한국 증시는 결국 미국주식·AI·금리 뉴스의 영향을 크게 받는다",
            "3. 크립토 위험선호는 성장주 분위기를 볼 때 같이 체크해야 한다",
        ]
    )
    return "\n".join(lines).strip()


def split_for_telegram(text: str) -> list[str]:
    chunks = []
    remaining = text
    while len(remaining) > TELEGRAM_LIMIT:
        split_at = remaining.rfind("\n", 0, TELEGRAM_LIMIT)
        if split_at < 1000:
            split_at = TELEGRAM_LIMIT
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def explain_telegram_error(status_code: int) -> str:
    if status_code == 403:
        return (
            "Telegram rejected the message with 403 Forbidden. Open your bot chat in Telegram, "
            "press Start or send /start, then make sure TELEGRAM_CHAT_ID belongs to that same bot."
        )
    if status_code == 400:
        return "Telegram rejected the chat id or message format. Check TELEGRAM_CHAT_ID."
    if status_code == 401:
        return "Telegram rejected the bot token. Check TELEGRAM_BOT_TOKEN."
    return "Telegram rejected the request."


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chunk in split_for_telegram(text):
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        if not response.ok:
            raise RuntimeError(
                f"{explain_telegram_error(response.status_code)} "
                f"Status: {response.status_code}. Response: {response.text}"
            )


def main() -> int:
    try:
        bot_token = require_env("TELEGRAM_BOT_TOKEN")
        chat_id = require_env("TELEGRAM_CHAT_ID")

        news_items = collect_news()
        briefing = build_briefing(news_items)
        send_telegram_message(bot_token, chat_id, briefing)
    except Exception as exc:
        print(f"Failed to send overseas economy briefing: {exc}", file=sys.stderr)
        return 1

    print("Overseas economy briefing sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
