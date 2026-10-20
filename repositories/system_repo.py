# -*- coding: utf-8 -*-
"""系统设置与操作日志数据访问层。"""

from typing import Any, Dict, List
from repositories.base_repo import query_all, execute_write


class SystemRepository:
    @staticmethod
    def get_settings_dict() -> Dict[str, str]:
        rows = query_all("SELECT setting_key, setting_value FROM system_settings")
        return {r["setting_key"]: r["setting_value"] for r in rows}

    @staticmethod
    def list_settings() -> List[Dict[str, Any]]:
        return query_all("SELECT * FROM system_settings ORDER BY setting_id")

    @staticmethod
    def update_setting(setting_key: str, setting_value: str) -> None:
        execute_write(
            "UPDATE system_settings SET setting_value = ?, updated_at = datetime('now', 'localtime') WHERE setting_key = ?",
            (setting_value, setting_key),
        )

    @staticmethod
    def log_operation(module_name: str, action_type: str, target_ref: str, detail: str, operator_name: str = "系统管理员") -> None:
        execute_write(
            "INSERT INTO operation_logs (module_name, action_type, target_ref, detail, operator_name) VALUES (?, ?, ?, ?, ?)",
            (module_name, action_type, target_ref, detail, operator_name),
        )

    @staticmethod
    def list_logs(limit: int = 50) -> List[Dict[str, Any]]:
        return query_all("SELECT * FROM operation_logs ORDER BY log_id DESC LIMIT ?", (limit,))
