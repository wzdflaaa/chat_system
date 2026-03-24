"""数据库模块：使用单例模式管理 SQLite 连接。"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import Lock


class DatabaseSingleton:
    """单例模式：确保全局只有一个数据库管理对象。

    好处：
    1. 避免重复创建连接配置与初始化逻辑。
    2. 集中管理建表、事务与连接参数，便于维护。
    """

    _instance: DatabaseSingleton | None = None
    _lock = Lock()

    def __new__(cls, db_path: str = 'chat_system.db') -> 'DatabaseSingleton':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str = 'chat_system.db') -> None:
        if getattr(self, '_initialized', False):
            return
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        self.init_db()

    def get_conn(self) -> sqlite3.Connection:
        """返回一个线程可用的 SQLite 连接。"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def init_db(self) -> None:
        """初始化所有业务表。"""
        conn = self.get_conn()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    model_name TEXT NOT NULL DEFAULT 'mock',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def get_db() -> DatabaseSingleton:
    """导出的工厂函数，便于调用方获取单例数据库对象。"""
    return DatabaseSingleton()
