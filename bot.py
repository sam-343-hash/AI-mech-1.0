"""Telegram front-end for the study bot (standard library only).

Usage:
    export TELEGRAM_BOT_TOKEN=123456:ABC...
    python bot.py            # run the Telegram bot
    python bot.py --cli      # chat in the terminal, no token needed
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

from study_core import StudyBot


class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"

    def call(self, method, **params):
        data = urllib.parse.urlencode(params).encode()
        with urllib.request.urlopen(self.base + method, data, timeout=70) as r:
            return json.load(r)

    def send(self, chat_id, text):
        for i in range(0, len(text), 4000):  # Telegram message limit is 4096
            self.call("sendMessage", chat_id=chat_id, text=text[i : i + 4000])


def run_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("Set TELEGRAM_BOT_TOKEN first (get one from @BotFather).")
    tg = Telegram(token)
    bot = StudyBot(notify=tg.send)
    offset = 0
    print("Study bot running. Press Ctrl+C to stop.")
    while True:
        try:
            updates = tg.call("getUpdates", offset=offset, timeout=50)["result"]
        except Exception as e:  # network hiccup: wait and retry
            print("poll error:", e)
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            if "text" in msg:
                reply = bot.handle(msg["chat"]["id"], msg["text"])
                if reply:
                    try:
                        tg.send(msg["chat"]["id"], reply)
                    except Exception as e:
                        print("send error:", e)


def run_cli():
    bot = StudyBot(notify=lambda cid, text: print(f"\n[bot] {text}\n> ", end=""))
    print("Study bot (terminal mode). Type /help. Ctrl+C to quit.")
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        print(bot.handle(1, line))


if __name__ == "__main__":
    run_cli() if "--cli" in sys.argv else run_telegram()
