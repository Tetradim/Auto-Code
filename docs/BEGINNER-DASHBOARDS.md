# Sentinel Edge - Beginner's Guide to the Grafana Dashboards

This guide was written specifically for people who are **new to trading and crypto**. No experience is required. We will explain everything in plain English, like you're learning to drive a car for the first time.

---

### What is Sentinel Edge?

Sentinel Edge is an automated trading bot that searches for small, repeatable statistical **edges** (advantages) in volatile crypto perpetual markets.

It doesn't guess. It combines order flow, on-chain data, funding rates, and market regime detection to decide when it has enough confidence to trade.

The **Grafana dashboards** are your translation layer — they turn the bot's complex calculations into something a human can understand.

---

### How to Use This Guide

1. Import the dashboards from the `grafana/` folder in this repo.
2. Start with **"Master Overview"** → then go to **"Live Sentinel"**.
3. Read the **text panels** on each dashboard — they were written for beginners.

---

## Dashboard 1: Master Overview

**Purpose**: Shows the overall health and performance of the bot.

### Key Panels Explained

**Equity Curve (Main Chart)**
- This is the most important line on the entire dashboard.
- It shows how much money the account has made over time.
- **Good**: Steady upward trend with relatively small dips.
- **Warning**: Sharp drops or long flat periods.

**Current Drawdown**
- Measures how far the account has fallen from its highest point.
- Analogy: If your account hit $10,000 but is now at $8,700, you are in a 13% drawdown.
- Healthy range: **< 10%**. Above 18–20% is concerning.

**PNL Summary (Today / 7D / 30D / All Time)**
- Simple green = profit, red = loss.
- Look for consistent profitability over time rather than one huge green day.

**Win Rate vs Profit Factor**
- **Win Rate**: How often the bot is right (55–68% is good for this type of bot).
- **Profit Factor**: How much money we make on winning trades vs losing trades. **> 1.8 is strong**, > 2.5 is excellent.

**Sharpe Ratio**
- Tells you how well the bot performs relative to the risk it takes.
- > 1.5 is considered very good.

---

## Dashboard 2: Live Sentinel (Most Important for Beginners)

This dashboard shows **what the bot is thinking right now**.

### Key Panels Explained

**Current Market Regime**
- The bot detects what "weather" the market is in (Trending, Choppy, High Volatility, Calm, etc.).
- Different strategies work in different regimes.

**Edge Score (0–100)**
- The single most important number.
- **> 75** = Strong edge — bot is confident.
- **60–74** = Moderate edge.
- **< 55** = No trade.

**Signal Breakdown**
This panel lists *why* the bot wants to buy or sell. The more factors that agree, the higher quality the signal.

Common reasons you will see:
- Strong orderflow imbalance
- Funding rate extreme
- On-chain whale positioning
- Microstructure exhaustion
- Sentiment divergence

**Live Position Card**
Shows:
- Direction (Long or Short)
- Entry price
- Current unrealized PNL
- How long the trade has been open
- **Conviction Level** (Low / Medium / High)

**Risk Meter**
Displays current risk as a percentage of the account. Green = safe, Yellow = caution, Red = high risk.

---

## Dashboard 3: Trade Archaeology (Learning From The Past)

**Purpose**: Helps you understand how the bot has performed historically.

**Important Panels:**

- **Trade Outcome Distribution**: Histogram showing typical win and loss sizes.
- **Edge Type Performance**: Shows which combinations of signals worked best.
- **Drawdown Autopsy**: Shows what the market looked like during the worst losing periods.
- **Monthly Heatmap**: Visual calendar of performance.

---

## How to Read a Live Trade Signal (Beginner Checklist)

1. Open **Live Sentinel** dashboard.
2. Check the **Edge Score** — is it above 70?
3. Look at **Market Regime** — is this a regime where the bot usually wins?
4. Read the **Signal Breakdown** — do multiple independent signals agree?
5. Check the **Risk Meter** — is the position size reasonable?
6. Decide whether you want to let the bot take the trade.

---

## Green Flags vs Red Flags

**Green Flags**
- Edge Score consistently > 75
- Equity curve making higher highs and higher lows
- Drawdown staying below 10%
- Multiple signal types agreeing

**Red Flags**
- Edge Score rarely going above 65
- Long flat equity curve
- Drawdown > 18%
- Bot keeps trading during "Chaotic" regime

---

## Glossary (Plain English)

- **Edge**: A small statistical advantage the bot tries to exploit.
- **Drawdown**: How much the account has dropped from its peak.
- **Regime**: The current personality of the market.
- **Order Flow**: Watching whether aggressive buyers or sellers are winning in real time.
- **Profit Factor**: Total profits divided by total losses.
- **Conviction**: How strongly the bot believes in the current trade.

---

**Created by Grok for the Sentinel Edge community.**
Last updated: 2025
Feedback and suggestions are welcome.