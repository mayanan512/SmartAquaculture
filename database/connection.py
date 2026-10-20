# -*- coding: utf-8 -*-
"""
SQLite 数据库连接与事务上下文管理模块。
所有 Repository 统一通过此模块获取连接，禁止各模块硬编码数据库路径。
支持默认本地 data/smart_aquaculture.db 存储，并在云端容器只读挂载盘或受限文件锁环境下自动回退至可写临时目录。
"""

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from config.settings import DB_PATH, DATA_DIR

_ACTIVE_DB_PATH: Path | None = None


def resolve_db_path() -> Path:
    """解析当前可用的 SQLite 数据库文件路径。"""
    global _ACTIVE_DB_PATH
    env_path = os.environ.get("SMART_AQUACULTURE_DB_PATH")
    if env_path:
        p = Path(env_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    if _ACTIVE_DB_PATH is not None:
        return _ACTIVE_DB_PATH

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA schema_version;")
        conn.execute("CREATE TABLE IF NOT EXISTS _lock_probe (id INTEGER);")
        conn.execute("DROP TABLE IF EXISTS _lock_probe;")
        conn.commit()
        conn.close()
        _ACTIVE_DB_PATH = DB_PATH
    except (sqlite3.Error, OSError, PermissionError):
        fallback_dir = Path(tempfile.gettempdir()) / "SmartAquacultureData"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        _ACTIVE_DB_PATH = fallback_dir / "smart_aquaculture.db"
    return _ACTIVE_DB_PATH


def get_connection() -> sqlite3.Connection:
    """获取开启外键约束与字典行工厂的 SQLite 连接。"""
    db_file = resolve_db_path()
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_transaction() -> Iterator[sqlite3.Connection]:
    """数据库事务上下文管理器，自动提交或回滚并关闭连接。"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
