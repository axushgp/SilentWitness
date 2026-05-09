#!/usr/bin/env python3

import sys
sys.path.append('.')

from mike_bridge import analyze_policy

# Test policy diff
diff_text = """+ We may now share your data with third parties for advertising purposes.
+ New terms about AI training on user content.
- Removed previous privacy guarantees."""

result = analyze_policy('test_service', None, diff_text)

print('Policy analysis result:')
print('Source:', result.source)
print('Error:', result.error)
print('Report path:', result.report_path)
print('Clauses found:', len(result.clauses))

for i, clause in enumerate(result.clauses, 1):
    print(f'\n{i}. {clause.get("clause", "Unknown")}')
    print(f'   Severity: {clause.get("severity", "N/A")}')
    print(f'   Risk points: {clause.get("risk_points", "N/A")}')
    print(f'   Implication: {clause.get("legal_implication", "")}')
    if clause.get("before"):
        print(f'   Before: {clause.get("before")[:100]}...')
    if clause.get("after"):
        print(f'   After: {clause.get("after")[:100]}...')