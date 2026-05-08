# Skill: MikeBridge

## Purpose
Send a full policy document to Mike OSS backend for legal-grade tabular
clause extraction with page-level citations.

## When to run
Only on CRITICAL or MODERATE severity. Skip for LOW or NO_CHANGE.

## Steps
1. Read full today snapshot HTML for the affected service
2. POST to http://localhost:3001/api/analyze:
   { "document": cleaned_text, "mode": "tabular_review", "service": service_name }
3. Parse response: array of { clause_name, before_text, after_text, implication }
4. Format as markdown table
5. POST to http://localhost:3001/api/export/docx to get report file
6. Save .docx to ~/.openclaw/snapshots/reports/{service}_{date}.docx
7. Return clause table to alert-composer

## Fallback
If Mike backend unreachable, log warning and skip. Do not block the alert.
