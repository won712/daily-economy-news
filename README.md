# Daily Economy News

Overseas economic and financial news briefing bot for Korean investors.

The bot collects overseas market news through RSS feeds, asks OpenAI to summarize it in Korean, groups the briefing by investment theme, and sends the result to Telegram.

## Sections

- Global Market
- AI / Semiconductor
- Energy / Oil
- Crypto
- Macro Data
- Korea Market Impact
- X Post Ideas

## Required GitHub Actions secrets

- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Run

Open the repository on GitHub, go to **Actions**, choose **Overseas economy briefing**, and click **Run workflow**.

The workflow also runs every day at 7:30 AM Korea time.
