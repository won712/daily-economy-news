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

Add these in **Settings > Secrets and variables > Actions > Repository secrets**.

| Secret name | Secret value |
| --- | --- |
| `OPENAI_API_KEY` | Your OpenAI API key |
| `TELEGRAM_BOT_TOKEN` | Token from BotFather |
| `TELEGRAM_CHAT_ID` | Your Telegram chat id number |

Important: put the text on the left in the **Name** field, and put your real key/token/id in the **Secret** field.

## Run

Open the repository on GitHub, go to **Actions**, choose **Overseas economy briefing**, and click **Run workflow**.

The workflow also runs every day at 7:30 AM Korea time.
