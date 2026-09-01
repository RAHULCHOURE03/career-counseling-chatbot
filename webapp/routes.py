"""Authentication, chat, and history HTTP routes."""

from datetime import date, datetime, timedelta, timezone
from functools import wraps
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for
from .extensions import bcrypt, db
from .models import ChatHistory, User
from .services.questions import record_question
from .services import knowledge_base

web = Blueprint("web", __name__)


def current_user():
    return db.session.get(User, session["user_id"]) if session.get("user_id") else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return (jsonify({"error": "Authentication required"}), 401) if request.path.startswith("/api/") else redirect(url_for("web.login"))
        return view(*args, **kwargs)
    return wrapped


@web.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name, email, password = request.form.get("name", "").strip(), request.form.get("email", "").strip().lower(), request.form.get("password", "")
        if not name or not email or not password: return render_template("signup.html", message="All fields are required"), 400
        if User.query.filter_by(email=email).first(): return render_template("signup.html", message="User already exists"), 409
        db.session.add(User(name=name, email=email, password=bcrypt.generate_password_hash(password).decode("utf-8")))
        db.session.commit()
        return redirect(url_for("web.login"))
    return render_template("signup.html")


@web.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get("email", "").strip().lower()).first()
        if user and bcrypt.check_password_hash(user.password, request.form.get("password", "")):
            session.clear(); session["user_id"] = user.id
            return redirect(url_for("web.index"))
        return render_template("login.html", message="Invalid credentials"), 401
    return render_template("login.html")


@web.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@web.route("/")
@login_required
def index(): return render_template("index.html")


@web.get("/api/me")
@login_required
def me():
    user = current_user()
    return jsonify({"name": user.name, "email": user.email})


@web.post("/api/chat")
@login_required
def chat():
    question = (request.get_json(silent=True) or {}).get("message")
    if not isinstance(question, str) or not question.strip(): return jsonify({"error": "A non-empty message is required"}), 400
    question = question.strip()
    if len(question) > 2000: return jsonify({"error": "Message must be at most 2000 characters"}), 400
    # Use official-source excerpts when the local corpus has a confident match.
    # General questions continue to use the existing TensorFlow chatbot.
    answer = knowledge_base.answer(question)
    if answer is None:
        from .services.chatbot_engine import reply
        answer = reply(question)
    db.session.add(ChatHistory(user_id=current_user().id, question=question, answer=answer))
    db.session.execute(db.delete(ChatHistory).where(ChatHistory.created_at < datetime.now(timezone.utc) - timedelta(days=7)))
    db.session.commit()
    record_question(question)
    return jsonify({"answer": answer})


@web.get("/api/history")
@login_required
def history():
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    entries = ChatHistory.query.filter_by(user_id=current_user().id).filter(ChatHistory.created_at >= cutoff).all()
    return jsonify({"dates": sorted({entry.created_at.date().isoformat() for entry in entries}, reverse=True)})


@web.get("/api/history/<history_date>")
@login_required
def history_by_date(history_date):
    try: selected = date.fromisoformat(history_date)
    except ValueError: return jsonify({"error": "Date must use YYYY-MM-DD"}), 400
    entries = ChatHistory.query.filter_by(user_id=current_user().id).order_by(ChatHistory.created_at.asc()).all()
    return jsonify([{"question": entry.question, "answer": entry.answer} for entry in entries if entry.created_at.date() == selected])
