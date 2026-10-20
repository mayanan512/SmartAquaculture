# -*- coding: utf-8 -*-
"""水质监测记录数据访问层。"""

from typing import Any, Dict, List, Optional
import pandas as pd
from repositories.base_repo import query_all, query_one, query_df, execute_write


class WaterQualityRepository:
    @staticmethod
    def insert_record(
        pond_id: int,
        recorded_at: str,
        water_temp_c: Optional[float],
        dissolved_oxygen_mg_l: Optional[float],
        ph: Optional[float],
        ammonia_mg_l: Optional[float],
        source_type: str = "MANUAL",
        quality_status: str = "VALID",
        batch_id: Optional[int] = None,
    ) -> int:
        return execute_write(
            """INSERT INTO water_quality_records
            (pond_id, batch_id, recorded_at, water_temp_c, dissolved_oxygen_mg_l, ph, ammonia_mg_l, source_type, quality_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pond_id, batch_id, recorded_at, water_temp_c, dissolved_oxygen_mg_l, ph, ammonia_mg_l, source_type, quality_status),
        )

    @staticmethod
    def get_latest_by_pond(pond_id: int) -> Optional[Dict[str, Any]]:
        return query_one(
            """SELECT w.*, p.pond_name, p.pond_code
               FROM water_quality_records w
               JOIN fishponds p ON w.pond_id = p.pond_id
               WHERE w.pond_id = ?
               ORDER BY w.recorded_at DESC, w.record_id DESC LIMIT 1""",
            (pond_id,),
        )

    @staticmethod
    def get_latest_all_ponds() -> List[Dict[str, Any]]:
        sql = """
        SELECT w.*, p.pond_name, p.pond_code
        FROM water_quality_records w
        JOIN fishponds p ON w.pond_id = p.pond_id
        WHERE w.record_id IN (
            SELECT MAX(record_id) FROM water_quality_records GROUP BY pond_id
        )
        ORDER BY p.pond_id
        """
        return query_all(sql)

    @staticmethod
    def query_records_df(
        pond_id: Optional[int] = None,
        batch_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        source_type: Optional[str] = None,
    ) -> pd.DataFrame:
        sql = """
        SELECT w.record_id, w.pond_id, p.pond_code, p.pond_name, w.batch_id,
               w.recorded_at, w.water_temp_c, w.dissolved_oxygen_mg_l, w.ph, w.ammonia_mg_l,
               w.source_type, w.quality_status
        FROM water_quality_records w
        JOIN fishponds p ON w.pond_id = p.pond_id
        WHERE 1=1
        """
        params: list = []
        if pond_id:
            sql += " AND w.pond_id = ?"
            params.append(pond_id)
        if batch_id:
            sql += " AND w.batch_id = ?"
            params.append(batch_id)
        if start_time:
            sql += " AND w.recorded_at >= ?"
            params.append(start_time)
        if end_time:
            sql += " AND w.recorded_at <= ?"
            params.append(end_time)
        if source_type:
            sql += " AND w.source_type = ?"
            params.append(source_type)
        sql += " ORDER BY w.recorded_at DESC, w.record_id DESC"
        return query_df(sql, tuple(params))
