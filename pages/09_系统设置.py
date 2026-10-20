# -*- coding: utf-8 -*-
"""
09 系统设置 (V3.3 全中文表格 + 在线修改系统运行参数与审计日志版)
"""

import pandas as pd
import streamlit as st
from config.settings import SEVERITY_LABELS, get_metric_label_cn
from components.theme import init_page
from repositories.alert_repo import AlertRepository
from repositories.system_repo import SystemRepository

init_page("系统设置", "系统设置")

t_rules, t_sys, t_logs = st.tabs(["📏 水质预警阈值规则配置", "⚙️ 系统运行与 AI 模式配置", "📜 关键操作审计日志"])

with t_rules:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">水质预警规则配置表</span></div></div>', unsafe_allow_html=True)
    rules = AlertRepository.list_rules()
    st.dataframe(
        pd.DataFrame([
            {
                "规则ID": r["rule_id"],
                "规则编号": r["rule_code"],
                "规则名称": r["rule_name"],
                "监测指标": get_metric_label_cn(r["metric_name"]),
                "判断方向": "低于阈值 (<)" if r["comparison_op"] == "LT" else "高于阈值 (>)",
                "当前阈值": f"{r['threshold_value']} {r['unit']}".strip(),
                "风险等级": SEVERITY_LABELS.get(r["severity"], r["severity"]),
                "启用状态": "已启用" if r["is_enabled"] else "已停用",
                "规则依据说明": r["description"],
            }
            for r in rules
        ]),
        use_container_width=True,
        hide_index=True,
    )

    with st.form("edit_rule_form_v33"):
        st.markdown("#### 修改预警规则阈值")
        c1, c2, c3 = st.columns(3)
        with c1:
            r_id = st.selectbox("选择规则", options=[r["rule_id"] for r in rules], format_func=lambda rid: next(f"{r['rule_code']} - {r['rule_name']}" for r in rules if r["rule_id"] == rid))
            cur_rule = next(r for r in rules if r["rule_id"] == r_id)
        with c2:
            new_th = st.number_input("新阈值数值", value=float(cur_rule["threshold_value"]), step=0.1)
        with c3:
            st.write("")
            enabled = st.checkbox("启用该预警规则", value=bool(cur_rule["is_enabled"]))
        if st.form_submit_button("✅ 保存规则配置"):
            AlertRepository.update_rule_threshold(r_id, new_th, 1 if enabled else 0)
            SystemRepository.log_operation("系统设置", "UPDATE_ALERT_RULE", cur_rule["rule_code"], f"更新阈值为 {new_th}, 启用={enabled}")
            st.cache_data.clear()
            st.success("预警规则已更新，后续录入或导入的水质数据将按新阈值判定！")
            st.rerun()

with t_sys:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">系统全局参数配置表</span></div></div>', unsafe_allow_html=True)
    settings = SystemRepository.list_settings()
    st.dataframe(
        pd.DataFrame([
            {
                "配置ID": s["setting_id"],
                "参数键名": s["setting_key"],
                "当前参数值": s["setting_value"],
                "所属分组": s["setting_group"],
                "参数作用说明": s["description"],
                "最近更新时间": s["updated_at"],
            }
            for s in settings
        ]),
        use_container_width=True,
        hide_index=True,
    )

    with st.form("edit_sys_setting_v33"):
        st.markdown("#### 在线修改系统运行参数")
        sc1, sc2 = st.columns(2)
        with sc1:
            s_key = st.selectbox("选择参数项", options=[s["setting_key"] for s in settings], format_func=lambda k: next(f"{s['setting_key']} ({s['description'][:22]}...)" for s in settings if s["setting_key"] == k))
        with sc2:
            cur_val = next(s["setting_value"] for s in settings if s["setting_key"] == s_key)
            new_val = st.text_input("新参数值", value=cur_val)
        if st.form_submit_button("✅ 保存系统参数"):
            SystemRepository.update_setting(s_key, new_val.strip())
            SystemRepository.log_operation("系统设置", "UPDATE_SYSTEM_SETTING", s_key, f"更新参数值为 {new_val.strip()}")
            st.cache_data.clear()
            st.success(f"参数 `{s_key}` 已更新为 `{new_val.strip()}`！")
            st.rerun()

with t_logs:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">关键业务操作审计日志 (最近 50 条)</span></div></div>', unsafe_allow_html=True)
    logs = SystemRepository.list_logs(limit=50)
    if logs:
        st.dataframe(
            pd.DataFrame([
                {
                    "日志ID": l["log_id"],
                    "所属模块": l["module_name"],
                    "操作类型": l["action_type"],
                    "关联对象": l["target_ref"] or "--",
                    "操作详情": l["detail"],
                    "操作人": l["operator_name"],
                    "记录时间": l["created_at"],
                }
                for l in logs
            ]),
            use_container_width=True,
            hide_index=True,
        )
