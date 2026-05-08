# Silent Witness

> Your contracts are being rewritten while you sleep. Silent Witness reads every word.

An always-on OpenClaw agent that monitors TOS updates, privacy policy changes, and contract revisions across 50+ services - classifies severity, scores legal risk across four axes, maps violations against India's DPDP Act 2023, and delivers plain-English alerts on Telegram before the change takes effect.

[GITHUB REPO PERMALINK](https://github.com/axushgp/SilentWitness)\
[PPT LINK](https://docs.google.com/presentation/d/1z1OGb6tLODgFdZf7GlQUzgHOImgapDm3pRPOicn9LRQ/edit?usp=sharing)\
[AI DISCLOSURE](https://docs.google.com/document/d/1AC6hUf9N87qQfKxpL-CnC3KtWluiMi69A5mpDoeWZn4/edit?usp=sharing)\
[DEMO VIDEO]()

---

## The Problem

Every time you tap "I AGREE" on a new app, you enter a legal contract. You almost certainly did not read it. Platforms change these documents silently, relying on a buried email notification that qualifies as legal notice.

- 8.5B+ people have agreed to TOS they never read
- 97 minutes - time it would take to read all TOS for services used in one average day
- Rs.18,000 Cr lost annually in India to subscription traps
- 0.06% of users read a privacy policy before clicking agree
- In 2022, PayPal quietly added a $2,500 fine for "misinformation" - caught only because one journalist happened to notice

No tool exists today that monitors these continuously, autonomously, and in plain language. Until now.

---

## Architecture

Silent Witness runs as two open-source systems in tandem, entirely locally:

```
OpenClaw (Pi Agent Runtime)          Mike OSS (Legal AI Sidecar)
        |                                       |
   Heartbeat Scheduler                  Tabular Clause Extraction
   Skill Orchestration          <-->    Before/After Legal Analysis
   Telegram Delivery                    .docx Report Generation
   Vault Query Interface                Page-Level Citations
```

### OpenClaw 5-Layer Mapping

| Layer | Component | Role in Silent Witness |
|-------|-----------|----------------------|
| L1 | Telegram | Outbound alerts, conversational queries |
| L2 | ProtocolAdapter | Normalises Telegram commands to agent instructions |
| L3 | Gateway | Session management, heartbeat scheduling |
| L4 | Pi Agent Loop | Diff, classify, score, compose |
| L5 | Skill Execution | 9 custom SKILL.md files |

---

## Features

### Core Pipeline
- **Autonomous heartbeat crawler** - monitors 6+ service URLs every 2 hours using httpx and BeautifulSoup snapshot diffing
- **Unified diff engine** - compares today's policy snapshot against yesterday's, extracts changed lines
- **LLM severity classifier** - classifies changes as CRITICAL / MODERATE / LOW using llama3.2:1b running locally via Ollama. Zero API cost.

### Legal Intelligence Layer
- **4-axis risk scorer** - scores 0-100 across data rights exposure, financial liability, IP risk, and service continuity
- **DPDP Act 2023 compliance overlay** - maps every detected change against Sections 4, 6, 8, 11, 16 of India's Digital Personal Data Protection Act 2023. First tool to do this.
- **Mike OSS tabular extraction** - CRITICAL findings piped through Mike (open-source Harvey/Legora alternative) for clause-by-clause legal analysis with before/after table and page-level citations
- **Opt-out navigator** - identifies exact opt-out mechanism and generates step-by-step instructions

### User Interface
- **PDF contract ingestion** - forward any NDA or contract PDF to the Telegram bot, receive risk breakdown in 60 seconds
- **SQLite change vault** - every detected change stored permanently, queryable conversationally
- **Telegram commands** - `/history`, `/stats`, direct PDF upload
- **Zero new app required** - entirely Telegram-native. Adoption barrier is zero.

### Privacy
- Fully local - no document ever leaves the machine
- Knox-compatible privacy architecture
- All snapshots, diffs, and vault data stored in `~/.openclaw/`

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Runtime | OpenClaw 2026 (Pi agent embedded) |
| LLM | Ollama llama3.2:1b (local inference) |
| Legal Analysis | Mike OSS (self-hosted) |
| Crawler | Python httpx + BeautifulSoup4 |
| Diff Engine | Python difflib (unified diff) |
| Database | SQLite |
| PDF Parsing | PyMuPDF (fitz) |
| Delivery | python-telegram-bot |
| Scheduling | OpenClaw heartbeat cron |
| OS | Ubuntu 22.04 (WSL2 compatible) |

---

## Project Structure

```
silent-witness/
  crawler.py              # Fetches and saves policy page snapshots
  differ.py               # Unified diff between today and yesterday
  classifier.py           # Ollama LLM severity classification
  alerter.py              # Telegram alert delivery
  vault.py                # SQLite change and contract vault
  bot.py                  # Telegram bot (PDF ingestion + queries)
  silent_witness.py       # Master pipeline orchestrator
  simulate_change.py      # Demo simulation script

  .openclaw/
    workspace/
      SOUL.md             # Agent identity and rules
      HEARTBEAT.md        # Autonomous run checklist
    skills/
      policy-crawler/SKILL.md
      policy-differ/SKILL.md
      severity-classifier/SKILL.md
      risk-scorer/SKILL.md
      dpdp-checker/SKILL.md
      alert-composer/SKILL.md
      mike-bridge/SKILL.md
    snapshots/
      watchlist.md        # Services being monitored
      *.html              # Daily snapshots
      reports/            # Mike-generated .docx reports
```

---

## Setup

### Prerequisites

- Ubuntu 22.04 or WSL2 on Windows
- Node.js 18+
- Python 3.10+
- Telegram bot token (from @BotFather)

### Step 1 - Install OpenClaw

```bash
sudo npm install -g openclaw
openclaw onboard
```

Select Ollama as model provider, Telegram as channel. Follow the wizard.

### Step 2 - Install Ollama and model

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:1b
```

### Step 3 - Install Python dependencies

```bash
pip3 install httpx beautifulsoup4 python-telegram-bot pymupdf python-dotenv --break-system-packages
```

### Step 4 - Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/silent-witness
cd silent-witness
```

Set your credentials:

```bash
export TELEGRAM_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

Get your chat ID: message your bot once, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and find the `id` field under `chat`.

### Step 5 - Create workspace

```bash
mkdir -p ~/.openclaw/workspace
mkdir -p ~/.openclaw/skills/{policy-crawler,policy-differ,severity-classifier,risk-scorer,dpdp-checker,alert-composer,mike-bridge}
mkdir -p ~/.openclaw/snapshots/reports
```

Copy the SOUL.md, HEARTBEAT.md, and all SKILL.md files from the `.openclaw/` folder in this repo to `~/.openclaw/`.

### Step 6 - Install Mike OSS (optional, for tabular legal analysis)

```bash
git clone https://github.com/willchen96/mike ~/mike
npm install --prefix ~/mike/backend
cp ~/mike/backend/.env.example ~/mike/backend/.env
# Fill in your Supabase and LLM API keys in .env
npm run dev --prefix ~/mike/backend
```

---

## Usage

### Run a manual heartbeat

```bash
python3 silent_witness.py
```

### Simulate a CRITICAL change for demo

```bash
python3 simulate_change.py spotify
python3 silent_witness.py
```

### Run the Telegram bot (PDF ingestion + queries)

```bash
pkill -f openclaw   # stop OpenClaw to avoid bot conflict
python3 bot.py
```

### Telegram commands

| Command | Action |
|---------|--------|
| `/history` | Last 5 detected policy changes |
| `/stats` | Vault statistics |
| Send a PDF | Analyze contract, return risk breakdown |

### Run OpenClaw autonomous mode

```bash
openclaw
```

The heartbeat runs every 2 hours automatically per `HEARTBEAT.md`.

---

## Watchlist

Edit `~/.openclaw/snapshots/watchlist.md` to add or remove services:

```markdown
| Service  | URL |
|----------|-----|
| spotify  | https://www.spotify.com/us/legal/privacy-policy/ |
| github   | https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement |
| notion   | https://www.notion.so/Privacy-Policy |
| netflix  | https://www.netflix.com/in/privacy |
| whatsapp | https://www.whatsapp.com/legal/privacy-policy |
| google   | https://policies.google.com/privacy |
```

---

## DPDP Act 2023 Coverage

Silent Witness maps every detected change against the following sections of India's Digital Personal Data Protection Act 2023:

| Section | Coverage |
|---------|----------|
| Section 4 | Lawful purpose and consent requirement |
| Section 6 | Free, specific, informed, unconditional consent |
| Section 8 | Data fiduciary obligations - accuracy, security, deletion |
| Section 11 | Right to withdraw consent |
| Section 16 | Cross-border data transfer restrictions |

---

## Risk Scoring

Every detected change is scored 0-100 across four axes:

| Axis | Max Score | Triggers |
|------|-----------|---------|
| Data Rights Exposure | 25 | Third-party sharing, advertising, data sale |
| Financial Liability | 25 | Fees, penalties, arbitration clauses |
| IP Risk | 25 | Content ownership, AI training, licensing |
| Service Continuity | 25 | Termination rights, throttling, service modification |

---

## License

MIT

---
