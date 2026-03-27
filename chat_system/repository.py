"""数据访问层。"""
from __future__ import annotations

from typing import Any

from chat_system.db import get_db


class ChatRepository:
    """封装所有数据库 CRUD，隔离 SQL 与业务逻辑。"""

    def __init__(self) -> None:
        self.db = get_db()

    def create_user(self, username: str, password_hash: str, role: str = "user") -> int:
        conn = self.db.get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO users(username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        conn = self.db.get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_conversation(self, user_id: int, title: str, model_name: str = "deepseek") -> int:
        conn = self.db.get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO conversations(user_id, title, model_name) VALUES (?, ?, ?)",
                (user_id, title, model_name),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def list_conversations(self, user_id: int) -> list[dict[str, Any]]:
        conn = self.db.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_conversation(self, conversation_id: int) -> dict[str, Any] | None:
        conn = self.db.get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_conversation_by_user(self, conversation_id: int, user_id: int) -> dict[str, Any] | None:
        conn = self.db.get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user_id),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_conversation_title(self, conversation_id: int, title: str) -> None:
        conn = self.db.get_conn()
        try:
            conn.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, conversation_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_conversation(self, conversation_id: int) -> None:
        conn = self.db.get_conn()
        try:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
        finally:
            conn.close()

    def touch_conversation(self, conversation_id: int) -> None:
        conn = self.db.get_conn()
        try:
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def add_message(self, conversation_id: int, role: str, content: str) -> int:
        conn = self.db.get_conn()
        try:
            cur = conn.execute(
                "INSERT INTO messages(conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,),
            )
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()

    def list_messages(self, conversation_id: int) -> list[dict[str, Any]]:
        conn = self.db.get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
                (conversation_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_message(self, message_id: int) -> dict[str, Any] | None:
        conn = self.db.get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM messages WHERE id = ?",
                (message_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_message(self, message_id: int, content: str) -> None:
        conn = self.db.get_conn()
        try:
            conn.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                (content, message_id),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_message(self, message_id: int) -> None:
        conn = self.db.get_conn()
        try:
            conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
            conn.commit()
        finally:
            conn.close()
    