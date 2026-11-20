"""Core logic for the study bot. No network code here, so it is easy to test."""
import difflib
import json
import os
import random
import threading
from pathlib import Path

DATA_DIR = Path(os.environ.get("STUDY_BOT_DATA", "data"))

HELP = """📚 Study Buddy commands

Flashcards
/addcard question | answer  – add a flashcard
/cards – list your cards
/delcard N – delete card number N
/quiz – get a question (just reply with your answer)
/skip – skip the current question

To-do
/todo task – add a task
/todos – list tasks
/done N – mark task N done

Notes
/note text – save a note
/notes – show notes

Focus
/pomodoro [minutes] – focus timer (default 25)
/stats – your quiz stats
/help – this message"""


class Store:
    """Tiny JSON-file storage, one file per chat."""

    def __init__(self, directory=DATA_DIR):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def _path(self, chat_id):
        return self.dir / f"{int(chat_id)}.json"

    def load(self, chat_id):
        p = self._path(chat_id)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"cards": [], "todos": [], "notes": [], "right": 0, "wrong": 0}

    def save(self, chat_id, data):
        with self.lock:
            self._path(chat_id).write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )


class StudyBot:
    def __init__(self, store=None, notify=None):
        self.store = store or Store()
        self.notify = notify or (lambda chat_id, text: None)
        self.pending = {}  # chat_id -> card index currently being quizzed

    # ---- entry point -------------------------------------------------
    def handle(self, chat_id, text):
        text = (text or "").strip()
        if not text:
            return ""
        if not text.startswith("/"):
            if chat_id in self.pending:
                return self._check_answer(chat_id, text)
            return "Send /help to see what I can do."
        cmd, _, arg = text.partition(" ")
        cmd = cmd.lower().split("@")[0]
        arg = arg.strip()
        fn = {
            "/start": lambda: "Hi! I'm your study buddy.\n\n" + HELP,
            "/help": lambda: HELP,
            "/addcard": lambda: self._addcard(chat_id, arg),
            "/cards": lambda: self._cards(chat_id),
            "/delcard": lambda: self._delcard(chat_id, arg),
            "/quiz": lambda: self._quiz(chat_id),
            "/skip": lambda: self._skip(chat_id),
            "/todo": lambda: self._todo(chat_id, arg),
            "/todos": lambda: self._todos(chat_id),
            "/done": lambda: self._done(chat_id, arg),
            "/note": lambda: self._note(chat_id, arg),
            "/notes": lambda: self._notes(chat_id),
            "/pomodoro": lambda: self._pomodoro(chat_id, arg),
            "/stats": lambda: self._stats(chat_id),
        }.get(cmd)
        return fn() if fn else "Unknown command. Try /help."

    # ---- flashcards --------------------------------------------------
    def _addcard(self, chat_id, arg):
        if "|" not in arg:
            return "Usage: /addcard question | answer"
        q, a = (s.strip() for s in arg.split("|", 1))
        if not q or not a:
            return "Usage: /addcard question | answer"
        d = self.store.load(chat_id)
        d["cards"].append({"q": q, "a": a, "box": 1})
        self.store.save(chat_id, d)
        return f"✅ Card #{len(d['cards'])} added."

    def _cards(self, chat_id):
        cards = self.store.load(chat_id)["cards"]
        if not cards:
            return "No cards yet. Add one with /addcard question | answer"
        return "\n".join(f"{i}. {c['q']}" for i, c in enumerate(cards, 1))

    def _delcard(self, chat_id, arg):
        d = self.store.load(chat_id)
        i = self._index(arg, len(d["cards"]))
        if i is None:
            return "Usage: /delcard N (see /cards)"
        removed = d["cards"].pop(i)
        self.store.save(chat_id, d)
        self.pending.pop(chat_id, None)
        return f"🗑 Deleted: {removed['q']}"

    def _quiz(self, chat_id):
        cards = self.store.load(chat_id)["cards"]
        if not cards:
            return "Add some cards first: /addcard question | answer"
        # Leitner-style: cards in lower boxes come up more often.
        lowest = min(c["box"] for c in cards)
        pool = [i for i, c in enumerate(cards) if c["box"] == lowest]
        idx = random.choice(pool)
        self.pending[chat_id] = idx
        return f"❓ {cards[idx]['q']}\n\n(reply with your answer, or /skip)"

    def _skip(self, chat_id):
        idx = self.pending.pop(chat_id, None)
        if idx is None:
            return "No active question. Use /quiz."
        cards = self.store.load(chat_id)["cards"]
        return f"Answer: {cards[idx]['a']}" if idx < len(cards) else "Skipped."

    def _check_answer(self, chat_id, text):
        idx = self.pending.pop(chat_id)
        d = self.store.load(chat_id)
        if idx >= len(d["cards"]):
            return "That card no longer exists. Try /quiz."
        card = d["cards"][idx]
        ratio = difflib.SequenceMatcher(
            None, text.lower().strip(), card["a"].lower().strip()
        ).ratio()
        if ratio >= 0.8:
            card["box"] = min(card["box"] + 1, 5)
            d["right"] += 1
            reply = "✅ Correct!"
        else:
            card["box"] = 1
            d["wrong"] += 1
            reply = f"❌ Not quite. Answer: {card['a']}"
        self.store.save(chat_id, d)
        return reply + "\n\nNext one? /quiz"

    def _stats(self, chat_id):
        d = self.store.load(chat_id)
        total = d["right"] + d["wrong"]
        pct = round(100 * d["right"] / total) if total else 0
        mastered = sum(1 for c in d["cards"] if c["box"] >= 4)
        return (
            f"📊 Answered: {total} ({d['right']} right, {pct}%)\n"
            f"Cards: {len(d['cards'])} ({mastered} well known)"
        )

    # ---- todos -------------------------------------------------------
    def _todo(self, chat_id, arg):
        if not arg:
            return "Usage: /todo task"
        d = self.store.load(chat_id)
        d["todos"].append({"text": arg, "done": False})
        self.store.save(chat_id, d)
        return f"📝 Added task #{len(d['todos'])}."

    def _todos(self, chat_id):
        todos = self.store.load(chat_id)["todos"]
        if not todos:
            return "No tasks. Add one with /todo task"
        return "\n".join(
            f"{i}. {'✅' if t['done'] else '⬜'} {t['text']}"
            for i, t in enumerate(todos, 1)
        )

    def _done(self, chat_id, arg):
        d = self.store.load(chat_id)
        i = self._index(arg, len(d["todos"]))
        if i is None:
            return "Usage: /done N (see /todos)"
        d["todos"][i]["done"] = True
        self.store.save(chat_id, d)
        return "🎉 Nice work!"

    # ---- notes -------------------------------------------------------
    def _note(self, chat_id, arg):
        if not arg:
            return "Usage: /note text"
        d = self.store.load(chat_id)
        d["notes"].append(arg)
        self.store.save(chat_id, d)
        return "🗒 Note saved."

    def _notes(self, chat_id):
        notes = self.store.load(chat_id)["notes"]
        if not notes:
            return "No notes yet. Add one with /note text"
        return "\n".join(f"{i}. {n}" for i, n in enumerate(notes, 1))

    # ---- pomodoro ----------------------------------------------------
    def _pomodoro(self, chat_id, arg):
        minutes = 25
        if arg:
            if not arg.isdigit() or not 1 <= int(arg) <= 180:
                return "Usage: /pomodoro [minutes 1-180]"
            minutes = int(arg)
        t = threading.Timer(
            minutes * 60,
            self.notify,
            args=(chat_id, f"⏰ {minutes} minutes done! Take a 5 minute break."),
        )
        t.daemon = True
        t.start()
        return f"🍅 Focus for {minutes} minutes. I'll ping you when it's over."

    @staticmethod
    def _index(arg, length):
        if not arg.isdigit():
            return None
        i = int(arg) - 1
        return i if 0 <= i < length else None
