# -*- coding: utf-8 -*-
"""
03 智能预警中心 (V3.4 完善版：含告警趋势折线/等级柱状双视图 + 人工异常告警登记 + 闭环追溯)
"""

from datetime import datetime
import streamlit as st
import pandas as pd
from config.settings import ALERT_STATUS_LABELS, SEVERITY_LABELS, WATER_METRICS
from components.theme import init_page
from components.metrics import render_kpi_card
from components.charts import build_donut_chart, apply_dark_tech_layout
from repositories.alert_repo import AlertRepository
from repositories.farm_repo import FarmRepository
from services.alert_service import AlertService

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

init_page("智能预警中心", "智能预警中心")

all_alerts = AlertRepository.list_alerts()
cnt_new = sum(1 for a in all_alerts if a["status"] == "NEW")
cnt_ack = sum(1 for a in all_alerts if a["status"] == "ACKNOWLEDGED")
cnt_res = sum(1 for a in all_alerts if a["status"] == "RESOLVED")
cnt_cls = sum(1 for a in all_alerts if a["status"] == "CLOSED")
cnt_total = len(all_alerts)

# 1. 顶部 4 大告警统计卡
ak1, ak2, ak3, ak4 = st.columns(4)
with ak1:
    render_kpi_card("累计告警总数", f"{cnt_total}", "条", f"待确认 {cnt_new} 条", "alert" if cnt_new > 0 else "up", "🚨", "#ff3366")
with ak2:
    render_kpi_card("待处理/处理中", f"{cnt_new + cnt_ack}", "条", f"处理中 {cnt_ack} 条", "alert" if (cnt_new + cnt_ack) > 0 else "up", "⏱️", "#ffb703")
with ak3:
    render_kpi_card("已复测解决", f"{cnt_res}", "条", "复测达标已完成", "up", "✅", "#06d6a0")
with ak4:
    render_kpi_card("已归档关闭", f"{cnt_cls}", "条", "全流程历史可追溯", "up", "📊", "#00bbf9")

st.write("")

# 2. 中部三栏：类型分布环形图 + 告警趋势/等级分布切换 + 最新告警动态列表
mc1, mc2, mc3 = st.columns([1.1, 1.5, 1.4])

with mc1:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">告警类型分布</span></div></div>', unsafe_allow_html=True)
    type_counts: dict = {}
    for a in all_alerts:
        t = a["alert_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    fig_types = build_donut_chart(
        labels=list(type_counts.keys()) if type_counts else ["无告警"],
        values=list(type_counts.values()) if type_counts else [1],
        title="",
        center_text=f"{cnt_total}<br>告警总数",
        height=220,
    )
    st.plotly_chart(fig_types, use_container_width=True)

with mc2:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">告警趋势与等级统计</span></div></div>', unsafe_allow_html=True)
    chart_mode = st.radio("图表视图：", ["TREND", "BAR"], format_func=lambda m: "📈 告警时段趋势折线" if m == "TREND" else "📊 风险等级实时分布", horizontal=True, label_visibility="collapsed")
    if HAS_PLOTLY:
        if chart_mode == "TREND":
            hours = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
            fig_t = go.Figure()
            fig_t.add_trace(go.Scatter(x=hours, y=[2, 4, 3, 5, 4, cnt_total], name="累计告警", mode="lines+markers", line=dict(color="#ff3366", width=2.5, shape="spline"), fill="tozeroy", fillcolor="rgba(255,51,102,0.08)"))
            fig_t.add_trace(go.Scatter(x=hours, y=[1, 2, 1, 3, 2, cnt_new + cnt_ack], name="活动待处理", mode="lines+markers", line=dict(color="#ffb703", width=2, shape="spline")))
            st.plotly_chart(apply_dark_tech_layout(fig_t, "", height=195), use_container_width=True)
        else:
            sev_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            sev_labels = [SEVERITY_LABELS[k] for k in sev_order]
            sev_vals = [sum(1 for a in all_alerts if a["severity"] == k) for k in sev_order]
            fig_sev = go.Figure(data=[go.Bar(
                x=sev_labels,
                y=sev_vals,
                marker=dict(color=["#ff3366", "#fb8500", "#ffb703", "#00bbf9"]),
                text=sev_vals,
                textposition="auto",
            )])
            st.plotly_chart(apply_dark_tech_layout(fig_sev, "", height=195), use_container_width=True)

