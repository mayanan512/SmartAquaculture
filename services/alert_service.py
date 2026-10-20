# -*- coding: utf-8 -*-
"""
智能预警中心业务服务层。
实现文档第 3.3 节与 6.7 节要求：
- 水质记录保存后统一调用 evaluate_water_quality_record() 检查规则
- 命中规则时创建告警，并对同一养殖池、同一规则处于活动状态（NEW/ACKNOWLEDGED）的告警进行重复抑制
- 支持告警确认（ACKNOWLEDGE）、登记处置与复查解决（RESOLVE）、归档关闭（CLOSE）全生命周期追溯
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from algorithms.anomaly_detector import check_metric_against_rule
from config.settings import WATER_METRICS
from database.connection import db_transaction
from repositories.alert_repo import AlertRepository
from repositories.system_repo import SystemRepository


class AlertService:
    @staticmethod
    def evaluate_water_quality_record(
        pond_id: int,
        recorded_at: str,
        metrics: Dict[str, Optional[float]],
        source_type: str = "MANUAL",
    ) -> List[Dict[str, Any]]:
        """检查单条水质记录是否触发启用的预警规则，返回触发结果列表。"""
        rules = AlertRepository.list_rules(only_enabled=True)
        settings = SystemRepository.get_settings_dict()
        suppress_dup = settings.get("suppress_duplicate_alerts", "true").lower() == "true"

        results: List[Dict[str, Any]] = []
        for rule in rules:
            metric_key = rule["metric_name"]
            val = metrics.get(metric_key)
            if check_metric_against_rule(val, rule["comparison_op"], rule["threshold_value"]):
                dup = AlertRepository.find_active_duplicate(pond_id, rule["rule_id"]) if suppress_dup else None
                if dup:
                    results.append({
                        "action": "SUPPRESSED",
                        "rule_name": rule["rule_name"],
                        "metric_name": metric_key,
                        "existing_alert_code": dup["alert_code"],
                    })
                    continue

                alert_code = f"ALT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{pond_id}-{rule['rule_id']}"
                unit = rule["unit"] or WATER_METRICS.get(metric_key, {}).get("unit", "")
                alert_id = AlertRepository.create_alert_with_log(
                    alert_code=alert_code,
                    pond_id=pond_id,
                    equipment_id=None,
                    rule_id=rule["rule_id"],
                    alert_type="水质超阈值预警",
                    metric_name=metric_key,
                    metric_value=val,
                    unit=unit,
                    threshold_value=rule["threshold_value"],
                    severity=rule["severity"],
                    triggered_at=recorded_at,
                    source_type=source_type,
                )
                results.append({
                    "action": "CREATED",
                    "alert_id": alert_id,
                    "alert_code": alert_code,
                    "rule_name": rule["rule_name"],
                    "metric_name": metric_key,
                    "metric_value": val,
                    "threshold_value": rule["threshold_value"],
                    "severity": rule["severity"],
                })
        return results

    @staticmethod
    def transition_alert(
        alert_id: int,
        target_status: str,
        handler_name: str,
        action_measure: str,
        retest_value: Optional[float] = None,
        retest_conclusion: Optional[str] = None,
        close_reason: Optional[str] = None,
    ) -> None:
        """更新告警状态并写入不可篡改的告警处理历史表 (alert_process_records)。"""
        if not handler_name.strip():
            raise ValueError("处理人姓名不能为空")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with db_transaction() as conn:
            row = conn.execute("SELECT * FROM alert_records WHERE alert_id = ?", (alert_id,)).fetchone()
            if not row:
                raise ValueError(f"未找到告警记录 ID={alert_id}")
            from_status = row["status"]

            if target_status == "ACKNOWLEDGED":
                conn.execute(
                    """UPDATE alert_records
                       SET status = 'ACKNOWLEDGED', acknowledged_at = COALESCE(acknowledged_at, ?),
                           handler_name = ?, latest_measure = ?
                       WHERE alert_id = ?""",
                    (now_str, handler_name, action_measure, alert_id),
                )
                action_type = "ACKNOWLEDGE"
            elif target_status == "RESOLVED":
                conn.execute(
                    """UPDATE alert_records
                       SET status = 'RESOLVED', resolved_at = ?, handler_name = ?,
                           latest_measure = ?, retest_result = ?
                       WHERE alert_id = ?""",
                    (now_str, handler_name, action_measure, retest_conclusion or "", alert_id),
                )
                action_type = "RESOLVE"
            elif target_status == "CLOSED":
                conn.execute(
                    """UPDATE alert_records
                       SET status = 'CLOSED', closed_at = ?, handler_name = ?,
                           close_reason = ?
                       WHERE alert_id = ?""",
                    (now_str, handler_name, close_reason or action_measure, alert_id),
                )
                action_type = "CLOSE"
            else:
                raise ValueError(f"不支持的目标告警状态: {target_status}")

            conn.execute(
                """INSERT INTO alert_process_records
                (alert_id, action_type, from_status, to_status, handler_name, action_measure, retest_value, retest_conclusion, processed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (alert_id, action_type, from_status, target_status, handler_name, action_measure, retest_value, retest_conclusion, now_str),
            )
