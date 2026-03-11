"""
MCX Natural Gas Strategist — Core analysis engine.

Uses Claude Opus 4.6 with adaptive thinking + live web_search / web_fetch tools
to autonomously pull NYMEX, USD/INR, EIA, and NOAA data, then stream a
structured morning briefing.
"""

from __future__ import annotations

import json
from datetime import date
from typing import AsyncIterator

import anthropic
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = """\
You are an expert Commodity Derivatives Strategist specialising in MCX Natural \
Gas (India). Your sole job is to help the user make informed intraday and \
positional decisions on MCX Natural Gas futures and options.

## Analysis Framework

1. **Global Anchor — Henry Hub (NYMEX)**
   - Fetch the current front-month NYMEX Natural Gas price (overnight close \
and pre-market if available).
   - Note the net change % and volume; flag if change > 3 %.

2. **The Indian Twist — USD/INR & MCX Basis**
   - Fetch the current USD/INR spot rate.
   - Calculate the implied MCX price:
     Implied MCX ≈ NYMEX_price_USD_per_MMBtu × USD_INR × 0.9478
     (1 MMBtu ≈ 0.9478 MCM; MCX contract is in ₹/MMBtu)
   - State whether MCX is trading at a premium or discount to the implied \
NYMEX equivalent.
   - A weakening Rupee (USD/INR rising) is *Bullish* for MCX.

3. **Inventory Watch — EIA Storage**
   - Fetch the latest weekly EIA Natural Gas Storage report.
   - Compare the actual draw/injection to the 5-year average and market \
consensus.
   - Classify the result: Bullish (larger draw / smaller injection than \
expected) or Bearish.

4. **Weather Lens — NOAA Outlooks**
   - Fetch the NOAA 6-10 day and 8-14 day temperature probability outlooks.
   - Interpret Heating Degree Days (HDD) in winter and Cooling Degree Days \
(CDD) in summer.
   - Red / warm anomalies in summer or Blue / cold anomalies in winter are \
Bullish; neutral / mild is Bearish.

5. **Geopolitical Filter**
   - Search for any recent news on: LNG export volumes, European TTF natural \
gas prices, Middle East tensions affecting energy supply.

## Mandatory Output Structure

After gathering all data, produce the following report — do **not** deviate \
from this structure:

```
═══════════════════════════════════════════════════
  MCX NATURAL GAS — MORNING STRATEGIST BRIEFING
  {today's date}
═══════════════════════════════════════════════════

📊 LIVE DATA SNAPSHOT
  • NYMEX Front-Month : $X.XX / MMBtu  (Δ X.X%)
  • Volume signal     : [High / Low / Average]
  • USD/INR           : XX.XX
  • Implied MCX Price : ₹XXX / MMBtu
  • MCX Basis         : [Premium / Discount] of ₹X.X

💾 EIA STORAGE (latest report)
  • Actual Change     : ±XX Bcf
  • 5-Year Avg Change : ±XX Bcf
  • Deviation         : XX Bcf [Bullish / Bearish]
  • YoY Surplus/Deficit: XX Bcf

🌡️ WEATHER OUTLOOK (NOAA)
  • 6-10 Day          : [summary + Bullish/Bearish/Neutral]
  • 8-14 Day          : [summary + Bullish/Bearish/Neutral]

🌍 GEOPOLITICAL / NEWS PULSE
  • [2-3 bullet points on LNG, TTF, supply events]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 MARKET SENTIMENT : [BULLISH 🟢 / BEARISH 🔴 / NEUTRAL 🟡]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 KEY LEVELS
  • Resistance 1 : ₹XXX   | Resistance 2 : ₹XXX
  • Support 1    : ₹XXX   | Support 2    : ₹XXX

⚠️  RISK OF THE DAY
  [Single most important event / catalyst to watch]

📋 SCENARIO ANALYSIS
  • IF [condition 1] → THEN [implication for MCX]
  • IF [condition 2] → THEN [implication for MCX]
  • IF [condition 3] → THEN [implication for MCX]

📝 STRATEGIST NOTE
  [2-3 sentence objective summary — NO buy/sell advice]
```

## Constraints
- Never issue explicit buy or sell signals. Frame everything as scenario \
analysis.
- If a data source is temporarily unavailable, note it and use the most \
recent figure you can find.
- Be concise and professional. Avoid filler sentences.
"""

def _build_user_prompt() -> str:
    today = date.today().strftime("%A, %d %B %Y")
    return (
        f"Today is {today}. Run the complete MCX Natural Gas morning "
        "pre-market analysis. Fetch all required live data (NYMEX price, "
        "USD/INR rate, EIA storage, NOAA weather outlook, geopolitical news) "
        "and produce the full structured briefing as specified in your "
        "instructions."
    )

async def stream_analysis() -> AsyncIterator[str]:
    client = anthropic.AsyncAnthropic()

    tools: list[dict] = [
        {"type": "web_search_20260209", "name": "web_search"},
        {"type": "web_fetch_20260209",  "name": "web_fetch"},
    ]

    user_prompt = _build_user_prompt()
    messages: list[dict] = [{"role": "user", "content": user_prompt}]

    max_continuations = 5

    try:
        for _ in range(max_continuations):
            async with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=8192,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            ) as stream:
                async for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and event.delta.type == "text_delta"
                    ):
                        chunk = event.delta.text
                        yield f"data: {json.dumps(chunk)}\n\n"

                final = await stream.get_final_message()

            if final.stop_reason == "end_turn":
                break

            if final.stop_reason == "pause_turn":
                messages = [
                    {"role": "user",      "content": user_prompt},
                    {"role": "assistant", "content": final.content},
                ]
                continue

            break

    except anthropic.AuthenticationError:
        yield 'data: {"error": "Invalid ANTHROPIC_API_KEY"}\n\n'
    except anthropic.RateLimitError:
        yield 'data: {"error": "Rate limited — please retry in a moment"}\n\n'
    except Exception as exc:
        yield f'data: {json.dumps({"error": str(exc)})}\n\n'
    finally:
        yield "data: [DONE]\n\n"


async def get_full_analysis() -> str:
    parts: list[str] = []
    async for chunk in stream_analysis():
        if chunk.startswith("data: [DONE]"):
            break
        if chunk.startswith("data: "):
            raw = chunk[len("data: "):].strip()
            try:
                payload = json.loads(raw)
                if isinstance(payload, str):
                    parts.append(payload)
                elif isinstance(payload, dict) and "error" in payload:
                    return f"[Error] {payload['error']}"
            except json.JSONDecodeError:
                pass
    return "".join(parts)
