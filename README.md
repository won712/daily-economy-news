# Daily Economy News

Free overseas economic and financial news briefing bot for Korean investors.

The bot collects overseas market news through public RSS feeds, keeps only items published within the last 6 hours, groups them by investment theme, and sends the result to Telegram. It does not use the OpenAI API, so no OpenAI key or API billing is required.

## Operating Principles

1. Run every morning at 7:30 AM Seoul time.
2. Include only news published within the last 6 hours.
3. Focus on news that may affect US stocks, AI stocks/semiconductors, crypto markets, or macro/rates.
4. Use only credible overseas sources.

## Sources

The bot prioritizes these overseas finance and market sources through public RSS or Google News RSS `site:` searches:

- Reuters
- CNBC
- MarketWatch
- Yahoo Finance
- Investing.com
- Bloomberg
- Financial Times
- The Wall Street Journal
- Federal Reserve / BEA official updates

## Sections

- US Stock Market
- AI
- Crypto
- Macro / Rates
- Korea Market Impact
- X Post Ideas

## Freshness Rule

Only news with a published timestamp within the last 6 hours is included. Older items are skipped automatically.

## GitHub Actions secrets

Add these in **Settings > Secrets and variables > Actions > Repository secrets**.

| Secret name | Required? | Secret value |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Required | Token from BotFather |
| `TELEGRAM_CHAT_ID` | Required | Your Telegram chat id number |

Important: put the text on the left in the **Name** field, and put your real token/id in the **Secret** field.

## Run

Open the repository on GitHub, go to **Actions**, choose **Overseas economy briefing**, and click **Run workflow**.

The workflow runs every day at 7:30 AM Korea time.
