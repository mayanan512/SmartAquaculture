# -*- coding: utf-8 -*-
"""
设备管理与在线率计算服务层。
严格按照文档第 6.6 节：
设备在线率（%） = 统计时点在线设备数 ÷ 纳入统计的设备总数 × 100%
并支持设备状态变更与告警闭环自动联动。
"""

from datetime import datetime
from typing import Any, Dict, Optional
from repositories.equipment_repo import EquipmentRepository
from repositories.alert_repo import AlertRepository
from repositories.system_repo import SystemRepository
from services.alert_service import AlertService


class EquipmentService:
    @staticmethod
    def get_equipment_summary(pond_id: Optional[int] = None) -> Dict[str, Any]:
        items = EquipmentRepository.list_equipment(pond_id=pond_id)
        total = len(items)
        online = sum(1 for e in items if e["status"] == "ONLINE")
        offline = sum(1 for e in items if e["status"] == "OFFLINE")
        fault = sum(1 for e in items if e["status"] == "FAULT")
        online_rate = round((online / total * 100.0), 1) if total > 0 else 0.0
        has_simulated = any(e["source_type"] == "SIMULATED" for e in items)
        return {
            "total": total,
            "online": online,
            "offline": offline,
            "fault": fault,
            "online_rate_pct": online_rate,
            "is_simulated": has_simulated,
            "items": items,
        }

    @staticmethod
    def update_status_with_alert_sync(
        equipment_id: int,
        new_status: str,
        remark: str = "",
        operator_name: str = "张工",
        source_type: str = "MANUAL",
    ) -> Dict[str, Any]:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        all_eq = EquipmentRepository.list_equipment()
        target_eq = next((e for e in all_eq if e["equipment_id"] == equipment_id), None)
        if not target_eq:
            raise ValueError(f"未找到设备 ID: {equipment_id}")

        EquipmentRepository.update_equipment_status(
            equipment_id=equipment_id,
            status=new_status,
            reported_at=now_str,
            source_type=source_type,
            remark=remark or f"人工更新状态为 {new_status}",
        )

        sync_msg = ""
        active_alerts = AlertRepository.list_alerts()
        eq_active_alerts = [
            a for a in active_alerts
            if a.get("equipment_id") == equipment_id and a["status"] in ("NEW", "ACKNOWLEDGED")
        ]

        if new_status == "ONLINE" and eq_active_alerts:
            for a in eq_active_alerts:
                AlertService.transition_alert(
                    alert_id=a["alert_id"],
                    target_status="RESOLVED",
                    handler_name=operator_name,
                    action_measure=remark or "设备检修恢复在线",
                    retest_value=1.0,
                    retest_conclusion="设备恢复在线正常上报",
                )
            sync_msg = f"，并已自动将 {len(eq_active_alerts)} 条关联设备告警更新为【已解决】"
        elif new_status in ("FAULT", "OFFLINE") and not eq_active_alerts:
            alert_code = f"ALT-EQ-{datetime.now().strftime('%m%d%H%M%S')}"
            sev = "HIGH" if new_status == "FAULT" else "MEDIUM"
            AlertRepository.create_alert_with_log(
                alert_code=alert_code,
                pond_id=target_eq.get("pond_id"),
                equipment_id=equipment_id,
                rule_id=None,
                alert_type="设备状态异常",
                metric_name="设备运行状态",
                metric_value=None,
                unit="",
                threshold_value=None,
                severity=sev,
                triggered_at=now_str,
                source_type=source_type,
            )
            sync_msg = f"，并已自动触发设备异常告警（编号 `{alert_code}`）"

        SystemRepository.log_operation(
            "养殖场与设备管理",
            "UPDATE_EQUIPMENT_STATUS",
            target_eq["equipment_code"],
            f"状态变更为 {new_status}：{remark}{sync_msg}",
            operator_name,
        )
        return {"equipment_code": target_eq["equipment_code"], "new_status": new_status, "sync_msg": sync_msg}
