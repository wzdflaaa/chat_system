"""Flask Web 层。"""
from __future__ import annotations

import json
from functools import wraps

from flask import Flask, Response, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from chat_system.repository import ChatRepository
from chat_system.service import ChatFacade


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key-please-change"

    repo = ChatRepository()
    facade = ChatFacade()

    @app.get("/")
    def home():
        if "user_id" in session:
            return redirect(url_for("chat_page"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("register.html")

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template("register.html", error="用户名和密码不能为空")
        if repo.get_user_by_username(username):
            return render_template("register.html", error="用户名已存在")

        user_id = repo.create_user(username, generate_password_hash(password), role="user")
        session["user_id"] = user_id
        session["username"] = username
        session["role"] = "user"
        return redirect(url_for("chat_page"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html")

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = repo.get_user_by_username(username)

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="用户名或密码错误")

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]
        return redirect(url_for("chat_page"))

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/chat")
    @login_required
    def chat_page():
        user_id = int(session["user_id"])
        conversations = facade.list_conversations(user_id)

        current_id = request.args.get("conversation_id", type=int)
        if current_id:
            current_conv = repo.get_conversation_by_user(current_id, user_id)
            if not current_conv:
                return redirect(url_for("chat_page"))

        if not current_id and conversations:
            current_id = conversations[0]["id"]

        messages = facade.list_messages(current_id) if current_id else []

        return render_template(
            "chat.html",
            username=session.get("username"),
            role=session.get("role"),
            conversations=conversations,
            current_id=current_id,
            messages=messages,
        )

    @app.post("/api/conversations")
    @login_required
    def create_conversation_api():
        payload = request.get_json(silent=True) or {}
        title = (payload.get("title") or "新会话").strip()
        model_name = (payload.get("model_name") or "deepseek").strip()
        conv_id = facade.create_conversation(int(session["user_id"]), title, model_name=model_name)
        return jsonify({"conversation_id": conv_id})

    @app.delete("/api/conversations/<int:conversation_id>")
    @login_required
    def delete_conversation_api(conversation_id: int):
        user_id = int(session["user_id"])
        conv = repo.get_conversation_by_user(conversation_id, user_id)
        if not conv:
            return jsonify({"error": "会话不存在或无权限"}), 404

        facade.delete_conversation(conversation_id)
        return jsonify({"ok": True})

    @app.post("/api/conversations/<int:conversation_id>/messages")
    @login_required
    def send_message_api(conversation_id: int):
        user_id = int(session["user_id"])
        conv = repo.get_conversation_by_user(conversation_id, user_id)
        if not conv:
            return jsonify({"error": "会话不存在或无权限"}), 404

        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        if not content:
            return jsonify({"error": "消息不能为空"}), 400

        facade.send_user_message(conversation_id, content)
        facade.update_conversation_title_if_needed(conversation_id, content)

        def event_stream():
            try:
                _, chunks = facade.stream_assistant_reply(conversation_id, content)
                for ck in chunks:
                    yield f"data: {json.dumps({'delta': ck}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

        return Response(event_stream(), mimetype="text/event-stream")

    @app.patch("/api/messages/<int:message_id>")
    @login_required
    def edit_message_api(message_id: int):
        if session.get("role") not in ("user", "admin"):
            return jsonify({"error": "无权限"}), 403

        payload = request.get_json(silent=True) or {}
        content = (payload.get("content") or "").strip()
        if not content:
            return jsonify({"error": "内容不能为空"}), 400

        msg = repo.get_message(message_id)
        if not msg:
            return jsonify({"error": "消息不存在"}), 404

        conv = repo.get_conversation_by_user(msg["conversation_id"], int(session["user_id"]))
        if not conv:
            return jsonify({"error": "无权限"}), 403

        facade.update_message(message_id, content)
        return jsonify({"ok": True})

    @app.delete("/api/messages/<int:message_id>")
    @login_required
    def delete_message_api(message_id: int):
        if session.get("role") not in ("user", "admin"):
            return jsonify({"error": "无权限"}), 403

        msg = repo.get_message(message_id)
        if not msg:
            return jsonify({"error": "消息不存在"}), 404

        conv = repo.get_conversation_by_user(msg["conversation_id"], int(session["user_id"]))
        if not conv:
            return jsonify({"error": "无权限"}), 403

        facade.delete_message(message_id)
        return jsonify({"ok": True})

    return app
