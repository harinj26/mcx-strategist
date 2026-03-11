# MCX Natural Gas Strategist

An AI-powered morning briefing tool for MCX Natural Gas futures and options traders. Uses Claude Opus 4.6 with live web search to pull real-time market data and produce a structured pre-market analysis — delivered via a web UI or Telegram bot.

---

## What It Does

Every morning, the strategist autonomously:

1. Fetches the **NYMEX Natural Gas front-month price** (Henry Hub)
2. Fetches the **USD/INR spot rate** and calculates the implied MCX price
3. Pulls the latest **EIA weekly storage report** and compares to the 5-year average
4. Reads **NOAA 6-10 and 8-14 day temperature outlooks**
5. Scans for **geopolitical/LNG/TTF news**

Then produces a structured briefing with:
- Live data snapshot
- EIA storage analysis (Bullish/Bearish)
- Weather outlook interpretation
- Key support/resistance levels
- Scenario analysis
- Overall market sentiment

> No explicit buy/sell signals — all analysis is scenario-based.

---

## Project Structure

```
mcx-strategist/
├── app.py            # FastAPI web server (SSE streaming endpoint)
├── strategist.py     # Core analysis engine (Claude API + tools)
├── telegram_bot.py   # Telegram bot interface
├── templates/
│   └── index.html    # Browser UI
├── requirements.txt
└── .env              # API keys (not committed)
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- `uv` (recommended) or `pip`

### 2. Install dependencies

```bash
cd mcx-strategist

# With uv
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# Or with pip
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=123456:ABC...
```

**Getting your keys:**

- **Anthropic API key** — [console.anthropic.com](https://console.anthropic.com)
- **Telegram bot token** — Message [@BotFather](https://t.me/BotFather) on Telegram, use `/newbot`

---

## Running

### Option A — Web UI

```bash
python app.py
```

Open [http://localhost:8000](http://localhost:8000) in your browser and click **Analyze**.

### Option B — Telegram Bot

```bash
python telegram_bot.py
```

Then in your Telegram chat with the bot:

| Command    | Action                          |
|------------|---------------------------------|
| `/morning` | Run full morning analysis       |
| `/start`   | Welcome message + command list  |
| `/help`    | Same as `/start`                |

> Analysis takes 30–90 seconds as Claude fetches live data.

### Keeping the bot running (background)

```bash
nohup python telegram_bot.py > /tmp/mcx-bot.log 2>&1 &
```

Check logs:
```bash
tail -f /tmp/mcx-bot.log
```

Stop it:
```bash
pkill -f telegram_bot.py
```

---

## Notes

- Only **one bot instance** can run at a time. Running two causes a `409 Conflict` error — kill the old process before starting a new one.
- The **rate limit error** from Anthropic means you've hit the Claude API usage limit. Wait a few minutes and retry.
- The model used is `claude-opus-4-6` with `adaptive` thinking and `web_search` / `web_fetch` tools enabled.
