# 📚 Study Buddy Bot

A simple Telegram bot for students: flashcards with a spaced-repetition quiz, a to-do list, notes and a Pomodoro focus timer. Pure Python standard library, so there is nothing to install.

## Features
- **Flashcards & quiz** – `/addcard question | answer`, `/quiz`. Cards you get right appear less often (Leitner boxes); typos are forgiven.
- **To-do list** – `/todo`, `/todos`, `/done N`
- **Notes** – `/note`, `/notes`
- **Pomodoro** – `/pomodoro [minutes]` pings you when time is up
- **Stats** – `/stats`

## Setup
1. Open Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot` and copy the token.
2. Requires Python 3.8+.
3. Run:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-token-here"   # Windows: set TELEGRAM_BOT_TOKEN=your-token-here
   python bot.py
   ```
4. Open your bot in Telegram and send `/start`.

Try it without Telegram: `python bot.py --cli`

## Tests
```bash
python -m unittest
```

## Data
Each chat's data is stored as JSON in `data/` (change with `STUDY_BOT_DATA`). Never commit your bot token.

## Hosting
Keep `python bot.py` running on any always-on machine (a Raspberry Pi, a small VPS, or a free host that supports background workers).

## License
MIT
