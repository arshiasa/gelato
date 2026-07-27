# Gelato House Passion Fruit Monitor 🍧

Automated monitor and live dashboard to check the availability of **پشن فروت (Passion Fruit)** across **Shahrak Gharb** and **Velenjak** locations of Gelato House (`order.gelatohouse.ir`) every 15 minutes.

## Features
- **Live Scraper**: Checks pre-rendered DOM HTML for item availability.
- **Telegram Notifications**: Outgoing alert dispatched when item status changes.
- **GitHub Actions Integration**: Automated serverless execution every 15 minutes (`.github/workflows/monitor.yml`).
- **Web Dashboard**: Responsive dark obsidian UI (`index.html`).

## GitHub Secrets Required
Add these under **Settings** -> **Secrets and variables** -> **Actions**:
- `TELEGRAM_BOT_TOKEN`: Telegram bot token from `@BotFather`.
- `TELEGRAM_CHAT_ID`: Recipient chat IDs (comma-separated).
