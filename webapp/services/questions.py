"""Keep the existing unique-question log without coupling it to routes."""

import json
from pathlib import Path
QUESTIONS_FILE = Path(__file__).resolve().parents[2] / "questions.json"


def record_question(question):
    try:
        questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf8")) if QUESTIONS_FILE.exists() else []
        if not any(item.get("question") == question for item in questions):
            questions.append({"question": question})
            QUESTIONS_FILE.write_text(json.dumps(questions, indent=4), encoding="utf8")
    except (OSError, json.JSONDecodeError):
        pass
