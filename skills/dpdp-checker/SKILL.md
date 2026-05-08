# Skill: DPDPChecker

## Purpose
Map a detected TOS change against India's Digital Personal Data Protection
Act 2023 (DPDP Act) and IT Act 2000. Flag violations or risks for Indian users.

## Key DPDP provisions to check
- Section 4: Personal data processed only for lawful purpose with consent
- Section 6: Consent must be free, specific, informed, unconditional
- Section 8: Obligations of data fiduciary - accuracy, security, deletion
- Section 11: Right to withdraw consent at any time
- Section 16: Transfer of personal data outside India (cross-border)

## Steps
1. Read diff_text
2. Check each DPDP section against the change
3. Flag any provision the change may violate
4. Note if change affects cross-border data transfer (Section 16)
5. Return: dpdp_flags as array of { section, risk, implication }

## Output format for alert
"DPDP Risk: Section {N} - {one line implication}"
## If no flags
"No India-specific regulatory risk detected"
