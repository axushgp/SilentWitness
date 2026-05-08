# Skill: SeverityClassifier

## Rubric
CRITICAL: New third-party data sharing, fees or penalties added, IP ownership
          change, arbitration clause added, opt-out deadline, surveillance expansion
MODERATE: Auto-renewal terms, price changes, account termination rights
LOW:      Typos, formatting, minor clarifications
NO_CHANGE: No meaningful difference detected

## Steps
1. Read diff_text from PolicyDiffer
2. Apply rubric - classify as CRITICAL / MODERATE / LOW / NO_CHANGE
3. Write one plain-English sentence on what changed
4. Note any deadline found in the changed text
5. Return: severity, summary, deadline

## Rule
When uncertain between two levels, always go higher.
