# -*- coding: utf-8 -*-
"""养殖生产管理数据访问层（批次、放养、投喂、生长、死亡、出塘与成本）。"""

from typing import Any, Dict, List, Optional
from repositories.base_repo import query_all, query_one, execute_write


class ProductionRepository:
    @staticmethod
    def list_batches(pond_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT b.*, p.pond_name, p.pond_code, s.species_name, s.category
        FROM culture_batches b
        JOIN fishponds p ON b.pond_id = p.pond_id
        JOIN species s ON b.species_id = s.species_id
        WHERE 1=1
        """
        params: list = []
        if pond_id:
            sql += " AND b.pond_id = ?"
            params.append(pond_id)
        if status:
            sql += " AND b.status = ?"
            params.append(status)
        sql += " ORDER BY b.batch_id DESC"
        return query_all(sql, tuple(params))

    @staticmethod
    def get_batch(batch_id: int) -> Optional[Dict[str, Any]]:
        return query_one(
            """SELECT b.*, p.pond_name, p.pond_code, s.species_name, s.category
               FROM culture_batches b
               JOIN fishponds p ON b.pond_id = p.pond_id
               JOIN species s ON b.species_id = s.species_id
               WHERE b.batch_id = ?""",
            (batch_id,),
        )

    @staticmethod
    def list_feeding_records(batch_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT f.*, b.batch_code, p.pond_name
        FROM feeding_records f
        JOIN culture_batches b ON f.batch_id = b.batch_id
        JOIN fishponds p ON f.pond_id = p.pond_id
        """
        if batch_id:
            return query_all(sql + " WHERE f.batch_id = ? ORDER BY f.fed_at DESC", (batch_id,))
        return query_all(sql + " ORDER BY f.fed_at DESC")

    @staticmethod
    def list_growth_records(batch_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT g.*, b.batch_code, p.pond_name
        FROM growth_records g
        JOIN culture_batches b ON g.batch_id = b.batch_id
        JOIN fishponds p ON g.pond_id = p.pond_id
        """
        if batch_id:
            return query_all(sql + " WHERE g.batch_id = ? ORDER BY g.sampled_at DESC", (batch_id,))
        return query_all(sql + " ORDER BY g.sampled_at DESC")

    @staticmethod
    def list_mortality_records(batch_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT m.*, b.batch_code, p.pond_name
        FROM mortality_records m
        JOIN culture_batches b ON m.batch_id = b.batch_id
        JOIN fishponds p ON m.pond_id = p.pond_id
        """
        if batch_id:
            return query_all(sql + " WHERE m.batch_id = ? ORDER BY m.recorded_at DESC", (batch_id,))
        return query_all(sql + " ORDER BY m.recorded_at DESC")

    @staticmethod
    def list_harvest_records(batch_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT h.*, b.batch_code, p.pond_name
        FROM harvest_records h
        JOIN culture_batches b ON h.batch_id = b.batch_id
        JOIN fishponds p ON h.pond_id = p.pond_id
        """
        if batch_id:
            return query_all(sql + " WHERE h.batch_id = ? ORDER BY h.harvested_at DESC", (batch_id,))
        return query_all(sql + " ORDER BY h.harvested_at DESC")

    @staticmethod
    def list_cost_records(batch_id: Optional[int] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT c.*, b.batch_code, p.pond_name
        FROM cost_records c
        LEFT JOIN culture_batches b ON c.batch_id = b.batch_id
        LEFT JOIN fishponds p ON c.pond_id = p.pond_id
        """
        if batch_id:
            return query_all(sql + " WHERE c.batch_id = ? ORDER BY c.occurred_at DESC", (batch_id,))
        return query_all(sql + " ORDER BY c.occurred_at DESC")
