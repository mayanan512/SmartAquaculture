try:
    import streamlit as st
except ImportError:
    class _DummySt:
        @staticmethod
        def cache_data(*a, **kw):
            return lambda fn: fn
    st = _DummySt

# -*- coding: utf-8 -*-
"""
养殖分析报表与大屏全局聚合统计服务层。
确保总览大屏、生产管理与分析报表读取完全一致的计算口径。
"""

from typing import Any, Dict
import pandas as pd
from repositories.alert_repo import AlertRepository
from repositories.base_repo import query_df
from repositories.farm_repo import FarmRepository
from services.equipment_service import EquipmentService
from services.production_service import ProductionService


class ReportService:
    @staticmethod
    @st.cache_data(ttl=2)
    def get_dashboard_overview() -> Dict[str, Any]:
        """获取智慧养殖总览大屏顶部与左右面板所需的全部核心汇总指标。"""
        ponds = FarmRepository.list_ponds()
        in_use_ponds = [p for p in ponds if p["status"] == "IN_USE"]

        batch_metrics = ProductionService.list_all_batch_metrics()
        active_batches = [b for b in batch_metrics if b["status"] == "ACTIVE"]

        total_estimated_biomass_kg = round(sum(b["estimated_biomass_kg"] for b in active_batches), 2)
        total_harvested_kg = round(sum(b["harvested_weight_kg"] for b in batch_metrics), 2)
        total_harvest_revenue_cny = round(sum(b["harvest_revenue_cny"] for b in batch_metrics), 2)
        total_feed_kg = round(sum(b["total_feed_kg"] for b in batch_metrics), 2)
        total_cost_cny = round(sum(b["total_cost_cny"] for b in batch_metrics), 2)

        alerts = AlertRepository.list_alerts()
        unhandled_alerts = [a for a in alerts if a["status"] in ("NEW", "ACKNOWLEDGED")]

        eq_summary = EquipmentService.get_equipment_summary()

        return {
            "total_ponds": len(ponds),
            "in_use_ponds": len(in_use_ponds),
            "active_batches_count": len(active_batches),
            "unhandled_alerts_count": len(unhandled_alerts),
            "equipment_online_rate_pct": eq_summary["online_rate_pct"],
            "total_estimated_biomass_kg": total_estimated_biomass_kg,
            "total_harvested_kg": total_harvested_kg,
            "total_harvest_revenue_cny": total_harvest_revenue_cny,
            "total_feed_kg": total_feed_kg,
            "total_cost_cny": total_cost_cny,
            "ponds": ponds,
            "active_batches": active_batches,
            "all_batch_metrics": batch_metrics,
            "alerts": alerts,
            "equipment_summary": eq_summary,
        }

    @staticmethod
    def get_harvest_by_period_df(period: str = "day") -> pd.DataFrame:
        """按日/周/月统计累计出塘产量与销售金额。"""
        if period == "month":
            date_expr = "substr(h.harvested_at, 1, 7)"
        elif period == "week":
            date_expr = "strftime('%Y-W%W', h.harvested_at)"
        else:
            date_expr = "substr(h.harvested_at, 1, 10)"

        sql = f"""
        SELECT {date_expr} AS period_label,
               p.pond_name,
               s.species_name,
               SUM(h.harvest_count) AS total_count,
               ROUND(SUM(h.total_weight_kg), 2) AS total_weight_kg,
               ROUND(SUM(h.total_amount_cny), 2) AS total_amount_cny
        FROM harvest_records h
        JOIN culture_batches b ON h.batch_id = b.batch_id
        JOIN fishponds p ON h.pond_id = p.pond_id
        JOIN species s ON b.species_id = s.species_id
        GROUP BY period_label, p.pond_name, s.species_name
        ORDER BY period_label ASC
        """
        return query_df(sql)

    @staticmethod
    def get_cost_breakdown_df() -> pd.DataFrame:
        """汇总饲料成本与各项成本记录。"""
        sql = """
        SELECT cost_category AS 成本类别, ROUND(SUM(amount_cny), 2) AS 金额_元
        FROM (
            SELECT '饲料投入' AS cost_category, (feed_weight_kg * unit_price_cny) AS amount_cny FROM feeding_records
            UNION ALL
            SELECT cost_category, amount_cny FROM cost_records
        )
        GROUP BY cost_category
        ORDER BY 金额_元 DESC
        """
        return query_df(sql)
