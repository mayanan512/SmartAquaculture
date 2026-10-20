# -*- coding: utf-8 -*-
"""通用数据库查询辅助基类。"""

from typing import Any, Dict, List, Optional
import pandas as pd
from database.connection import get_connection, db_transaction


def query_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def query_df(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def execute_write(sql: str, params: tuple = ()) -> int:
    with db_transaction() as conn:
        cur = conn.execute(sql, params)
        return cur.lastrowid or 0
