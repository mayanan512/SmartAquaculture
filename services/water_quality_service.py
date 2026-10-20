# -*- coding: utf-8 -*-
"""
水质监测中心业务服务层。
负责水质数据校验、缺失状态标记、入库保存及自动联动预警服务。
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import pandas as pd
from config.settings import QUALITY_VALID, QUALITY_MISSING
from repositories.water_quality_repo import WaterQualityRepository
from repositories.production_repo import ProductionRepository
from services.alert_service import AlertService


class WaterQualityService:
    @staticmethod
    def validate_and_save(
        pond_id: int,
        recorded_at: str,
        water_temp_c: Optional[float],
        dissolved_oxygen_mg_l: Optional[float],
        ph: Optional[float],
        ammonia_mg_l: Optional[float],
        source_type: str = "MANUAL",
        batch_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """校验单条水质数据、写入数据库并调用预警规则引擎。"""
        metrics = {
            "water_temp_c": water_temp_c,
            "dissolved_oxygen_mg_l": dissolved_oxygen_mg_l,
            "ph": ph,
            "ammonia_mg_l": ammonia_mg_l,
        }
        non_null = [v for v in metrics.values() if v is not None and not pd.isna(v)]
        if not non_null:
            raise ValueError("至少需要填写一项有效水质指标数值")

        if water_temp_c is not None and not (-5.0 <= float(water_temp_c) <= 45.0):
            raise ValueError("水温数值超出合理物理范围 (-5°C ~ 45°C)")
        if dissolved_oxygen_mg_l is not None and not (0.0 <= float(dissolved_oxygen_mg_l) <= 30.0):
            raise ValueError("溶解氧数值超出合理范围 (0 ~ 30 mg/L)")
        if ph is not None and not (0.0 <= float(ph) <= 14.0):
            raise ValueError("pH 值必须在 0 ~ 14 之间")
        if ammonia_mg_l is not None and not (0.0 <= float(ammonia_mg_l) <= 20.0):
            raise ValueError("氨氮数值超出合理范围 (0 ~ 20 mg/L)")

        quality_status = QUALITY_VALID if len(non_null) == 4 else QUALITY_MISSING

        if batch_id is None:
            active_batches = ProductionRepository.list_batches(pond_id=pond_id, status="ACTIVE")
            if active_batches:
                batch_id = active_batches[0]["batch_id"]

        record_id = WaterQualityRepository.insert_record(
            pond_id=pond_id,
            recorded_at=recorded_at,
            water_temp_c=water_temp_c,
            dissolved_oxygen_mg_l=dissolved_oxygen_mg_l,
            ph=ph,
            ammonia_mg_l=ammonia_mg_l,
            source_type=source_type,
            quality_status=quality_status,
            batch_id=batch_id,
        )

        triggered = AlertService.evaluate_water_quality_record(
            pond_id=pond_id,
            recorded_at=recorded_at,
            metrics=metrics,
            source_type=source_type,
        )
        return {"record_id": record_id, "quality_status": quality_status, "alerts": triggered}

    @staticmethod
    def import_from_dataframe(df: pd.DataFrame, default_source: str = "MANUAL") -> Tuple[int, int, list]:
        """批量导入 CSV/Excel 水质数据，返回 (成功数, 失败数, 错误原因列表)。"""
        required_cols = {"pond_id", "recorded_at"}
        missing = required_cols - set(df.columns)
        if missing:
            return 0, len(df), [f"缺少必填列: {', '.join(sorted(missing))}"]

        success_cnt = 0
        fail_cnt = 0
        errors = []
        for idx, row in df.iterrows():
            try:
                pond_id = int(row["pond_id"])
                recorded_at = str(row["recorded_at"]).strip()
                datetime.fromisoformat(recorded_at.replace("/", "-"))
                temp = None if pd.isna(row.get("water_temp_c")) else float(row.get("water_temp_c"))
                do_val = None if pd.isna(row.get("dissolved_oxygen_mg_l")) else float(row.get("dissolved_oxygen_mg_l"))
                ph_val = None if pd.isna(row.get("ph")) else float(row.get("ph"))
                nh3_val = None if pd.isna(row.get("ammonia_mg_l")) else float(row.get("ammonia_mg_l"))
                src = str(row.get("source_type") or default_source).strip()
                WaterQualityService.validate_and_save(
                    pond_id=pond_id,
                    recorded_at=recorded_at,
                    water_temp_c=temp,
                    dissolved_oxygen_mg_l=do_val,
                    ph=ph_val,
                    ammonia_mg_l=nh3_val,
                    source_type=src,
                )
                success_cnt += 1
            except Exception as exc:
                fail_cnt += 1
                errors.append(f"第 {idx + 1} 行导入失败: {exc}")
        return success_cnt, fail_cnt, errors
