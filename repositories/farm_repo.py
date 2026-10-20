# -*- coding: utf-8 -*-
"""养殖场、区域、养殖池与品种档案数据访问层。"""

from typing import Any, Dict, List, Optional
from repositories.base_repo import query_all, query_one, execute_write


class FarmRepository:
    @staticmethod
    def list_farms() -> List[Dict[str, Any]]:
        return query_all("SELECT * FROM aquaculture_farms ORDER BY farm_id")

    @staticmethod
    def list_areas(farm_id: Optional[int] = None) -> List[Dict[str, Any]]:
        if farm_id:
            return query_all("SELECT * FROM aquaculture_areas WHERE farm_id = ? ORDER BY area_id", (farm_id,))
        return query_all("SELECT * FROM aquaculture_areas ORDER BY area_id")

    @staticmethod
    def list_ponds(farm_id: Optional[int] = None, area_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
        SELECT p.*, a.area_name, f.farm_name,
               b.batch_id AS active_batch_id, b.batch_code AS active_batch_code,
               s.species_name AS active_species_name
        FROM fishponds p
        JOIN aquaculture_areas a ON p.area_id = a.area_id
        JOIN aquaculture_farms f ON p.farm_id = f.farm_id
        LEFT JOIN culture_batches b ON p.pond_id = b.pond_id AND b.status = 'ACTIVE'
        LEFT JOIN species s ON b.species_id = s.species_id
        WHERE 1=1
        """
        params: list = []
        if farm_id:
            sql += " AND p.farm_id = ?"
            params.append(farm_id)
        if area_id:
            sql += " AND p.area_id = ?"
            params.append(area_id)
        if status:
            sql += " AND p.status = ?"
            params.append(status)
        sql += " ORDER BY p.pond_id"
        return query_all(sql, tuple(params))

    @staticmethod
    def get_pond(pond_id: int) -> Optional[Dict[str, Any]]:
        ponds = FarmRepository.list_ponds()
        for p in ponds:
            if p["pond_id"] == pond_id:
                return p
        return None

    @staticmethod
    def create_pond(pond_code: str, farm_id: int, area_id: int, pond_name: str, pond_type: str, area_m2: float, capacity: float, status: str = "IN_USE") -> int:
        return execute_write(
            """INSERT INTO fishponds (pond_code, farm_id, area_id, pond_name, pond_type, area_m2, capacity, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pond_code, farm_id, area_id, pond_name, pond_type, area_m2, capacity, status),
        )

    @staticmethod
    def list_species() -> List[Dict[str, Any]]:
        return query_all("SELECT * FROM species ORDER BY species_id")

    @staticmethod
    def create_species(species_code: str, species_name: str, category: str, growth_stage: str, temp_min_c: float, temp_max_c: float, do_min_mg_l: float, ph_min: float, ph_max: float, ammonia_max_mg_l: float, remark: str = "") -> int:
        return execute_write(
            """INSERT INTO species
            (species_code, species_name, category, growth_stage, temp_min_c, temp_max_c, do_min_mg_l, ph_min, ph_max, ammonia_max_mg_l, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (species_code, species_name, category, growth_stage, temp_min_c, temp_max_c, do_min_mg_l, ph_min, ph_max, ammonia_max_mg_l, remark),
        )
