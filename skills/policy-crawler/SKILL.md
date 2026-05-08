# Skill: PolicyCrawler

## Purpose
Fetch the current HTML of a policy/TOS page and save a local snapshot.

## When to use
Called during heartbeat. Crawl every URL in ~/.openclaw/snapshots/watchlist.md

## Steps
1. Read snapshots/watchlist.md to get service names and URLs
2. For each entry, fetch the URL using httpx with a standard browser user-agent
3. Save HTML to ~/.openclaw/snapshots/{service_name}_{today_date}.html
4. Strip script/style tags before saving to reduce noise
5. Log "Crawled {service_name}" to session log

## Error handling
If URL times out or returns non-200, log failure and skip. Do not retry.
