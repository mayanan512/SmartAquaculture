# -*- coding: utf-8 -*-
"""预警规则、告警记录与处理历史数据访问层。"""

from typing import Any, Dict, List, Optional
from database.connection import db_transaction
from repositories.base_repo import query_all, query_one, execute_write


class AlertRepository:
    @staticmethod
    def list_rules(only_enabled: bool = False) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM alert_rules"
        if only_enabled:
            sql += " WHERE is_enabled = 1"
        sql += " ORDER BY rule_id"
        return query_all(sql)

    @staticmethod
    def update_rule_threshold(rule_id: int, threshold_value: float, is_enabled: int = 1) -> None:
        execute_write(
            "UPDATE alert_rules SET threshold_value = ?, is_enabled = ? WHERE rule_id = ?",
            (threshold_value, is_enabled, rule_id),
        )

    @staticmethod
    def find_active_duplicate(pond_id: int, rule_id: int) -> Optional[Dict[str, Any]]:
        return query_one(
            """SELECT * FROM alert_records
               WHERE pond_id = ? AND rule_id = ? AND status IN ('NEW', 'ACKNOWLEDGED')
               ORDER BY alert_id DESC LIMIT 1""",
            (pond_id, rule_id),
        )

    @staticmethod
    def create_alert_with_log(
        alert_code: str,
        pond_id: Optional[int],
        equipment_id: Optional[int],
        rule_id: Optional[int],
        alert_type: str,
        metric_name: str,
        metric_value: Optional[float],
        unit: str,
        threshold_value: Optional[float],
        severity: str,
        triggered_at: str,
        source_type: str = "SIMULATED",
    ) -> int:
        with db_transaction() as conn:
            cur = conn.execute(
                """INSERT INTO alert_records
                (alert_code, pond_id, equipment_id, rule_id, alert_type, metric_name, metric_value, unit,
                 threshold_value, severity, status, triggered_at, source_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?)""",
                (alert_code, pond_id, equipment_id, rule_id, alert_type, metric_name, metric_value, unit, threshold_value, severity, triggered_at, source_type),
            )
            alert_id = cur.lastrowid
            conn.execute(
                """INSERT INTO alert_process_records
                (alert_id, action_type, from_status, to_status, handler_name, action_measure, processed_at)
                VALUES (?, 'CREATE', NULL, 'NEW', '系统预警服务', ?, ?)""",
                (alert_id, f"触发规则自动创建告警：{metric_name} 实测值 {metric_value}{unit}", triggered_at),
            )
            return int(alert_id)

    @staticmethod
    def list_alerts(status: Optional[str] = None, pond_id: Optional[int] = None, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT a.*, p.pond_name, p.pond_code, e.equipment_name
        FROM alert_records a
        LEFT JOIN fishponds p ON a.pond_id = p.pond_id
        LEFT JOIN equipment e ON a.equipment_id = e.equipment_id
        WHERE 1=1
        """
        params: list = []
        if status:
            sql += " AND a.status = ?"
            params.append(status)
        if pond_id:
            sql += " AND a.pond_id = ?"
            params.append(pond_id)
        if severity:
            sql += " AND a.severity = ?"
            params.append(severity)
        sql += " ORDER BY CASE a.status WHEN 'NEW' THEN 1 WHEN 'ACKNOWLEDGED' THEN 2 WHEN 'RESOLVED' THEN 3 ELSE 4 END, a.triggered_at DESC"
        return query_all(sql, tuple(params))

    @staticmethod
    def list_process_history(alert_id: int) -> List[Dict[str, Any]]:
        return query_all(
            "SELECT * FROM alert_process_records WHERE alert_id = ? ORDER BY process_id ASC",
            (alert_id,),
        )
