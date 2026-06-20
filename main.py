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
        "section": "Global Market",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20markets%20OR%20economy%20OR%20stocks%20OR%20Federal%20Reserve&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Global Market",
        "source": "CNBC",
        "url": "https://news.google.com/rss/search?q=site%3Acnbc.com%20markets%20OR%20stocks%20OR%20economy%20OR%20investing&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Global Market",
        "source": "MarketWatch",
        "url": "https://news.google.com/rss/search?q=site%3Amarketwatch.com%20markets%20OR%20stocks%20OR%20economy&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Global Market",
        "source": "Bloomberg",
        "url": "https://news.google.com/rss/search?q=site%3Abloomberg.com%20markets%20OR%20economy%20OR%20stocks&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Global Market",
        "source": "Financial Times",
        "url": "https://news.google.com/rss/search?q=site%3Aft.com%20markets%20OR%20economy%20OR%20central%20banks&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Global Market",
        "source": "Wall Street Journal",
        "url": "https://news.google.com/rss/search?q=site%3Awsj.com%20markets%20OR%20economy%20OR%20stocks&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI / Semiconductor",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20Nvidia%20OR%20TSMC%20OR%20semiconductor%20OR%20AI%20chips&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI / Semiconductor",
        "source": "CNBC",
        "url": "https://news.google.com/rss/search?q=site%3Acnbc.com%20Nvidia%20OR%20AI%20chips%20OR%20semiconductor%20OR%20TSMC&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI / Semiconductor",
        "source": "Yahoo Finance",
        "url": "https://news.google.com/rss/search?q=site%3Afinance.yahoo.com%20Nvidia%20OR%20AMD%20OR%20TSMC%20OR%20Micron%20OR%20semiconductor&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "AI / Semiconductor",
        "source": "Seeking Alpha",
        "url": "https://news.google.com/rss/search?q=site%3Aseekingalpha.com%20Nvidia%20OR%20AMD%20OR%20Broadcom%20OR%20semiconductor&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Energy / Oil",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20oil%20prices%20OR%20Brent%20OR%20WTI%20OR%20OPEC&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Energy / Oil",
        "source": "Investing.com",
        "url": "https://news.google.com/rss/search?q=site%3Ainvesting.com%20oil%20OR%20Brent%20OR%20WTI%20OR%20OPEC%20OR%20commodities&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Crypto",
        "source": "Yahoo Finance",
        "url": "https://news.google.com/rss/search?q=site%3Afinance.yahoo.com%20Bitcoin%20OR%20Ethereum%20OR%20crypto%20OR%20stablecoin&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Crypto",
        "source": "CNBC",
        "url": "https://news.google.com/rss/search?q=site%3Acnbc.com%20Bitcoin%20OR%20Ethereum%20OR%20crypto%20OR%20stablecoin&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Macro Data",
        "source": "Reuters",
        "url": "https://news.google.com/rss/search?q=site%3Areuters.com%20CPI%20OR%20PPI%20OR%20jobs%20OR%20GDP%20OR%20FOMC%20OR%20Fed&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Macro Data",
        "source": "Investing.com",
        "url": "https://news.google.com/rss/search?q=site%3Ainvesting.com%20economic%20calendar%20OR%20CPI%20OR%20Fed%20OR%20dollar%20OR%20yields&hl=en-US&gl=US&ceid=US:en",
    },
    {
        "section": "Macro Data",
        "source": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
    },
    {
        "section": "Macro Data",
        "source": "BEA",
        "url": "https://apps.bea.gov/rss/rss.xml",
    },
]

TRUSTED_SOURCE_HINTS = (
    "Reuters",
    "CNBC",
    "MarketWatch",
    "Yahoo Finance",
    "Investing.com",
    "Seeking Alpha",
    "Bloomberg",
    "Financial Times",
    "Wall Street Journal",
    "Federal Reserve",
    "BEA",
)

SECTION_LABELS = {
    "Global Market": "글로벌 시장",
    "AI / Semiconductor": "AI / 반도체",
    "Energy / Oil": "에너지 / 유가",
    "Crypto": "크립토",
    "Macro Data": "매크로 지표",
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
        trusted = any(source in item.source for source in TRUSTED_SOURCE_HINTS)
        return (1 if trusted else 0, item.published_at)

    return sorted(items, key=score, reverse=True)


def why_it_matters(section: str) -> str:
    if section == "Global Market":
        return "미국 증시, 금리, 달러 흐름은 한국 증시 외국인 수급과 환율에 직접 영향을 줍니다."
    if section == "AI / Semiconductor":
        return "AI와 반도체 뉴스는 삼성전자, SK하이닉스, HBM/장비주 투자심리에 연결됩니다."
    if section == "Energy / Oil":
        return "유가 변동은 한국의 물가, 원가 부담, 정유/화학/항공 업종에 영향을 줄 수 있습니다."
    if section == "Crypto":
        return "크립토 위험선호 변화는 성장주와 글로벌 유동성 심리를 볼 때 참고할 수 있습니다."
    if section == "Macro Data":
        return "물가, 고용, GDP, FOMC 관련 뉴스는 금리 기대와 원달러 환율에 영향을 줍니다."
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
            f"최근 {NEWS_WINDOW_HOURS}시간 이내 수집된 지정 소스 뉴스가 없습니다."
        )

    grouped: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        grouped[item.section].append(item)

    lines = [
        "해외 경제 뉴스 브리핑",
        today,
        f"최근 {NEWS_WINDOW_HOURS}시간 이내 뉴스만 선별",
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
            "오늘 한국 시장에서는 반도체 대형주, 원달러 환율, 미국 금리 기대, 유가 민감 업종을 함께 확인하세요.",
            "",
            "[X Post Ideas]",
            "1. 최근 6시간 해외 뉴스만 보면 장전 체크리스트가 훨씬 선명해진다",
            "2. 한국 증시는 미국 금리와 반도체 뉴스의 영향을 크게 받는다",
            "3. 유가와 환율은 한국 기업 실적을 볼 때 빠질 수 없는 변수다",
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
