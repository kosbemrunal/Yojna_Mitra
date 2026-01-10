import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from google import genai 
from groq import Groq 

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Configure Gemini API
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------------------
# Initialize SQLite Database
# ---------------------------

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT
                )""")

    c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    sender TEXT,
                    message TEXT
                )""")

    conn.commit()
    conn.close()

init_db()

def clean_format(text):
    text = text.replace("•", "• ")
    text = text.replace("* ", "")
    text = text.replace("**", "")
    text = text.replace(" -", "\n- ")
    text = text.replace(". ", ".\n")
    text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
    return text.strip()

# ---------------------------
# AI Reply Function
# ---------------------------
def ai_reply(user_message):
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Yojna Mitra, an expert assistant for Indian Government schemes. "
                        "Always reply in the same language as the user. "
                        "Provide clear, structured answers."
                    )
                },
                {"role": "user", "content": user_message}
            ],
            max_tokens=1500,
            temperature=0.3
        )

        # FIX: Access content correctly
        ai_text = completion.choices[0].message.content

        return ai_text

    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

# ---------------------------
# ROUTES
# ---------------------------

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")
    return redirect("/chat")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_pw = generate_password_hash(password)

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
            conn.commit()
        except Exception:
            conn.close()
            return "⚠ Username already exists!"

        conn.close()
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        c = conn.cursor()

        c.execute("SELECT id, password FROM users WHERE username=?", (username,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            return redirect("/chat")
        else:
            return "⚠ Invalid username or password"

    return render_template("login.html")


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    if request.method == "POST":
        user_message = request.form["message"]

        # Save user message
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
                  (user_id, "user", user_message))
        conn.commit()
        conn.close()

        # Generate bot reply
        bot_message = ai_reply(user_message)

        # Save bot reply
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (user_id, sender, message) VALUES (?, ?, ?)",
                  (user_id, "bot", bot_message))
        conn.commit()
        conn.close()

        return redirect("/chat")

    # Load chat history
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT sender, message FROM chat_history WHERE user_id=?", (user_id,))
    history = [{"sender": row[0], "text": row[1]} for row in c.fetchall()]
    conn.close()

    return render_template("index.html", chat_history=history)


@app.route("/new_chat")
def new_chat():
    """Clears the chat history for the logged-in user."""
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("DELETE FROM chat_history WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

    return redirect("/chat")

@app.route("/set_language", methods=["POST"])
def set_language():
    selected_language = request.form.get("language")
    session["language"] = selected_language
    return redirect("/chat")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
