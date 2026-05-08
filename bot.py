from __future__ import annotations

import os
import tempfile
from pathlib import Path

from alerter import send_telegram
from contract_analyzer import analyze_pdf
from utils import load_dotenv
from vault import recent_changes, stats


def format_stats() -> str:
    current = stats()
    return "\n".join(
        [
            "Silent Witness stats",
            f"Changes: {current['changes']}",
            f"Critical: {current['critical']}",
            f"Moderate: {current['moderate']}",
            f"Contracts: {current['contracts']}",
        ]
    )


def format_history(limit: int = 5) -> str:
    rows = recent_changes(limit)
    if not rows:
        return "No changes stored yet."
    lines = ["Recent policy changes"]
    for row in rows:
        lines.append(f"{row['detected_at']} - {row['service']} - {row['severity']} - {row['summary']}")
    return "\n".join(lines)


def _run_telegram_bot() -> int:
    try:
        from telegram import Update
        from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
    except ImportError:
        print("python-telegram-bot is not installed. Install with: pip install python-telegram-bot")
        return 1

    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("TELEGRAM_TOKEN is missing. Put it in .env or your shell environment.")
        return 1

    async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(format_history())

    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(format_stats())

    async def pdf(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        document = update.message.document
        if not document or not document.file_name.lower().endswith(".pdf"):
            return
        await update.message.reply_text("Analyzing PDF contract...")
        file = await context.bot.get_file(document.file_id)
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / document.file_name
            await file.download_to_drive(target)
            try:
                result = analyze_pdf(target, str(update.effective_chat.id))
                clause = result["clauses"][0] if result["clauses"] else {}
                await update.message.reply_text(
                    "\n".join(
                        [
                            f"Contract risk: {result['severity']} ({result['risk_score']}/100)",
                            result["summary"],
                            f"Top clause: {clause.get('clause', 'Detected clause')}",
                            f"Report: {result['report_path']}",
                        ]
                    )
                )
            except Exception as exc:
                await update.message.reply_text(f"Could not analyze PDF: {exc}")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(MessageHandler(filters.Document.PDF, pdf))
    print("Silent Witness Telegram bot running. Press Ctrl+C to stop.")
    app.run_polling()
    return 0


def main() -> int:
    load_dotenv()
    if os.getenv("TELEGRAM_TOKEN"):
        return _run_telegram_bot()

    print("Silent Witness bot local mode")
    print("Set TELEGRAM_TOKEN to enable Telegram polling.")
    print("")
    print("/stats")
    print(format_stats())
    print("")
    print("/history")
    print(format_history())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
