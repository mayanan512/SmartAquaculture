# -*- coding: utf-8 -*-
"""设备档案与状态历史数据访问层。"""

from typing import Any, Dict, List, Optional
from repositories.base_repo import query_all, execute_write


class EquipmentRepository:
    @staticmethod
    def list_equipment(pond_id: Optional[int] = None, status: Optional[str] = None, equipment_type: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT e.*, p.pond_name, p.pond_code
        FROM equipment e
        LEFT JOIN fishponds p ON e.pond_id = p.pond_id
        WHERE 1=1
        """
        params: list = []
        if pond_id:
            sql += " AND e.pond_id = ?"
            params.append(pond_id)
        if status:
            sql += " AND e.status = ?"
            params.append(status)
        if equipment_type:
            sql += " AND e.equipment_type = ?"
            params.append(equipment_type)
        # 优先将故障(FAULT)与离线(OFFLINE)设备排在前面，确保大屏与设备台账一眼看到异常设备
        sql += " ORDER BY CASE e.status WHEN 'FAULT' THEN 1 WHEN 'OFFLINE' THEN 2 ELSE 3 END, e.equipment_id"
        return query_all(sql, tuple(params))

    @staticmethod
    def update_equipment_status(equipment_id: int, status: str, reported_at: str, source_type: str = "SIMULATED", remark: str = "") -> None:
        execute_write(
            "UPDATE equipment SET status = ?, last_reported_at = ?, updated_at = ? WHERE equipment_id = ?",
            (status, reported_at, reported_at, equipment_id),
        )
        execute_write(
            "INSERT INTO equipment_status_records (equipment_id, status, source_type, reported_at, remark) VALUES (?, ?, ?, ?, ?)",
            (equipment_id, status, source_type, reported_at, remark),
        )

    @staticmethod
    def create_equipment(
        equipment_code: str,
        equipment_name: str,
        equipment_type: str,
        pond_id: Optional[int],
        install_location: str,
        status: str = "ONLINE",
        source_type: str = "MANUAL",
        reported_at: str = "",
    ) -> int:
        eq_id = execute_write(
            """INSERT INTO equipment
               (equipment_code, equipment_name, equipment_type, pond_id, install_location, status, source_type, last_reported_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (equipment_code, equipment_name, equipment_type, pond_id, install_location, status, source_type, reported_at),
        )
        execute_write(
            "INSERT INTO equipment_status_records (equipment_id, status, source_type, reported_at, remark) VALUES (?, ?, ?, ?, ?)",
            (eq_id, status, source_type, reported_at, "新建设备建档入库"),
        )
        return eq_id

    @staticmethod
    def list_status_records(limit: int = 30) -> List[Dict[str, Any]]:
        sql = """
        SELECT r.*, e.equipment_code, e.equipment_name, e.equipment_type, p.pond_code, p.pond_name
        FROM equipment_status_records r
        JOIN equipment e ON r.equipment_id = e.equipment_id
        LEFT JOIN fishponds p ON e.pond_id = p.pond_id
        ORDER BY r.reported_at DESC, r.status_record_id DESC
        LIMIT ?
        """
        return query_all(sql, (limit,))
