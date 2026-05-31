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

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
TARGET_CHAT_ID     = int(os.environ["TARGET_CHAT_ID"])
DB_PATH            = "tsuki.db"
PORT               = int(os.environ.get("PORT", 8080))

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
log = logging.getLogger("tsuki-bot")
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

ROTATING_POSTS = [
    """Welcome to Tsuki x RWA! 🐈‍⬛🤖

Dev is here and always has been. Everything is planned. There are no coincidences 🧩
Your job as a community member is to be a raider, detective and project cheerleader. Positive Vibes Always! 🕵🏽‍♂️🔍

🥇 "One community to rule them all"

🐈‍⬛ Tsuki x RWA Linktree (All links): https://linktr.ee/tsukionsol
🐈‍⬛ Welcome PDF: https://tinyurl.com/tsukipdf""",

    """new here? here's how to get $TSUKI 🐈‍⬛

[ADD WALLET + DEX STEPS HERE]

CA: [ADD CONTRACT ADDRESS]

drop any questions in the chat, someone will help you out""",

    """where are we headed 🗺️

[ADD ROADMAP PHASES HERE]

been a wild ride so far. still just getting started""",

    """marketing wallet + treasury 🏦

[ADD SOLSCAN LINK OR WALLET ADDRESS]

all on-chain. go look for yourself 🧩""",
]

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"alive.")
    def log_message(self, *args):
        pass

def run_ping_server():
    HTTPServer(("0.0.0.0", PORT), PingHandler).serve_forever()

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        username TEXT,
        full_name TEXT,
        text TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS post_index (
        id INTEGER PRIMARY KEY CHECK (id=1),
        idx INTEGER NOT NULL DEFAULT 0
    )""")
    con.execute("INSERT OR IGNORE INTO post_index (id, idx) VALUES (1, 0)")
    con.commit()
    con.close()

def save_message(chat_id, username, full_name, text):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO messages (chat_id, username, full_name, text, timestamp) VALUES (?,?,?,?,?)",
        (chat_id, username, full_name, text, datetime.now(timezone.utc).isoformat()),
    )
    con.commit()
    con.close()

def get_messages_since(chat_id, hours=12):
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT username, full_name, text, timestamp FROM messages "
        "WHERE chat_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
        (chat_id, cutoff),
    ).fetchall()
    con.close()
    return [{"username": r[0], "full_name": r[1], "text": r[2], "ts": r[3]} for r in rows]

def next_post():
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT idx FROM post_index WHERE id=1").fetchone()
    idx = row[0] % len(ROTATING_POSTS)
    con.execute("UPDATE post_index SET idx=? WHERE id=1", (idx + 1,))
    con.commit()
    con.close()
    return ROTATING_POSTS[idx]

def build_summary(messages):
    if not messages:
        return (
            "🌙 tsuki catch-up\n\n"
            "quiet one this window. check back in a few hours 🐈‍⬛"
        )
    chat_log = "\n".join(
        f"[{m['full_name']} (@{m['username'] or 'anon'})]: {m['text']}"
        for m in messages
    )
    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=700,
        system="""You write 12-hour chat summaries for a Telegram group called Tsuki x RWA. It's a crypto community.

Write like a real person texting a friend who missed the chat. Say what happened. Don't announce it, don't frame it, don't narrate it. Just say the thing.

Use this exact format with double line breaks between each section:

🌙 tsuki catch-up

[3-5 sentences covering what people actually talked about. mention specific topics, names, links, or anything that got shared. write like you were sitting in the chat]

[2-3 sentences on the best moment or thread. paraphrase what was said. don't say it was interesting or notable — just describe it]

[1-2 sentences on the vibe. was it busy, slow, tense, locked in? describe it like you felt it, not like you're labelling it]

[unanswered questions or threads still going. if nothing, write "nothing hanging"]

🔥 highlights
[2-3 of the best individual messages or moments as short punchy bullets. quote or closely paraphrase. no editorialising, just the moment]

[one short low-key sign-off, different each time]

---

Hard rules. Break any of these and rewrite the whole thing:

No em dashes. Use commas or periods.
No rule of three. Don't group things into trios every time. Two is fine. Four is fine.
No "it's not X it's Y" or "not just X but Y". Just say what it is.
No self-narration. Delete "here's the thing", "the key takeaway is", "what's interesting is", "this highlights", "this underscores".
No significance inflation. Delete "marking a pivotal moment", "a testament to", "setting the stage for", "speaks to a broader".
No -ing phrase padding. Cut anything after the comma that starts with "highlighting", "underscoring", "showcasing", "paving the way".
No AI adjectives: pivotal, notable, robust, seamless, transformative, innovative, vibrant, groundbreaking, crucial, significant, comprehensive, dynamic, multifaceted.
No AI verbs: leverage, foster, elevate, empower, streamline, underscore, showcase, bolster, cultivate, harness, spearhead, garner, resonate.
Use "is" not "serves as", "stands as", "represents". Use "has" not "boasts" or "features".
Vary sentence length. Short ones mixed with longer ones. Not every sentence the same.
Aim for 150-180 words total.""",
        messages=[{"role": "user", "content": f"Chat log:\n\n{chat_log}"}],
    )
    return msg.content[0].text

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
    await update.message.reply_text("checking the last 12 hours... 🐈‍⬛")
    messages = get_messages_since(update.effective_chat.id, hours=12)
    await update.message.reply_text(build_summary(messages))

async def cmd_chatid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Chat ID: `{update.effective_chat.id}`", parse_mode="Markdown"
    )

async def job_summary(app):
    log.info("Posting 12h summary")
    messages = get_messages_since(TARGET_CHAT_ID, hours=12)
    await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=build_summary(messages))

async def job_post(app):
    log.info("Posting rotating message")
    await app.bot.send_message(chat_id=TARGET_CHAT_ID, text=next_post())

def main():
    init_db()
    threading.Thread(target=run_ping_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("chatid", cmd_chatid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_summary, "cron", hour="8,20", minute=0, args=[app])
    scheduler.add_job(job_post, "cron", hour="9,15,21,3", minute=0, args=[app])
    scheduler.start()

    log.info("Bot running")
    app.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()