with mc3:
    latest_strips = []
    for a in all_alerts[:3]:
        cls = "" if a["severity"] in ("CRITICAL", "HIGH") else "warn"
        st_lbl = ALERT_STATUS_LABELS.get(a["status"], a["status"])
        st_bg = "#ff3366" if a["status"] == "NEW" else ("#ffb703" if a["status"] == "ACKNOWLEDGED" else "#06d6a0")
        target_name = a["pond_name"] or a["equipment_name"] or "系统节点"
        m_lbl = WATER_METRICS.get(a["metric_name"], {}).get("label", a["metric_name"])
        desc_str = f"实测 {a['metric_value']}{a['unit'] or ''} (阈值 {a['threshold_value']}{a['unit'] or ''})" if a["metric_value"] is not None else a["alert_type"]
        latest_strips.append(
            f'<div class="alert-strip {cls}"><div><div class="alert-title">🚨 {target_name} · {m_lbl}</div>'
            f'<div class="alert-desc">{desc_str}</div></div>'
            f'<span style="background:{st_bg}; color:#fff; font-size:0.74rem; padding:2px 8px; border-radius:4px; white-space:nowrap;">{st_lbl}</span></div>'
        )
    st.markdown(
        f"""<div class="tech-card">
<div class="tech-card-header">
<span class="tech-card-title">最新告警实时状态</span>
<span class="tech-card-action">动态同步</span>
</div>
{"".join(latest_strips)}
</div>""",
        unsafe_allow_html=True,
    )

# 3. 底部：告警筛选、明细列表、闭环处置与人工异常登记
st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">告警台账筛选与闭环管理</span></div></div>', unsafe_allow_html=True)
f1, f2 = st.columns(2)
with f1:
    st_filter = st.selectbox("按处理状态筛选：", options=["ALL", "NEW", "ACKNOWLEDGED", "RESOLVED", "CLOSED"], format_func=lambda s: "全部状态" if s == "ALL" else ALERT_STATUS_LABELS[s])
with f2:
    sev_filter = st.selectbox("按风险等级筛选：", options=["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"], format_func=lambda s: "全部风险等级" if s == "ALL" else SEVERITY_LABELS[s])

filtered_alerts = AlertRepository.list_alerts(
    status=None if st_filter == "ALL" else st_filter,
    severity=None if sev_filter == "ALL" else sev_filter,
)

tab_list, tab_handle, tab_manual = st.tabs([
    f"📋 告警明细列表 (共 {len(filtered_alerts)} 条)",
    "🛠️ 告警确认、处置复测与历史追溯",
    "➕ 人工登记养殖/设备异常告警",
])

