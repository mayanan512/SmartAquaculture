# -*- coding: utf-8 -*-
"""
AI 智能决策辅助服务层 (v0.2.0 双模增强版)。
遵循文档第 3.5 节约束：
1. 自动整合水质现状、历史趋势斜率、Scikit-learn IsolationForest 多维异常分、品种适宜范围与活动告警。
2. 支持接入兼容 OpenAI 格式的外部大模型 REST API（DeepSeek / 通义千问 / OpenAI / 本地 Ollama 等）。
3. 具备高可用降级保障：当未配置 API Key、网络受限或请求超时时，自动无缝切换至本地规则+机器学习引擎，不影响系统运行。
4. 严格安全边界：AI 输出仅供人工核查参考，绝不直接自动控制增氧机、水泵或投喂设备。
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List, Optional
from algorithms.anomaly_detector import analyze_series_trend, detect_multivariate_anomalies_iforest
from database.connection import db_transaction
from repositories.alert_repo import AlertRepository
from repositories.base_repo import query_all
from repositories.farm_repo import FarmRepository
from repositories.system_repo import SystemRepository
from repositories.water_quality_repo import WaterQualityRepository
from services.production_service import ProductionService


class AIDecisionService:
    RULE_ENGINE_VERSION = "本地专家规则与孤立森林多维检测引擎 v2.0"

    @staticmethod
    def _call_openai_compatible_llm(
        api_base: str,
        api_key: str,
        model_name: str,
        context_prompt: str,
        timeout_sec: int = 15,
    ) -> Dict[str, str]:
        """通过标准库 urllib 调用兼容 OpenAI /v1/chat/completions 的大模型接口。"""
        url = api_base.rstrip("/") + "/chat/completions"
        system_msg = (
            "你是『智渔云』智慧水产养殖数字孪生平台的资深水产养殖与水质工程专家AI助手。"
            "请严格基于提供的实测/模拟数据上下文进行分析，禁止编造未提供的数值，禁止下达自动启停硬件指令。"
            "请以 JSON 格式输出三个字段：status_summary（现状摘要）、cause_analysis（分条原因分析，用换行分隔）、"
            "action_suggestions（分条人工核查与处置建议，用换行分隔，末尾注明安全边界）。"
        )
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": context_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return {
                "status_summary": str(parsed.get("status_summary", "")).strip(),
                "cause_analysis": str(parsed.get("cause_analysis", "")).strip(),
                "action_suggestions": str(parsed.get("action_suggestions", "")).strip(),
            }

    @staticmethod
    def generate_pond_analysis(pond_id: int, api_key_override: Optional[str] = None) -> Dict[str, Any]:
        pond = FarmRepository.get_pond(pond_id)
        if not pond:
            raise ValueError(f"未找到养殖池 ID={pond_id}")

        latest_wq = WaterQualityRepository.get_latest_by_pond(pond_id)
        wq_df = WaterQualityRepository.query_records_df(pond_id=pond_id)
        active_alerts = [
            a for a in AlertRepository.list_alerts(pond_id=pond_id)
            if a["status"] in ("NEW", "ACKNOWLEDGED")
        ]

        batch_info = None
        species_info = None
        if pond.get("active_batch_id"):
            batch_info = ProductionService.calculate_batch_metrics(pond["active_batch_id"])
            for sp in FarmRepository.list_species():
                if sp["species_id"] == batch_info["species_id"]:
                    species_info = sp
                    break

        # 1. 多维异常检测 (IsolationForest) 与趋势斜率
        iforest_res = detect_multivariate_anomalies_iforest(wq_df)
        do_trend = {"trend_label": "无数据"}
        nh3_trend = {"trend_label": "无数据"}
        if not wq_df.empty:
            wq_sorted = wq_df.sort_values("recorded_at")
            do_trend = analyze_series_trend(wq_sorted["dissolved_oxygen_mg_l"].tolist())
            nh3_trend = analyze_series_trend(wq_sorted["ammonia_mg_l"].tolist())

        if latest_wq:
            wq_summary_str = (
                f"采集时间 {latest_wq['recorded_at']} (来源:{latest_wq['source_type']}) | "
                f"水温:{latest_wq['water_temp_c'] if latest_wq['water_temp_c'] is not None else '缺失'}°C, "
                f"溶解氧:{latest_wq['dissolved_oxygen_mg_l'] if latest_wq['dissolved_oxygen_mg_l'] is not None else '缺失'}mg/L, "
                f"pH:{latest_wq['ph'] if latest_wq['ph'] is not None else '缺失'}, "
                f"氨氮:{latest_wq['ammonia_mg_l'] if latest_wq['ammonia_mg_l'] is not None else '缺失'}mg/L"
            )
        else:
            wq_summary_str = "暂无水质监测记录"

        iforest_text = iforest_res.get("summary", "样本不足未启用多维离群检测")
        input_summary = (
            f"养殖池：{pond['pond_name']} ({pond['pond_code']}) | "
            f"在养批次：{batch_info['batch_code'] if batch_info else '无在养批次'} "
            f"({species_info['species_name'] if species_info else '未关联品种'}) | "
            f"最新水质：{wq_summary_str} | 活动告警数：{len(active_alerts)} | {iforest_text}"
        )

        # 2. 检查是否配置了外部大模型 API
        settings = SystemRepository.get_settings_dict()
        api_key = (api_key_override or os.environ.get("OPENAI_API_KEY") or "").strip()
        api_base = os.environ.get("OPENAI_BASE_URL") or settings.get("llm_api_base", "https://api.deepseek.com/v1")
        model_name = os.environ.get("OPENAI_MODEL") or settings.get("llm_model_name", "deepseek-chat")
        timeout_sec = int(settings.get("llm_timeout_seconds", "15") or 15)

        engine_used = AIDecisionService.RULE_ENGINE_VERSION
        llm_output = None

        if api_key:
            try:
                llm_output = AIDecisionService._call_openai_compatible_llm(
                    api_base=api_base,
                    api_key=api_key,
                    model_name=model_name,
                    context_prompt=input_summary,
                    timeout_sec=timeout_sec,
                )
                if llm_output.get("status_summary") and llm_output.get("cause_analysis"):
                    engine_used = f"LLM-API ({model_name}) + 孤立森林多维检测"
                else:
                    llm_output = None
            except Exception as exc:
                engine_used = f"{AIDecisionService.RULE_ENGINE_VERSION} [大模型调用降级: {type(exc).__name__}]"
                llm_output = None

        # 3. 本地规则引擎与模板生成（默认或自动降级路径）
        if llm_output is not None:
            status_summary = llm_output["status_summary"]
            cause_text = llm_output["cause_analysis"]
            suggestion_text = llm_output["action_suggestions"]
        else:
            causes: List[str] = []
            suggestions: List[str] = []

            if not latest_wq:
                status_summary = f"{pond['pond_name']} 当前尚无水质监测数据，无法开展定量风险判定。"
                causes.append("尚未录入或导入该池塘的水质记录。")
                suggestions.append("请前往【水质监测中心】录入或通过 CSV 导入最新实测数据。")
            else:
                if active_alerts:
                    status_summary = (
                        f"【存在 {len(active_alerts)} 项活动预警】{pond['pond_name']} 最新监测时间 {latest_wq['recorded_at']}，"
                        f"溶解氧序列{do_trend['trend_label']}，氨氮序列{nh3_trend['trend_label']}；{iforest_text}。"
                    )
                else:
                    status_summary = (
                        f"【水质整体平稳】{pond['pond_name']} 最新各项已采集指标均处于配置阈值范围内，"
                        f"溶解氧序列{do_trend['trend_label']}，氨氮序列{nh3_trend['trend_label']}；{iforest_text}。"
                    )

                do_val = latest_wq.get("dissolved_oxygen_mg_l")
                nh3_val = latest_wq.get("ammonia_mg_l")
                temp_val = latest_wq.get("water_temp_c")
                ph_val = latest_wq.get("ph")

                if do_val is None or nh3_val is None or temp_val is None or ph_val is None:
                    causes.append("当前监测记录存在缺失字段（NULL），可能是部分传感器探头离线或人工漏填。")
                    suggestions.append("建议核查对应池塘的水质传感终端连接状态，并进行人工便携式仪器复测补录。")

                if do_val is not None and do_val < 5.0:
                    causes.append(f"溶解氧实测值 ({do_val} mg/L) 低于安全下限 (5.0 mg/L)，可能由增氧设备故障、夜间生物耗氧高峰或高密度存量 ({batch_info['estimated_biomass_kg'] if batch_info else '--'} kg) 引起。")
                    suggestions.append("【人工核查建议】立即现场检查增氧机与微孔曝气管运行状态，必要时开启备用增氧设备并暂停当餐投喂。")

                if nh3_val is not None and nh3_val > 0.40:
                    causes.append(f"氨氮实测值 ({nh3_val} mg/L) 高于预警阈值 (0.40 mg/L)，通常与近期投喂蛋白负荷较高、残饵粪便积累或生物滤池硝化效率下降有关。")
                    suggestions.append("【人工核查建议】适量加大循环水换水或生物滤池反冲洗比例，下调后续 1~2 餐投喂量 20%~30%，并补充芽孢杆菌/硝化菌制剂。")

                if iforest_res.get("latest_is_anomaly"):
                    causes.append(f"Scikit-learn IsolationForest 模型识别到当前多指标组合存在离群偏移 (决策分={iforest_res.get('latest_score')})，提示潜在复合水质波动。")
                    suggestions.append("【多维核查建议】缩短未来 6 小时内的水质复测间隔，重点关注水温-pH-非离子氨的耦合变化。")

                if species_info and temp_val is not None:
                    if temp_val < species_info["temp_min_c"] or temp_val > species_info["temp_max_c"]:
                        causes.append(
                            f"水温 ({temp_val}°C) 超出【{species_info['species_name']}】适宜水温区间 ({species_info['temp_min_c']}~{species_info['temp_max_c']}°C)。"
                        )
                        suggestions.append("【人工核查建议】检查车间温控或水源调配系统，根据水温变化动态调整日投喂率。")

                if not causes:
                    causes.append("各项实测水质参数与品种适宜生长范围匹配良好，未发现超阈值异常或多维离群波动。")
                    suggestions.append("维持当前日常巡检、定时投喂与水质监测频次；定期抽样记录生长规格以更新存量估算。")

            suggestions.append("【安全边界说明】以上结论由规则、无监督学习与大模型辅助引擎生成，仅供养殖管理人员核查参考，系统不会自动启停任何现场硬件设备。")
            cause_text = "\n".join(f"{i+1}. {c}" for i, c in enumerate(causes))
            suggestion_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(suggestions))

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_id = active_alerts[0]["alert_id"] if active_alerts else None
        batch_id = batch_info["batch_id"] if batch_info else None

        with db_transaction() as conn:
            cur = conn.execute(
                """INSERT INTO ai_analysis_records
                (pond_id, batch_id, alert_id, engine_version, input_summary, status_summary, cause_analysis, action_suggestions, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pond_id, batch_id, alert_id, engine_used, input_summary, status_summary, cause_text, suggestion_text, now_str),
            )
            analysis_id = int(cur.lastrowid)

        return {
            "analysis_id": analysis_id,
            "pond_id": pond_id,
            "pond_name": pond["pond_name"],
            "engine_version": engine_used,
            "input_summary": input_summary,
            "status_summary": status_summary,
            "cause_analysis": cause_text,
            "action_suggestions": suggestion_text,
            "iforest_result": iforest_res,
            "analyzed_at": now_str,
        }

    @staticmethod
    def list_history(pond_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        sql = """
        SELECT a.*, p.pond_name, p.pond_code
        FROM ai_analysis_records a
        LEFT JOIN fishponds p ON a.pond_id = p.pond_id
        """
        if pond_id:
            return query_all(sql + " WHERE a.pond_id = ? ORDER BY a.analysis_id DESC LIMIT ?", (pond_id, limit))
        return query_all(sql + " ORDER BY a.analysis_id DESC LIMIT ?", (limit,))
