from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
from datetime import datetime
import os
import re
import json
import requests
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from groq import Groq

from db import get_db_connection

load_dotenv()
groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

app = Flask(__name__)
CORS(app)

AI_API_KEY = os.getenv("GROK_API_KEY", "").strip()
AI_API_URL = os.getenv(
    "GROK_API_URL",
    "https://api.x.ai/v1/chat/completions"
)
AI_MODEL = os.getenv("GROK_MODEL", "grok-3-mini")


def json_error(message, status=400):
    return jsonify({"success": False, "error": message}), status


def current_user():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id") or request.args.get("user_id")
    try:
        return int(user_id) if user_id else None
    except (TypeError, ValueError):
        return None


def get_admin_id():
    user_id = current_user()
    if not user_id:
        return None

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id FROM users WHERE user_id=%s AND role='admin' AND status='active'",
            (user_id,)
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None
    finally:
        cursor.close()
        conn.close()


def format_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y %I:%M %p")
    return str(value)


def fetch_one(query, params=()):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def fetch_all(query, params=()):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def run_ai(prompt, system_message):
    if not AI_API_KEY:
        return None

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    response = requests.post(
        AI_API_URL,
        headers={
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=45
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def local_moderation(title, content):
    text = f"{title} {content}".lower()

    rules = [
        (r"(buy now|limited offer|discount|promo|promotion|sale)", "Promotional content"),
        (r"(http://|https://|www\.)", "Spam link"),
        (r"\b(idiot|stupid|hate you|shut up)\b", "Inappropriate language"),
        (r"(free money|click here|earn \$\d+)", "Suspicious or spam content"),
    ]

    reasons = []
    score = 5.0

    for pattern, reason in rules:
        if re.search(pattern, text):
            reasons.append(reason)
            score += 25

    score = min(score, 99.0)

    if score >= 75:
        risk = "High"
    elif score >= 40:
        risk = "Medium"
    else:
        risk = "Low"

    reason = reasons[0] if reasons else "No major issue detected"
    return reason, risk, score

# -----------------------------
# AI moderation function
# -----------------------------
def ai_moderate(title, content):

    prompt = f"""
You are an AI content moderation system for an online community platform.

Analyze the following post.

Title:
{title}

Content:
{content}

Classify the post based on:
- spam
- promotional content
- inappropriate language
- harassment
- harmful content
- suspicious links
- other problematic content

Return ONLY valid JSON in this exact format:

{{
    "risk_level": "Low",
    "ai_score": 0,
    "flag_reason": "No problematic content detected"
}}

Rules:
- risk_level must be exactly Low, Medium, or High.
- ai_score must be a number from 0 to 100.
- flag_reason should briefly explain the main reason.
"""

    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a content moderation AI."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            response_format={
                "type": "json_object"
            }
        )

        result = response.choices[0].message.content
        result = json.loads(result)

        # Make sure the risk value exactly matches the MySQL ENUM
        risk_level = str(
            result.get("risk_level", "Medium")
        ).strip().lower()

        risk_map = {
            "low": "Low",
            "medium": "Medium",
            "high": "High"
        }

        if risk_level not in risk_map:
            raise Exception(
                f"Groq returned an invalid risk level: {risk_level}"
            )

        risk = risk_map[risk_level]

        score = float(result.get("ai_score", 50))
        score = min(max(score, 0), 100)

        reason = str(
            result.get(
                "flag_reason",
                "Manual review required"
            )
        ).strip()[:100]

        return reason, risk, score

    except Exception as error:
        print("Groq moderation error:", error)
        raise Exception(
            "Groq AI moderation failed. Please check the Groq API configuration."
        )

def fallback_assistant(message):
    text = message.lower()

    if any(word in text for word in ["hello", "hi", "hey"]):
        return "Hello! I am ModSense AI Assistant. How can I help you with the community platform?"

    if "community" in text or "join" in text:
        return "You can explore active communities from Explore Communities and join a community from its card."

    if "post" in text or "create" in text:
        return "Use Create Post to publish a title and message in a community you are part of."

    if "comment" in text or "reply" in text:
        return "Open a post to read comments and add a new comment or reply."

    if "like" in text:
        return "Open a post and use the Like button. You can like or unlike a post."

    if "moderation" in text or "moderate" in text:
        return "Content Moderation uses AI analysis to identify a reason, risk level and score for flagged posts."

    if "account" in text or "profile" in text or "login" in text:
        return "Your logged-in account is stored in browser localStorage for this project."

    return (
        "I can help with communities, posts, comments, likes, moderation, "
        "and general questions about using ModSense."
    )


