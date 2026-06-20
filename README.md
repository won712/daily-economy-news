# Daily Economy News

Overseas economic and financial news briefing bot for Korean investors.

The bot collects overseas market news through RSS feeds, groups it by investment theme, and sends the result to Telegram.

If `OPENAI_API_KEY` is available and has quota, the bot asks OpenAI to create a Korean investor briefing. If the key is missing or quota is unavailable, the bot still sends a free RSS-based briefing without AI summarization.

## Sections

- Global Market
- AI / Semiconductor
- Energy / Oil
- Crypto
- Macro Data
- Korea Market Impact
- X Post Ideas

## GitHub Actions secrets

Add these in **Settings > Secrets and variables > Actions > Repository secrets**.

| Secret name | Required? | Secret value |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | Required | Token from BotFather |
| `TELEGRAM_CHAT_ID` | Required | Your Telegram chat id number |
| `OPENAI_API_KEY` | Optional | Your OpenAI API key, only if you want AI summaries |

Important: put the text on the left in the **Name** field, and put your real key/token/id in the **Secret** field.

## Run

Open the repository on GitHub, go to **Actions**, choose **Overseas economy briefing**, and click **Run workflow**.

The workflow also runs every day at 7:30 AM Korea time.
