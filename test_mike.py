#!/usr/bin/env python3

import sys
sys.path.append('.')

from mike_bridge import analyze_contract_text

# Test contract text
test_text = """
This agreement contains confidentiality provisions and data sharing terms.
The parties agree to indemnify each other for any losses.
Data may be shared with third parties for processing.
Limitation of liability is set at $100,000.
"""

result = analyze_contract_text('test_contract.pdf', test_text)

print('Mike analysis result:')
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