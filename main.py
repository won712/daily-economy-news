import html
import os
import re
import sys
import textwrap
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from openai import OpenAI


RSS_FEEDS = {
    "Global Market": [
        "https://news.google.com/rss/search?q=US+stock+market+Federal+Reserve+Treasury+yields+dollar&hl=en-US&gl=US&ceid=US:en",
    ],
    "AI / Semiconductor": [
        "https://news.google.com/rss/search?q=Nvidia+TSMC+Samsung+SK+Hynix+Micron+AI+semiconductor&hl=en-US&gl=US&ceid=US:en",
    ],
    "Energy / Oil": [
        "https://news.google.com/rss/search?q=oil+prices+Brent+WTI+OPEC+Middle+East+Strait+of+Hormuz&hl=en-US&gl=US&ceid=US:en",
    ],
    "Crypto": [
        "https://news.google.com/rss/search?q=Bitcoin+Ethereum+stablecoin+crypto+regulation+market&hl=en-US&gl=US&ceid=US:en",
    ],
    "Macro Data": [
        "https://news.google.com/rss/search?q=CPI+PPI+jobs+GDP+retail+sales+FOMC+inflation&hl=en-US&gl=US&ceid=US:en",
        "https://www.federalreserve.gov/feeds/press_monetary.xml",
        "https://apps.bea.gov/rss/rss.xml",
    ],
}

TRUSTED_SOURCE_HINTS = (
    "Reuters",
    "CNBC",
    "Yahoo Finance",
    "MarketWatch",
    "Financial Times",
    "Federal Reserve",
    "BLS",
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
MAX_TOTAL_ITEMS = 22
TELEGRAM_LIMIT = 4096


@dataclass(frozen=True)
class NewsItem:
    section: str
    title: str
    source: str
    link: str
    published: str


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


def split_google_news_title(title: str) -> tuple[str, str]:
    title = html.unescape(title).strip()
    if " - " not in title:
        return title, "Unknown"
    headline, source = title.rsplit(" - ", 1)
    return headline.strip(), source.strip()


def infer_source(feed_url: str) -> str:
    if "federalreserve.gov" in feed_url:
        return "Federal Reserve"
    if "bea.gov" in feed_url:
        return "BEA"
    return "Unknown"


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
                "title": item.findtext("title", default="").strip(),
                "link": item.findtext("link", default="").strip(),
                "published": item.findtext("pubDate", default="").strip(),
            }
        )
    return items


def collect_news() -> list[NewsItem]:
    grouped: dict[str, list[NewsItem]] = defaultdict(list)
    seen_titles: set[str] = set()

    for section, feeds in RSS_FEEDS.items():
        for feed_url in feeds:
            try:
                raw_items = fetch_rss(feed_url)
            except Exception as exc:
                print(f"Skipping RSS feed after fetch error: {feed_url} ({exc})", file=sys.stderr)
                continue

            for raw_item in raw_items:
                if "news.google.com" in feed_url:
                    headline, source = split_google_news_title(raw_item["title"])
                else:
                    headline = html.unescape(raw_item["title"]).strip()
                    source = infer_source(feed_url)
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
                    )
                )

    selected: list[NewsItem] = []
    for section, items in grouped.items():
        selected.extend(rank_items(items)[:MAX_ITEMS_PER_SECTION])

    return selected[:MAX_TOTAL_ITEMS]


def rank_items(items: list[NewsItem]) -> list[NewsItem]:
    def score(item: NewsItem) -> tuple[int, str]:
        trusted = any(source in item.source for source in TRUSTED_SOURCE_HINTS)
        return (1 if trusted else 0, item.published)

    return sorted(items, key=score, reverse=True)


def build_prompt(items: list[NewsItem]) -> str:
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")
    source_lines = []
    for idx, item in enumerate(items, start=1):
        source_lines.append(
            textwrap.dedent(
                f"""
                {idx}. Section: {item.section}
                   Original English headline: {item.title}
                   Source: {item.source}
                   Published: {item.published}
                   Link: {item.link}
                """
            ).strip()
        )

    return textwrap.dedent(
        f"""
        You are an overseas economy news analyst writing for Korean retail investors.

        Create a concise Korean Telegram briefing using only the news items below.
        Do not invent facts. Avoid clickbait, rumors, and unsupported certainty.
        If an item is weak, repetitive, or not market-relevant, skip it.

        Required output sections:
        1. Global Market
        2. AI / Semiconductor
        3. Energy / Oil
        4. Crypto
        5. Macro Data
        6. Korea Market Impact
        7. X Post Ideas

        For each selected news item, include:
        - Korean summary
        - Original English headline
        - Source name
        - Link
        - Why it matters to Korean investors

        Style:
        - Write in Korean.
        - Keep it useful for investment preparation, not sensational.
        - Korea Market Impact should connect the news to Korean stocks, KRW/USD,
          semiconductors, oil-sensitive sectors, and rates where relevant.
        - X Post Ideas should be 3 short Korean post ideas.
        - Keep the whole answer under 3,500 Korean characters.

        Briefing time: {today}

        News items:
        {chr(10).join(source_lines)}
        """
    ).strip()


def summarize_with_openai(openai_api_key: str, items: list[NewsItem]) -> str:
    client = OpenAI(api_key=openai_api_key)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        input=build_prompt(items),
        temperature=0.2,
    )
    return response.output_text.strip()


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


def build_free_briefing(items: list[NewsItem]) -> str:
    today = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M KST")
    if not items:
        return f"해외 경제 뉴스 브리핑\n{today}\n\n오늘 수집된 해외 경제 뉴스가 없습니다."

    grouped: dict[str, list[NewsItem]] = defaultdict(list)
    for item in items:
        grouped[item.section].append(item)

    lines = [
        "해외 경제 뉴스 브리핑",
        today,
        "",
        "AI 요약 대신 무료 RSS 기반으로 생성한 브리핑입니다.",
        "",
    ]

    for section in RSS_FEEDS:
        section_items = grouped.get(section, [])[:3]
        if not section_items:
            continue
        lines.append(f"[{SECTION_LABELS.get(section, section)}]")
        for idx, item in enumerate(section_items, start=1):
            lines.extend(
                [
                    f"{idx}. {item.title}",
                    f"Source: {item.source}",
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
            "1. 해외 뉴스 먼저 보면 한국 시장 대응 속도가 달라진다",
            "2. 한국 증시는 미국 금리와 반도체 뉴스의 영향을 크게 받는다",
            "3. 유가와 환율은 한국 기업 실적을 볼 때 빠질 수 없는 변수다",
        ]
    )
    return "\n".join(lines).strip()


def summarize_news(openai_api_key: str | None, items: list[NewsItem]) -> str:
    if not items:
        return "오늘 수집된 해외 경제 뉴스가 없습니다."
    if not openai_api_key:
        return build_free_briefing(items)

    try:
        return summarize_with_openai(openai_api_key, items)
    except Exception as exc:
        print(f"OpenAI summarization failed, using free RSS fallback: {exc}", file=sys.stderr)
        return build_free_briefing(items)


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
        response.raise_for_status()


def main() -> int:
    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        bot_token = require_env("TELEGRAM_BOT_TOKEN")
        chat_id = require_env("TELEGRAM_CHAT_ID")

        news_items = collect_news()
        briefing = summarize_news(openai_api_key, news_items)
        send_telegram_message(bot_token, chat_id, briefing)
    except Exception as exc:
        print(f"Failed to send overseas economy briefing: {exc}", file=sys.stderr)
        return 1

    print("Overseas economy briefing sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
