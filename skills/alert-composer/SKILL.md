# Skill: AlertComposer

## Purpose
Compose and send a Telegram alert combining all skill outputs.

## Only runs for CRITICAL or MODERATE severity.

## Message format
*Silent Witness Alert*
!! *{SEVERITY}* - {SERVICE}

*What changed:*
{summary from SeverityClassifier}

*Risk Score:* {total}/100 - {primary_driver}

*DPDP:* {top flag or "No India-specific risk detected"}

*Opt-out:*
{opt-out step 1 or "No opt-out available"}

*Deadline:* {deadline or "None stated"}

## Steps
1. Assemble message from all skill outputs
2. Send via Telegram to configured chat ID
3. Log to memory with timestamp, service, severity