def assistant_reply(message):
    if not AI_API_KEY:
        return fallback_assistant(message)

    try:
        result = run_ai(
            message,
            (
                "You are ModSense AI Assistant for an AI community platform. "
                "Answer clearly and briefly. Help with communities, posts, "
                "comments, likes, moderation and platform navigation. "
                "Do not invent actions that the platform cannot perform."
            )
        )
        return result or fallback_assistant(message)
    except Exception as exc:
        print("AI assistant fallback:", exc)
        return fallback_assistant(message)


# -----------------------------
# Health / frontend
# -----------------------------

@app.get("/api/health")
def health():
    return jsonify({
        "success": True,
        "message": "ModSense backend is running."
    })


@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def frontend(path):
    requested = FRONTEND_DIR / path
    if requested.is_file():
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


# -----------------------------
# Authentication
# -----------------------------

@app.post("/api/signup")
def signup():
    data = request.get_json(silent=True) or {}

    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not all([first_name, last_name, email, password]):
        return json_error("All fields are required.")

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return json_error("Enter a valid email address.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT user_id FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            return json_error("An account with this email already exists.", 409)

        cursor.execute(
            """
            INSERT INTO users
            (first_name, last_name, email, password_hash, role, status)
            VALUES (%s, %s, %s, %s, 'user', 'active')
            """,
            (first_name, last_name, email, password)
        )
        conn.commit()

        return jsonify({
            "success": True,
            "message": "Account created successfully.",
            "user": {
                "user_id": cursor.lastrowid,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": "user",
                "status": "active"
            }
        }), 201
    except Error as exc:
        conn.rollback()
        return json_error(str(exc), 500)
    finally:
        cursor.close()
        conn.close()


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return json_error("Email and password are required.")

    user = fetch_one(
        """
        SELECT user_id, first_name, last_name, email, role, status
        FROM users
        WHERE email=%s AND password_hash=%s
        """,
        (email, password)
    )

    if not user:
        return json_error("Invalid email or password.", 401)

    if user["status"] != "active":
        return json_error("This account is inactive.", 403)

    return jsonify({"success": True, "message": "Login successful.", "user": user})


# -----------------------------
# Posts
# -----------------------------

@app.get("/api/posts")
def get_posts():
    posts = fetch_all(
        """
        SELECT
            p.post_id,
            p.title,
            p.content,
            p.created_at,
            c.community_id,
            c.name AS community_name,
            CONCAT(u.first_name, ' ', u.last_name) AS author_name,
            COUNT(DISTINCT l.like_id) AS total_likes
        FROM posts p
        JOIN communities c ON c.community_id=p.community_id
        JOIN users u ON u.user_id=p.user_id
        LEFT JOIN post_likes l ON l.post_id=p.post_id
        LEFT JOIN content_moderations m
            ON m.post_id=p.post_id AND m.status='removed'
        WHERE c.status='active' AND m.moderation_id IS NULL
        GROUP BY p.post_id
        ORDER BY p.created_at DESC
        """
    )

    for post in posts:
        post["created_at"] = format_datetime(post["created_at"])

    return jsonify({"success": True, "posts": posts})


@app.post("/api/posts")
def create_post():

    data = request.json or {}

    title = data.get("title")
    community_name = data.get("community")
    content = data.get("content")
    user_id = data.get("user_id", 1)

    if not all([title, community_name, content]):

        return jsonify({
            "error": "Title, community, and content are required."
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute(
            "SELECT community_id FROM communities WHERE name = %s",
            (community_name,)
        )

        community = cursor.fetchone()

        if not community:

            return jsonify({
                "error": "Selected community does not exist."
            }), 404

        community_id = community["community_id"]

        # Create the post
        cursor.execute(
            """
            INSERT INTO posts
            (community_id, user_id, title, content)
            VALUES (%s, %s, %s, %s)
            """,
            (community_id, user_id, title, content)
        )

        post_id = cursor.lastrowid
        
        # Send post to Groq AI
        reason, risk, score = ai_moderate(title, content)
        # Save AI moderation result
        cursor.execute(
            """INSERT INTO content_moderations
            (post_id, flag_reason, risk_level, ai_score, status)
            VALUES (%s, %s, %s, %s, 'pending')""",
            (
                post_id,
                reason,
                risk,
                score
            )
        )
        moderation = {
            "flag_reason": reason,
            "risk_level": risk,
            "ai_score": score
        }

        conn.commit()

        return jsonify({
            "message": "Post created and sent for moderation.",
            "post_id": post_id,
            "moderation": moderation
        }), 201

    except Exception as e:

        conn.rollback()

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        cursor.close()
        conn.close()


@app.get("/api/posts/<int:post_id>")
def get_post(post_id):
    post = fetch_one(
        """
        SELECT
            p.post_id, p.title, p.content, p.created_at,
            c.community_id, c.name AS community_name,
            CONCAT(u.first_name, ' ', u.last_name) AS author_name,
            COUNT(DISTINCT l.like_id) AS total_likes
        FROM posts p
        JOIN communities c ON c.community_id=p.community_id
        JOIN users u ON u.user_id=p.user_id
        LEFT JOIN post_likes l ON l.post_id=p.post_id
        WHERE p.post_id=%s
        GROUP BY p.post_id
        """,
        (post_id,)
    )

    if not post:
        return json_error("Post not found.", 404)

    post["created_at"] = format_datetime(post["created_at"])
    return jsonify({"success": True, "post": post})


@app.post("/api/posts/<int:post_id>/like")
def toggle_like(post_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return json_error("user_id is required.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT like_id FROM post_likes WHERE post_id=%s AND user_id=%s",
            (post_id, user_id)
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                "DELETE FROM post_likes WHERE like_id=%s",
                (existing["like_id"],)
            )
            liked = False
        else:
            cursor.execute(
                "INSERT INTO post_likes (post_id, user_id) VALUES (%s, %s)",
                (post_id, user_id)
            )
            liked = True

        conn.commit()

        cursor.execute(
            "SELECT COUNT(*) AS total_likes FROM post_likes WHERE post_id=%s",
            (post_id,)
        )
        total = cursor.fetchone()["total_likes"]

        return jsonify({
            "success": True,
            "liked": liked,
            "total_likes": total
        })
    finally:
        cursor.close()
        conn.close()


# -----------------------------
# Comments
# -----------------------------

@app.get("/api/posts/<int:post_id>/comments")
def get_comments(post_id):
    comments = fetch_all(
        """
        SELECT
            c.comment_id,
            c.post_id,
            c.user_id,
            c.parent_comment_id,
            c.comment_text,
            c.created_at,
            CONCAT(u.first_name, ' ', u.last_name) AS author_name
        FROM post_comments c
        JOIN users u ON u.user_id=c.user_id
        WHERE c.post_id=%s
        ORDER BY c.created_at ASC
        """,
        (post_id,)
    )

    for comment in comments:
        comment["created_at"] = format_datetime(comment["created_at"])

    return jsonify({"success": True, "comments": comments})


@app.post("/api/posts/<int:post_id>/comments")
def add_comment(post_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    comment_text = data.get("comment_text", "").strip()
    parent_comment_id = data.get("parent_comment_id")

    if not user_id or not comment_text:
        return json_error("User and comment text are required.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            INSERT INTO post_comments
            (post_id, user_id, parent_comment_id, comment_text)
            VALUES (%s, %s, %s, %s)
            """,
            (post_id, user_id, parent_comment_id, comment_text)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Comment posted."}), 201
    finally:
        cursor.close()
        conn.close()


# -----------------------------
# Communities
# -----------------------------

@app.get("/api/communities")
def get_communities():
    communities = fetch_all(
        """
        SELECT
            c.community_id, c.name, c.description, c.about,
            c.status, c.created_at, c.category_id,
            cat.category_name,
            c.created_by,
            CONCAT(COALESCE(u.first_name,''), ' ', COALESCE(u.last_name,'')) AS creator_name
        FROM communities c
        LEFT JOIN categories cat ON cat.category_id=c.category_id
        LEFT JOIN users u ON u.user_id=c.created_by
        WHERE c.status='active'
        ORDER BY c.created_at DESC
        """
    )

    for community in communities:
        community["created_at"] = format_datetime(community["created_at"])

    return jsonify({"success": True, "communities": communities})


@app.get("/api/communities/<int:community_id>")
def get_community(community_id):
    community = fetch_one(
        """
        SELECT
            c.community_id, c.name, c.description, c.about,
            c.status, c.created_at, c.category_id,
            cat.category_name,
            c.created_by,
            CONCAT(COALESCE(u.first_name,''), ' ', COALESCE(u.last_name,'')) AS creator_name
        FROM communities c
        LEFT JOIN categories cat ON cat.category_id=c.category_id
        LEFT JOIN users u ON u.user_id=c.created_by
        WHERE c.community_id=%s AND c.status='active'
        """,
        (community_id,)
    )

    if not community:
        return json_error("Community not found.", 404)

    community["created_at"] = format_datetime(community["created_at"])
    return jsonify({"success": True, "community": community})


@app.post("/api/communities/<int:community_id>/join")
def join_community(community_id):
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    if not user_id:
        return json_error("user_id is required.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT community_id FROM communities WHERE community_id=%s AND status='active'",
            (community_id,)
        )
        if not cursor.fetchone():
            return json_error("Community not found.", 404)

        cursor.execute(
            """
            INSERT INTO community_members (community_id, user_id)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE joined_at=joined_at
            """,
            (community_id, user_id)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Joined community."})
    finally:
        cursor.close()
        conn.close()


@app.delete("/api/communities/<int:community_id>/leave")
def leave_community(community_id):
    user_id = request.args.get("user_id")

    if not user_id:
        data = request.get_json(silent=True) or {}
        user_id = data.get("user_id")

    if not user_id:
        return json_error("user_id is required.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM community_members WHERE community_id=%s AND user_id=%s",
            (community_id, user_id)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Left community."})
    finally:
        cursor.close()
        conn.close()


@app.get("/api/users/<int:user_id>/communities")
def user_communities(user_id):
    communities = fetch_all(
        """
        SELECT
            c.community_id, c.name, c.description, c.about,
            c.status, c.created_at, cat.category_name
        FROM community_members cm
        JOIN communities c ON c.community_id=cm.community_id
        LEFT JOIN categories cat ON cat.category_id=c.category_id
        WHERE cm.user_id=%s AND c.status='active'
        ORDER BY cm.joined_at DESC
        """,
        (user_id,)
    )

    for community in communities:
        community["created_at"] = format_datetime(community["created_at"])

    return jsonify({"success": True, "communities": communities})


# -----------------------------
# AI Assistant Chat
# -----------------------------

@app.route("/api/assistant/chat", methods=["POST"])
def assistant_chat():
    try:
        data = request.get_json() or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({
                "status": "error",
                "message": "Message cannot be empty."
            }), 400

        system_message = """
You are ModSense AI Assistant, a simple and friendly chatbot for the ModSense community platform.

Answer users naturally and conversationally.

Keep responses short and relevant. Usually answer in 1 to 3 sentences.

Do not use tables, headings, bullet points, numbered lists, emojis, or excessive formatting unless the user specifically asks for a detailed explanation or list.

Do not repeat the same generic response.

Answer the user's actual question directly.

You can help with communities, posts, comments, likes, user accounts, content moderation, AI moderation, and using the ModSense platform.

If the user asks something simple, give a simple answer.

For example:

User: "What can you tell me about?"
Assistant: "I can help you with things on ModSense like communities, posts, comments, and moderation. What would you like to know?"

User: "Tell me about communities."
Assistant: "Communities are spaces where users can discuss a particular topic or interest. You can join communities, view posts, and participate in discussions."

User: "What can I do here?"
Assistant: "You can explore communities, join them, create posts, comment on discussions, and interact with other users."

User: "How does moderation work?"
Assistant: "ModSense uses AI to check posts for things like spam, inappropriate content, or suspicious activity. Posts that need attention can then be reviewed by an admin."

Sound like a normal helpful assistant, not a formal AI-generated article.
"""

        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.5
        )

        reply = response.choices[0].message.content.strip()

        return jsonify({
            "status": "success",
            "reply": reply
        }), 200

    except Exception as e:
        print("AI Assistant Error:", e)

        return jsonify({
            "status": "error",
            "message": "AI Assistant is currently unavailable."
        }), 500


# -----------------------------
# Admin
# -----------------------------

@app.get("/api/admin/analytics")
def admin_analytics():
    admin_id = get_admin_id()
    if not admin_id:
        return json_error("Administrator access required.", 403)

    queries = {
        "total_users": "SELECT COUNT(*) AS value FROM users",
        "active_users": "SELECT COUNT(*) AS value FROM users WHERE status='active'",
        "inactive_users": "SELECT COUNT(*) AS value FROM users WHERE status='inactive'",
        "total_communities": "SELECT COUNT(*) AS value FROM communities",
        "active_communities": "SELECT COUNT(*) AS value FROM communities WHERE status='active'",
        "inactive_communities": "SELECT COUNT(*) AS value FROM communities WHERE status='inactive'",
        "total_posts": "SELECT COUNT(*) AS value FROM posts",
        "total_comments": "SELECT COUNT(*) AS value FROM post_comments",
        "total_likes": "SELECT COUNT(*) AS value FROM post_likes",
        "pending_moderation": "SELECT COUNT(*) AS value FROM content_moderations WHERE status='pending'"
    }

    analytics = {}
    for key, query in queries.items():
        row = fetch_one(query)
        analytics[key] = row["value"]

    return jsonify({"success": True, "analytics": analytics})


@app.get("/api/admin/users")
def admin_users():
    if not get_admin_id():
        return json_error("Administrator access required.", 403)

    users = fetch_all(
        """
        SELECT user_id, first_name, last_name, email, role, status, joined_at
        FROM users
        ORDER BY joined_at DESC
        """
    )
    for user in users:
        user["joined_at"] = format_datetime(user["joined_at"])

    return jsonify({"success": True, "users": users})


@app.put("/api/admin/users/<int:user_id>/status")
def admin_user_status(user_id):
    admin_id = get_admin_id()
    if not admin_id:
        return json_error("Administrator access required.", 403)

    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in ("active", "inactive"):
        return json_error("Status must be active or inactive.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET status=%s WHERE user_id=%s",
            (status, user_id)
        )
        conn.commit()
        return jsonify({"success": True, "message": "User status updated."})
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/communities")
def admin_communities():
    if not get_admin_id():
        return json_error("Administrator access required.", 403)

    communities = fetch_all(
        """
        SELECT
            c.community_id, c.name, c.description, c.status,
            cat.category_name,
            COUNT(DISTINCT cm.user_id) AS member_count,
            COUNT(DISTINCT p.post_id) AS post_count
        FROM communities c
        LEFT JOIN categories cat ON cat.category_id=c.category_id
        LEFT JOIN community_members cm ON cm.community_id=c.community_id
        LEFT JOIN posts p ON p.community_id=c.community_id
        GROUP BY c.community_id
        ORDER BY c.created_at DESC
        """
    )

    return jsonify({"success": True, "communities": communities})


@app.put("/api/admin/communities/<int:community_id>/status")
def admin_community_status(community_id):
    if not get_admin_id():
        return json_error("Administrator access required.", 403)

    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in ("active", "inactive"):
        return json_error("Status must be active or inactive.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE communities SET status=%s WHERE community_id=%s",
            (status, community_id)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Community status updated."})
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/moderation")
def admin_moderation():
    if not get_admin_id():
        return json_error("Administrator access required.", 403)

    rows = fetch_all(
        """
        SELECT
            m.moderation_id,
            m.post_id,
            m.flag_reason,
            m.risk_level,
            m.ai_score,
            m.status,
            m.created_at,
            p.title,
            p.content,
            c.name AS community_name,
            CONCAT(u.first_name, ' ', u.last_name) AS author_name
        FROM content_moderations m
        JOIN posts p ON p.post_id=m.post_id
        JOIN communities c ON c.community_id=p.community_id
        JOIN users u ON u.user_id=p.user_id
        ORDER BY
            CASE m.status WHEN 'pending' THEN 1 ELSE 2 END,
            m.ai_score DESC,
            m.created_at DESC
        """
    )

    for row in rows:
        row["created_at"] = format_datetime(row["created_at"])

    return jsonify({"success": True, "moderation": rows})


@app.post("/api/admin/moderation/analyze/<int:post_id>")
def admin_analyze_post(post_id):
    if not get_admin_id():
        return json_error("Administrator access required.", 403)

    post = fetch_one(
        "SELECT title, content FROM posts WHERE post_id=%s",
        (post_id,)
    )
    if not post:
        return json_error("Post not found.", 404)

    reason, risk, score = ai_moderate(post["title"], post["content"])

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO content_moderations
            (post_id, flag_reason, risk_level, ai_score, status)
            VALUES (%s, %s, %s, %s, 'pending')
            ON DUPLICATE KEY UPDATE
                flag_reason=VALUES(flag_reason),
                risk_level=VALUES(risk_level),
                ai_score=VALUES(ai_score)
            """,
            (post_id, reason, risk, score)
        )
        conn.commit()

        return jsonify({
            "success": True,
            "message": "AI moderation analysis completed.",
            "analysis": {
                "reason": reason,
                "risk_level": risk,
                "ai_score": score
            }
        })
    finally:
        cursor.close()
        conn.close()


@app.put("/api/admin/moderation/<int:moderation_id>")
def admin_moderation_action(moderation_id):
    admin_id = get_admin_id()
    if not admin_id:
        return json_error("Administrator access required.", 403)

    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if status not in ("pending", "approved", "removed"):
        return json_error("Invalid moderation status.")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE content_moderations
            SET status=%s, reviewed_by=%s, reviewed_at=NOW()
            WHERE moderation_id=%s
            """,
            (status, admin_id, moderation_id)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Moderation status updated."})
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
