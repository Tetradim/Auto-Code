# Tutorial 5: Performance Lab — Is the Bot Profitable?

This is your report card.

### Must-know metrics explained for beginners:

- **Equity Curve (top graph):** Should trend upward with small dips. Big jagged drops = too much risk. Smooth = healthy.
- **Max Drawdown:** The largest % drop from a peak. Think of it as "how bad did it feel at the worst moment?" Keep this under 15% until you trust the system.
- **Profit Factor:** Total money won ÷ total money lost. 1.6+ means for every $1 lost you made $1.60. This is more important than win rate.
- **Expectancy:** Average profit per trade. Even $8 per trade at 10 trades per day compounds to serious money.

### How to use the Recent Trades table:
- Sort by "edge_at_entry" — you will see that trades above 75 almost always win.
- Look at the "reason" column. Over time you will recognize patterns the bot loves.
- If you see many "Storm" or "Choppy" reasons with losses, lower max_leverage in config.

**Rule of thumb:** After 30–50 trades, if Profit Factor > 1.5 and Max Drawdown < 15%, the bot has a real edge. Keep running it. If not, tweak only one parameter at a time and re-test.