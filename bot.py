import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import anthropic
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
TARGET_CHAT_ID     = int(os.environ["TARGET_CHAT_ID"])
DB_PATH            = "tsuki.db"
PORT               = int(os.environ.get("PORT", 8080))

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("tsuki-bot")

claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── Keep-alive server (for UptimeRobot) ──────────────────────────────────────

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Tsuki bot is alive.")
    def log_message(self, *args):
        pass  # suppress noisy HTTP logs

def run_ping_server():
    server = HTTPServer(("0.0.0.0", PORT), PingHandler)
    log.info(f"Ping server running on port {PORT}")
    server.serve_forever()

# ── Database ──────────────────────────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id    INTEGER NOT NULL,
            username   TEXT,
            full_name  TEXT,
            text       TEXT NOT NULL,
            timestamp  TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()


def save_message(chat_id: int, username: str | None, full_name: str, text: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO messages (chat_id, username, full_name, text, timestamp) VALUES (?,?,?,?,?)",
        (chat_id, username, full_name, text, datetime.now(timezone.utc).isoformat()),
    )
    con.commit()
    con.close()


def get_messages_since(chat_id: int, hours: int = 12) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT username, full_name, text, timestamp FROM messages "
        "WHERE chat_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
        (chat_id, cutoff),
    ).fetchall()
    con.close()
    return [{"username": r[0], "full_name": r[1], "text": r[2], "ts": r[3]} for r in rows]


# ── Summary ───────────────────────────────────────────────────────────────────

def build_summary(messages: list[dict]) -> str:
    if not messages:
        return "🌙 TSUKI 12H DIGEST\n──────────────────\nChat was quiet this window. Nothing to summarise."

    chat_log = "\n".join(
        f"[{m['full_name']} (@{m['username'] or 'anon'})]: {m['text']}"
        for m in messages
    )

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system="""You are a summariser bot for a crypto Telegram group called $TSUKI.
Summarise the last 12 hours of chat into a short digest using this format:

🌙 TSUKI 12H DIGEST
──────────────────
📌 Main topics: [brief]
💬 Highlights: [1-2 notable moments]
🔥 Hype: [anything exciting, or 'quiet window']
❓ Open questions: [unanswered questions, or 'none']
──────────────────
Keep it concise and crypto-native in tone.""",
        messages=[{"role": "user", "content": f"Chat log:\n\n{chat_log}"}],
    )
    return msg.content[0].text


# ── Handlers ──────────────────────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.text:
        return
    user = msg.from_user
    save_message(
        chat_id=msg.chat_id,
        username=user.username if user else None,
        full_name=user.full_name if user else "Unknown",
        text=msg.text,
    )


async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Generating digest... 🌙")
    messages = get_messages_since(update.effective_chat.id, hours=12)
    await update.message.reply_text(build_summary(messages))


async def cmd_chatid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Chat ID: `{update.effective_chat.id}`", parse_mode="Markdown"
    )


# ── Scheduled job ─────────────────────────────────────────────────────────────

async def job_summary(app: Application):
    log.info("Posting scheduled 12h summary")
    messages = get_messages_since(TARGET_CHAT_ID, hours=12)
    await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=build_summary(messages))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    init_db()

    # Start ping server in background thread
    t = threading.Thread(target=run_ping_server, daemon=True)
    t.start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_summary, "cron", hour="8,20", minute=0, args=[app])
    scheduler.start()

    log.info("Bot running")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
