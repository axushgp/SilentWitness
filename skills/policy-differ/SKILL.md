# Skill: PolicyDiffer

## Purpose
Compare today's snapshot against yesterday's and extract changed lines.

## Steps
1. For each service in watchlist.md, find today and yesterday snapshots
2. Strip HTML to plain text before diffing
3. Run unified diff - extract only added (+) and removed (-) lines
4. If diff is under 5 lines, classify as trivial - skip
5. Return diff_text and service_name to next skill

## Output
diff_text: string of changed lines, capped at 100 lines
status: diff_found | no_change | no_baseline
