# Skill: RiskScorer

## Purpose
Produce a numerical legal risk score (0-100) for a detected policy change.

## Scoring axes (25 points each)
- Data Rights Exposure: does change expand what data is collected or shared?
- Financial Liability: does it introduce fees, penalties, or binding arbitration?
- IP Risk: does it affect ownership of user content or restrict user rights?
- Service Continuity: can platform now terminate, throttle, or modify service?

## Steps
1. Read diff_text and severity from SeverityClassifier
2. Score each axis 0-25 based on the change
3. Sum to produce total score 0-100
4. Write one sentence explaining the primary risk driver
5. Return: total_score, data_score, financial_score, ip_score, continuity_score, primary_driver

## Format for alert
"Risk Score: {total}/100 - {primary_driver}"