with tab_list:
    if filtered_alerts:
        table_rows = []
        for a in filtered_alerts:
            m_lbl = WATER_METRICS.get(a["metric_name"], {}).get("label", a["metric_name"])
            table_rows.append({
                "告警编号": a["alert_code"],
                "养殖池/设备": a["pond_name"] or a["equipment_name"] or "--",
                "告警类型": a["alert_type"],
                "异常指标": m_lbl,
                "实测值": f"{a['metric_value']} {a['unit'] or ''}".strip() if a["metric_value"] is not None else "--",
                "设定阈值": f"{a['threshold_value']} {a['unit'] or ''}".strip() if a["threshold_value"] is not None else "--",
                "风险等级": SEVERITY_LABELS.get(a["severity"], a["severity"]),
                "当前状态": ALERT_STATUS_LABELS.get(a["status"], a["status"]),
                "发生时间": a["triggered_at"],
                "处理人": a["handler_name"] or "--",
                "最新处置措施": a["latest_measure"] or "--",
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    else:
        st.info("当前筛选条件下暂无告警记录。")

with tab_handle:
    if all_alerts:
        col_form, col_hist = st.columns([1.2, 1.3])
        alert_map = {a["alert_id"]: f"{a['alert_code']} | {a['pond_name'] or a['equipment_name']} ({ALERT_STATUS_LABELS.get(a['status'])})" for a in all_alerts}
        with col_form:
            sel_aid = st.selectbox("选择要处置或查看历史的告警单：", options=list(alert_map.keys()), format_func=lambda k: alert_map[k])
            cur_a = next(a for a in all_alerts if a["alert_id"] == sel_aid)
            with st.form("alert_process_v34"):
                t_status = st.selectbox("目标变更状态：", options=["ACKNOWLEDGED", "RESOLVED", "CLOSED"], format_func=lambda s: ALERT_STATUS_LABELS[s])
                h_name = st.text_input("处置人员姓名：", value=cur_a["handler_name"] or "张工")
                h_measure = st.text_area("处置措施说明：", value=cur_a["latest_measure"] or "开启备用纯氧增氧机并调整生物滤池反冲洗频率")
                r_val = st.number_input("复测指标数值（可选）：", value=6.2, step=0.1)
                r_conc = st.text_input("复测结论 / 关闭说明：", value=cur_a["retest_result"] or "复测指标恢复正常安全区间")
                if st.form_submit_button("✅ 提交处置并更新状态"):
                    try:
                        AlertService.transition_alert(sel_aid, t_status, h_name, h_measure, r_val, r_conc, r_conc)
                        st.cache_data.clear()
                        st.success("告警状态更新成功，处理历史已写入数据库！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"处理失败: {e}")
        with col_hist:
            st.markdown(f"#### 📜 告警 `{cur_a['alert_code']}` 全生命周期追溯历史")
            hist = AlertRepository.list_process_history(sel_aid)
            if hist:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "处理时间": h["processed_at"],
                            "动作": h["action_type"],
                            "状态流转": f"{ALERT_STATUS_LABELS.get(h['from_status'], '初始')} → {ALERT_STATUS_LABELS.get(h['to_status'], h['to_status'])}",
                            "处理人": h["handler_name"],
                            "措施与复测结论": f"{h['action_measure'] or ''} {(' | 复测:' + h['retest_conclusion']) if h['retest_conclusion'] else ''}",
                        }
                        for h in hist
                    ]),
                    use_container_width=True,
                    hide_index=True,
                )

with tab_manual:
    ponds = FarmRepository.list_ponds()
    with st.form("manual_alert_v34"):
        st.markdown("#### ➕ 人工登记现场巡塘异常（依据设计文档 3.3 节）")
        mc_a, mc_b, mc_c = st.columns(3)
        with mc_a:
            m_pond = st.selectbox("关联养殖池", options=[p["pond_id"] for p in ponds], format_func=lambda pid: next(p["pond_name"] for p in ponds if p["pond_id"] == pid))
            m_type = st.selectbox("异常类型", options=["人工巡检养殖异常", "设备状态异常", "摄食活力减退异常", "水色藻相突变异常"])
        with mc_b:
            m_metric = st.text_input("异常现象/指标名称", value="夜间巡塘轻度浮头/摄食减缓")
            m_sev = st.selectbox("风险等级", options=["HIGH", "MEDIUM", "CRITICAL", "LOW"], format_func=lambda s: SEVERITY_LABELS[s])
        with mc_c:
            m_val = st.number_input("实测参考值（可选）", value=4.8, step=0.1)
            m_th = st.number_input("对比标准值（可选）", value=5.0, step=0.1)
        if st.form_submit_button("✅ 提交人工异常告警"):
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            code_s = f"ALT-MAN-{datetime.now().strftime('%H%M%S')}"
            AlertRepository.create_alert_with_log(
                alert_code=code_s,
                pond_id=m_pond,
                equipment_id=None,
                rule_id=None,
                alert_type=m_type,
                metric_name=m_metric,
                metric_value=m_val,
                unit="",
                threshold_value=m_th,
                severity=m_sev,
                triggered_at=now_s,
                source_type="MANUAL",
            )
            st.cache_data.clear()
            st.success(f"人工异常告警 `{code_s}` 已创建并纳入预警闭环！")
            st.rerun()
