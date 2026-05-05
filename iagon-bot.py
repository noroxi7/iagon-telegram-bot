#!/usr/bin/env python3

import subprocess
import logging
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN   = "YOUR_BOT_TOKEN"
ALLOWED_ID  = 123456789  # Your Telegram chat ID
LOG_PATH    = "/home/noroxi/iagon/iagon-checker/logs"
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)

import re
def strip_ansi(text: str) -> str:
    return re.sub(r'\x1b\[[0-9;]*m', '', text)

# In-memory state: initialized to current log line count on startup
last_line_seen = 0

def is_allowed(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_ID

def run_command(cmd: list, input_text: str = None, timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return strip_ansi((result.stdout + result.stderr).strip())
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Error: {e}"

def get_today_log() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(LOG_PATH, f"iagon_{today}.log")

def read_log_lines() -> list:
    try:
        with open(get_today_log(), "r") as f:
            return f.readlines()
    except FileNotFoundError:
        return []

# ─── COMMANDS ─────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    output = run_command(["iagon-node", "service", "status"])
    await update.message.reply_text(f"📊 {output}")

async def cmd_start_node(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    output = run_command(["sudo", "iagon-node", "service", "start"], input_text="yes\n")
    await update.message.reply_text(f"▶️ {output}")

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    output = run_command(["sudo", "iagon-node", "service", "stop"], input_text="yes\n")
    await update.message.reply_text(f"⏹️ {output}")

async def cmd_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    output = run_command(["sudo", "iagon-node", "service", "restart"], input_text="yes\n")
    await update.message.reply_text(f"🔄 {output}")

async def cmd_benchmark(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    await update.message.reply_text("⏳ Running benchmark, this may take a minute...")
    try:
        result = subprocess.run(
            ["iagon-node", "benchmark"],
            capture_output=True,
            text=True,
            timeout=180
        )
        output = strip_ansi((result.stdout + result.stderr).strip())
    except subprocess.TimeoutExpired:
        output = "Benchmark timed out after 3 minutes."
    except Exception as e:
        output = f"Error: {e}"
    await update.message.reply_text(f"📈 Benchmark results:\n\n{output}")

async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    lines = read_log_lines()
    if not lines:
        await update.message.reply_text("No log file found for today.")
        return
    last = "".join(lines[-20:])
    await update.message.reply_text(f"📄 Last log entries, this is from iagon-checker\n\n For iagon-node logs check on your node terminal:\n\n<pre>{last}</pre>", parse_mode="HTML")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update): return
    text = (
        "🤖 *Iagon Node Bot*\n\n"
        "/status — Check service status\n"
        "/start\\_node — Start the service\n"
        "/stop — Stop the service\n"
        "/restart — Restart the service\n"
        "/benchmark — Run performance benchmark\n"
        "/logs — Show last 20 log lines\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── ALERT MONITOR ────────────────────────────────────────────────────────────

async def check_logs_for_alerts(context: ContextTypes.DEFAULT_TYPE):
    global last_line_seen

    lines = read_log_lines()
    new_lines = lines[last_line_seen:]

    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        lower = line.lower()
        if "stopped" in lower or "error" in lower or "permission denied" in lower:
            block = [line]
            j = i + 1
            while j < len(new_lines):
                if new_lines[j].startswith("["):
                    break
                block.append(new_lines[j])
                j += 1

            block_text = "".join(block).strip()

            if "stopped" in lower:
                if "service started successfully" in block_text.lower():
                    emoji = "⚠️"
                    header = "Service was stopped but restarted successfully"
                else:
                    emoji = "🚨"
                    header = "Service stopped — check required"
            else:
                emoji = "❌"
                header = "Error detected"

            msg = f"{emoji} <b>{header}</b>\n\n<pre>{block_text}</pre>"
            await context.bot.send_message(chat_id=ALLOWED_ID, text=msg, parse_mode="HTML")
            i = j
        else:
            i += 1

    last_line_seen = len(lines)

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    global last_line_seen

    # Initialize to current end of log so past entries are ignored on startup
    last_line_seen = len(read_log_lines())

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("status",     cmd_status))
    app.add_handler(CommandHandler("start_node", cmd_start_node))
    app.add_handler(CommandHandler("stop",       cmd_stop))
    app.add_handler(CommandHandler("restart",    cmd_restart))
    app.add_handler(CommandHandler("benchmark",  cmd_benchmark))
    app.add_handler(CommandHandler("logs",       cmd_logs))
    app.add_handler(CommandHandler("help",       cmd_help))

    app.job_queue.run_repeating(check_logs_for_alerts, interval=60, first=10)

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()