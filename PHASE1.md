# Phase 1 local setup

1. Create and activate a virtual environment, then install the project requirements:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`, then set `DATABASE_URL` to your existing PostgreSQL connection string and choose a long random `SECRET_KEY`. Keep `.env` private; it is ignored by Git.

3. Ensure PostgreSQL is running, then start the application:

   ```powershell
   python app.py
   ```

   The first startup creates the `user` and `chat_history` tables. Existing `history.json` is left untouched as an archive; new history is stored in the database and linked to the signed-in user.

4. Run the automated Phase 1 checks:

   ```powershell
   pytest tests -q
   ```

## API behavior

`POST /api/chat` accepts `{ "message": "..." }` and requires a logged-in session. The server obtains the user ID from that session, invokes the existing TensorFlow intent chatbot, and records the resulting question/answer together. `GET /api/history` and `GET /api/history/YYYY-MM-DD` use the same session identity and cannot select another user's history.
