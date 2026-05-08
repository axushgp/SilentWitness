# Heartbeat (every 2 hours)

1. Run policy-crawler - crawl all URLs in snapshots/watchlist.md
2. Run policy-differ - diff each against yesterday's snapshot
3. For non-trivial diffs: run severity-classifier and risk-scorer
4. For CRITICAL or MODERATE: run dpdp-checker, mike-bridge, opt-out-navigator
5. Run alert-composer - send Telegram alert with full output
6. Log results to memory/YYYY-MM-DD.md with timestamp and severity
7. Sunday 7am only: run digest-composer, send weekly report
