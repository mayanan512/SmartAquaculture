# -*- coding: utf-8 -*-
"""
01 智慧养殖总览大屏 (V3.9 像素级等高对齐 + 控制条防截断 + 图表零重叠版)
"""

import base64
from datetime import datetime
import random
import streamlit as st
import pandas as pd
from config.settings import ASSETS_DIR, POND_STATUS_LABELS, ALERT_STATUS_LABELS, EQUIPMENT_STATUS_LABELS, get_metric_label_cn
from components.theme import init_page, render_tech_image
from components.metrics import render_kpi_card
from components.charts import build_dual_metric_spline_chart, build_3d_digital_twin_scene, apply_dark_tech_layout
from repositories.farm_repo import FarmRepository
from repositories.water_quality_repo import WaterQualityRepository
from services.report_service import ReportService
from services.water_quality_service import WaterQualityService

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

init_page("智慧养殖总览大屏", "智慧养殖总览")

overview = ReportService.get_dashboard_overview()
species_list = FarmRepository.list_species()
all_batches = overview["all_batch_metrics"]
active_batches = overview["active_batches"]
eq_summary = overview["equipment_summary"]

avg_weight_g = round(sum(b["latest_avg_weight_g"] for b in active_batches) / len(active_batches), 1) if active_batches else 0.0
avg_survival_pct = round(sum(b["biological_survival_rate_pct"] for b in all_batches) / len(all_batches), 1) if all_batches else 0.0

# 1. 顶部 4 大核心 KPI 指标卡 (104px 固定等高)
k1, k2, k3, k4 = st.columns(4)
with k1:
    render_kpi_card("养殖池总数", f"{overview['total_ponds']}", "个", f"在养运行 {overview['in_use_ponds']} 个 (↑6%)", "up", "🌊", "#00f0ff")
with k2:
    render_kpi_card("当前在养批次", f"{overview['active_batches_count']}", "批", f"存量 {overview['total_estimated_biomass_kg']:,.0f} kg (↑8%)", "up", "🐟", "#06d6a0")
with k3:
    render_kpi_card("设备在线率", f"{overview['equipment_online_rate_pct']}", "%", f"在线 {eq_summary['online']} / 总计 {eq_summary['total']} 台", "up", "⚙️", "#00bbf9")
with k4:
    alert_cnt = overview["unhandled_alerts_count"]
    render_kpi_card("未处理告警", f"{alert_cnt}", "条", "待确认 + 处理中告警", "down" if alert_cnt == 0 else "alert", "🚨", "#ff3366" if alert_cnt > 0 else "#06d6a0")

st.write("")

# 2. 三栏大屏核心布局
col_left, col_center, col_right = st.columns([1.18, 1.74, 1.18])

# ==================== 中央数字孪生园区 ====================
with col_center:
    st.markdown(
        """<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">🌐 数字孪生示范园区全景</span>
<span class="tech-card-action">🟢 焦点同步 <a href="?jump_to=05" target="_self" class="card-jump-btn">AI诊断 →</a></span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # 第一行：池塘选择下拉框 + 模拟采集按钮（同行同高无顶置标签，完整显示池塘名与按钮文字）
    c_sel1, c_sel2 = st.columns([1.85, 1.0])
    with c_sel1:
        pond_options = {p["pond_id"]: f"🎯 {p['pond_code']} · {p['pond_name']}" for p in overview["ponds"]}
        default_pid = st.session_state.get("selected_pond_id", overview["ponds"][0]["pond_id"])
        if default_pid not in pond_options:
            default_pid = overview["ponds"][0]["pond_id"]
        sel_pid = st.selectbox(
            "聚焦养殖池点位：",
            options=list(pond_options.keys()),
            format_func=lambda pid: pond_options[pid],
            index=list(pond_options.keys()).index(default_pid),
            label_visibility="collapsed",
        )
        st.session_state["selected_pond_id"] = sel_pid
    with c_sel2:
        if st.button("⚡ 模拟实时采集", use_container_width=True, help="为当前聚焦池塘生成一条最新模拟水质记录并自动检验预警"):
            cur_wq = WaterQualityRepository.get_latest_by_pond(sel_pid)
            base_t = float(cur_wq["water_temp_c"]) if cur_wq and cur_wq["water_temp_c"] is not None else 25.5
            base_do = float(cur_wq["dissolved_oxygen_mg_l"]) if cur_wq and cur_wq["dissolved_oxygen_mg_l"] is not None else 6.2
            base_ph = float(cur_wq["ph"]) if cur_wq and cur_wq["ph"] is not None else 7.8
            base_nh3 = float(cur_wq["ammonia_mg_l"]) if cur_wq and cur_wq["ammonia_mg_l"] is not None else 0.22
            WaterQualityService.validate_and_save(
                pond_id=sel_pid,
                recorded_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                water_temp_c=round(base_t + random.uniform(-0.3, 0.3), 1),
                dissolved_oxygen_mg_l=round(max(3.8, base_do + random.uniform(-0.25, 0.25)), 2),
                ph=round(base_ph + random.uniform(-0.1, 0.1), 2),
                ammonia_mg_l=round(max(0.05, base_nh3 + random.uniform(-0.02, 0.03)), 2),
                source_type="SIMULATED",
            )
            st.cache_data.clear()
            st.rerun()

    # 第二行：全宽水平铺开场景切换单选框，彻底消除三行竖排挤压
    scene_mode = st.radio(
        "场景渲染模式：",
        options=["3D_RENDER", "3D_INTERACTIVE", "2D_VECTOR"],
        format_func=lambda m: "🏢 3D园区实景视图" if m == "3D_RENDER" else ("🧊 3D水体剖面模型" if m == "3D_INTERACTIVE" else "🗺️ 2D平面矢量拓扑"),
        horizontal=True,
        label_visibility="collapsed",
    )

    park_render_img = ASSETS_DIR / "images" / "park_3d_render.png"
    if scene_mode == "3D_RENDER" and park_render_img.exists():
        render_tech_image(park_render_img, caption="智渔云数字孪生示范园区三维实景视图 (A/B/C/D区循环水车间、综合控制中心与尾水净化池)", max_height_px=420)
    elif scene_mode == "3D_INTERACTIVE":
        latest_all_wq = WaterQualityRepository.get_latest_all_ponds()
        fig_3d = build_3d_digital_twin_scene(
            ponds=overview["ponds"],
            latest_wq_list=latest_all_wq,
            active_batches=overview["active_batches"],
            alerts=overview["alerts"],
            selected_pond_id=sel_pid,
        )
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        svg_path = ASSETS_DIR / "images" / "park_map.svg"
        if svg_path.exists():
            render_tech_image(svg_path, caption="智渔云数字孪生示范园区 2D 矢量平面拓扑", max_height_px=420)

    # 底部真实可点击停靠栏 (Dock Bar)
    st.markdown('<div class="tech-card notranslate" translate="no" style="padding:8px 12px; margin-top:4px;"><div class="tech-card-header"><span class="tech-card-title" style="font-size:0.9rem;">🧭 带入当前聚焦池塘快捷跳转</span></div></div>', unsafe_allow_html=True)
    d1, d2, d3, d4, d5, d6 = st.columns(6)
    with d1: st.page_link("pages/02_水质监测中心.py", label="💧 该池水质", use_container_width=True)
    with d2: st.page_link("pages/03_智能预警中心.py", label="🚨 预警处置", use_container_width=True)
    with d3: st.page_link("pages/04_养殖生产管理.py", label="🐟 养殖生产", use_container_width=True)
    with d4: st.page_link("pages/05_AI智能决策.py", label="🤖 AI诊断", use_container_width=True)
    with d5: st.page_link("pages/06_养殖分析报表.py", label="📊 分析报表", use_container_width=True)
    with d6: st.page_link("pages/07_养殖场与设备管理.py", label="⚙️ 池塘设备", use_container_width=True)

selected_pond = next(p for p in overview["ponds"] if p["pond_id"] == sel_pid)
selected_batch = next((b for b in active_batches if b["pond_id"] == sel_pid), None)
latest_wq = WaterQualityRepository.get_latest_by_pond(sel_pid)

# ==================== 左侧数据面板 ====================
with col_left:
    # 2.1 养殖概况卡片
    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">养殖概况</span>
<span class="tech-card-action">实时复算 <a href="?jump_to=04" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; border-left:3px solid #00f0ff;">
<div style="font-size:0.75rem; color:#9cc2ff; white-space:nowrap;">养殖池总数 / 在养</div>
<div style="font-size:1.1rem; font-weight:700; color:#fff;">{overview['total_ponds']} / {overview['in_use_ponds']} <span style="font-size:0.74rem; color:#9cc2ff;">池</span></div>
<div style="font-size:0.7rem; color:#06d6a0;">较上月 ↑ 6%</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; border-left:3px solid #06d6a0;">
<div style="font-size:0.75rem; color:#9cc2ff; white-space:nowrap;">累计出塘产量</div>
<div style="font-size:1.1rem; font-weight:700; color:#fff;">{overview['total_harvested_kg']:,.1f} <span style="font-size:0.74rem; color:#9cc2ff;">kg</span></div>
<div style="font-size:0.7rem; color:#06d6a0;">营收 ¥{overview['total_harvest_revenue_cny']:,.0f}</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; border-left:3px solid #00b4d8;">
<div style="font-size:0.75rem; color:#9cc2ff; white-space:nowrap;">养殖品种</div>
<div style="font-size:1.1rem; font-weight:700; color:#fff;">{len(species_list)} <span style="font-size:0.74rem; color:#9cc2ff;">种</span></div>
<div style="font-size:0.7rem; color:#9cc2ff;">鱼 / 虾 / 蟹协同</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; border-left:3px solid #ffb703;">
<div style="font-size:0.75rem; color:#9cc2ff; white-space:nowrap;">当前估算存量</div>
<div style="font-size:1.1rem; font-weight:700; color:#fff;">{overview['total_estimated_biomass_kg']:,.1f} <span style="font-size:0.74rem; color:#9cc2ff;">kg</span></div>
<div style="font-size:0.7rem; color:#06d6a0;">较上月 ↑ 8%</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; border-left:3px solid #9d4edd;">
<div style="font-size:0.75rem; color:#9cc2ff; white-space:nowrap;">平均规格</div>
<div style="font-size:1.1rem; font-weight:700; color:#fff;">{avg_weight_g} <span style="font-size:0.74rem; color:#9cc2ff;">g</span></div>
<div style="font-size:0.7rem; color:#06d6a0;">较上月 ↑ 4%</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; border-left:3px solid #00f0ff;">
<div style="font-size:0.75rem; color:#9cc2ff; white-space:nowrap;">综合成活率</div>
<div style="font-size:1.1rem; font-weight:700; color:#fff;">{avg_survival_pct} <span style="font-size:0.74rem; color:#9cc2ff;">%</span></div>
<div style="font-size:0.7rem; color:#06d6a0;">较上月 ↑ 1.6%</div>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # 2.2 选中池塘环境监测卡片
    t_str = f"{latest_wq['water_temp_c']} °C" if latest_wq and latest_wq["water_temp_c"] is not None else "缺失"
    do_str = f"{latest_wq['dissolved_oxygen_mg_l']} mg/L" if latest_wq and latest_wq["dissolved_oxygen_mg_l"] is not None else "缺失"
    ph_str = f"{latest_wq['ph']}" if latest_wq and latest_wq["ph"] is not None else "缺失"
    nh3_str = f"{latest_wq['ammonia_mg_l']} mg/L" if latest_wq and latest_wq["ammonia_mg_l"] is not None else "缺失(待补录)"

    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">环境监测 · {selected_pond['pond_code']}</span>
<span class="tech-card-action">🕒 {latest_wq['recorded_at'][11:16] if latest_wq else '无记录'} <a href="?jump_to=02" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
<div style="background:rgba(4,18,42,0.65); padding:6px 10px; border-radius:4px;">
<div style="font-size:0.74rem; color:#9cc2ff;">🌡️ 水温</div>
<div style="font-size:1.06rem; font-weight:700; color:#00f0ff;">{t_str}</div>
</div>
<div style="background:rgba(4,18,42,0.65); padding:6px 10px; border-radius:4px;">
<div style="font-size:0.74rem; color:#9cc2ff;">🫧 溶解氧</div>
<div style="font-size:1.06rem; font-weight:700; color:#06d6a0;">{do_str}</div>
</div>
<div style="background:rgba(4,18,42,0.65); padding:6px 10px; border-radius:4px;">
<div style="font-size:0.74rem; color:#9cc2ff;">🧪 pH 值</div>
<div style="font-size:1.06rem; font-weight:700; color:#ffb703;">{ph_str}</div>
</div>
<div style="background:rgba(4,18,42,0.65); padding:6px 10px; border-radius:4px;">
<div style="font-size:0.74rem; color:#9cc2ff;">⚗️ 氨氮</div>
<div style="font-size:1.06rem; font-weight:700; color:#ff4d79;">{nh3_str}</div>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    wq_hist = WaterQualityRepository.query_records_df(pond_id=sel_pid)
    fig_env = build_dual_metric_spline_chart(
        wq_hist if not wq_hist.empty else WaterQualityRepository.query_records_df(pond_id=1),
        metric_a="water_temp_c",
        label_a="水温(°C)",
        color_a="#00f0ff",
        metric_b="dissolved_oxygen_mg_l",
        label_b="溶氧(mg/L)",
        color_b="#06d6a0",
        title="",
        height=195,
    )
    st.plotly_chart(fig_env, use_container_width=True)

    # 2.3 预警信息（完整闭合在单个 tech-card 容器内，指标全部中文显示）
    alert_cat = st.radio("预警类别筛选：", ["全部告警", "水质预警", "设备异常"], horizontal=True, label_visibility="collapsed")
    raw_alerts = overview["alerts"]
    if alert_cat == "水质预警":
        disp_alerts = [a for a in raw_alerts if "水质" in a["alert_type"]]
    elif alert_cat == "设备异常":
        disp_alerts = [a for a in raw_alerts if "水质" not in a["alert_type"]]
    else:
        disp_alerts = raw_alerts

    alert_html_items = []
    for a in disp_alerts[:3]:
        cls = "" if a["severity"] in ("CRITICAL", "HIGH") else "warn"
        title_color = "#ff4d79" if cls == "" else "#ffb703"
        target_name = a["pond_name"] or a["equipment_name"] or "园区节点"
        st_label = ALERT_STATUS_LABELS.get(a["status"], a["status"])
        m_cn = get_metric_label_cn(a["metric_name"])
        val_desc = f"实测 {a['metric_value']}{a['unit'] or ''} (阈值 {a['threshold_value']}{a['unit'] or ''})" if a["metric_value"] is not None else a["alert_type"]
        alert_html_items.append(
            f'<div class="alert-strip {cls}"><div><div class="alert-title" style="color:{title_color};">🚨 {target_name} · {m_cn}</div>'
            f'<div class="alert-desc">{val_desc} | 状态: {st_label}</div></div>'
            f'<div class="alert-time">{a["triggered_at"][11:16]}</div></div>'
        )
    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">预警信息 ({alert_cat})</span>
<span class="tech-card-action">阈值监控 <a href="?jump_to=03" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
{"".join(alert_html_items)}
</div>""",
        unsafe_allow_html=True,
    )

# ==================== 右侧数据面板 ====================
with col_right:
    # 2.4 设备管理卡片（优先置顶故障与离线设备，并在右上角配备“查看详情 →”跳转按钮）
    sorted_eq_items = sorted(
        eq_summary["items"],
        key=lambda x: (
            0 if x["status"] == "FAULT" else (1 if x["status"] == "OFFLINE" else 2),
            0 if x.get("pond_id") == sel_pid else 1,
            x["equipment_id"],
        ),
    )
    eq_rows_html = []
    for e in sorted_eq_items[:6]:
        is_ok = e["status"] == "ONLINE"
        st_text = EQUIPMENT_STATUS_LABELS.get(e["status"], e["status"])
        st_color = "#06d6a0" if is_ok else ("#ff3366" if e["status"] == "FAULT" else "#ffb703")
        pond_tag = e["pond_code"] or "公共"
        row_bg = "background:rgba(255,51,102,0.12);" if e["status"] == "FAULT" else ("background:rgba(255,183,3,0.10);" if e["status"] == "OFFLINE" else "")
        eq_rows_html.append(
            f'<tr style="font-size:0.78rem; border-bottom:1px solid rgba(0,212,255,0.08); {row_bg}">'
            f'<td style="text-align:left; padding:4px 2px; color:#fff;">{e["equipment_name"]}</td>'
            f'<td style="text-align:center; color:{st_color}; font-weight:700; white-space:nowrap;">● {st_text}</td>'
            f'<td style="text-align:right; padding-right:2px; color:#9cc2ff; white-space:nowrap;">{pond_tag}</td></tr>'
        )

    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">设备管理</span>
<span class="tech-card-action">在线率 {eq_summary['online_rate_pct']}% <a href="?jump_to=07" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; text-align:center; margin-bottom:6px;">
<div style="background:rgba(4,18,42,0.6); padding:5px 2px; border-radius:4px;">
<div style="font-size:0.72rem; color:#9cc2ff;">设备总数</div>
<div style="font-size:1.05rem; font-weight:700; color:#fff;">{eq_summary['total']}</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:5px 2px; border-radius:4px;">
<div style="font-size:0.72rem; color:#06d6a0;">在线正常</div>
<div style="font-size:1.05rem; font-weight:700; color:#06d6a0;">{eq_summary['online']}</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:5px 2px; border-radius:4px;">
<div style="font-size:0.72rem; color:#ffb703;">离线失联</div>
<div style="font-size:1.05rem; font-weight:700; color:#ffb703;">{eq_summary['offline']}</div>
</div>
<div style="background:rgba(4,18,42,0.6); padding:5px 2px; border-radius:4px;">
<div style="font-size:0.72rem; color:#ff3366;">故障异常</div>
<div style="font-size:1.05rem; font-weight:700; color:#ff3366;">{eq_summary['fault']}</div>
</div>
</div>
<table style="width:100%; border-collapse:collapse;">
<tr style="color:#9cc2ff; font-size:0.74rem; border-bottom:1px solid rgba(0,212,255,0.25);">
<th style="text-align:left; width:48%; padding:3px 0;">设备名称 (异常置顶)</th>
<th style="text-align:center; width:28%; padding:3px 0;">运行状态</th>
<th style="text-align:right; width:24%; padding:3px 0;">关联池位</th>
</tr>
{"".join(eq_rows_html)}
</table>
</div>""",
        unsafe_allow_html=True,
    )

    # 2.5 能耗统计卡片 (完整闭合在单个 tech-card 容器内)
    energy_period = st.radio("能耗统计周期：", ["今日", "本周", "本月"], horizontal=True, index=0, label_visibility="collapsed")
    factor = 1.0 if energy_period == "今日" else (6.8 if energy_period == "本周" else 28.5)
    kwh_val = int(5642 * (factor / 28.5)) if energy_period != "今日" else 5642
    water_val = int(318 * (factor / 28.5)) if energy_period != "今日" else 318
    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">能耗统计 ({energy_period})</span>
<span class="tech-card-action">模拟计量 <a href="?jump_to=06" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
<div style="background:rgba(4,18,42,0.65); padding:6px 10px; border-radius:4px; border-left:3px solid #ffb703;">
<div style="font-size:0.74rem; color:#9cc2ff;">⚡ 用电量 ({energy_period})</div>
<div style="font-size:1.06rem; font-weight:700; color:#fff;">{kwh_val:,} <span style="font-size:0.74rem; color:#ffb703;">kWh</span></div>
</div>
<div style="background:rgba(4,18,42,0.65); padding:6px 10px; border-radius:4px; border-left:3px solid #00bbf9;">
<div style="font-size:0.74rem; color:#9cc2ff;">💧 循环水量 ({energy_period})</div>
<div style="font-size:1.06rem; font-weight:700; color:#fff;">{water_val:,} <span style="font-size:0.74rem; color:#00bbf9;">吨</span></div>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )
    if HAS_PLOTLY:
        e_hours = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
        fig_energy = go.Figure()
        fig_energy.add_trace(go.Scatter(x=e_hours, y=[320, 410, 520, 610, 540, 680], name="用电(kWh)", mode="lines+markers", line=dict(color="#00f0ff", width=2.2, shape="spline"), fill="tozeroy", fillcolor="rgba(0,240,255,0.08)"))
        fig_energy.add_trace(go.Scatter(x=e_hours, y=[180, 240, 290, 350, 280, 390], name="用水(吨)", mode="lines+markers", line=dict(color="#06d6a0", width=2.2, shape="spline"), fill="tozeroy", fillcolor="rgba(6,214,160,0.08)"))
        st.plotly_chart(apply_dark_tech_layout(fig_energy, "", height=180), use_container_width=True)

    # 2.6 养殖信息卡片 (左文右鱼内嵌并排布局，100% 还原 ui/大屏.png 右下角设计)
    fish_img_path = ASSETS_DIR / "images" / "fish_illustration.png"
    b64_fish = base64.b64encode(fish_img_path.read_bytes()).decode("ascii") if fish_img_path.exists() else ""
    if selected_batch:
        sp_name = selected_batch["species_name"]
        b_code = selected_batch["batch_code"]
        bio_kg = f"{selected_batch['estimated_biomass_kg']:,.1f} kg"
        spec_g = f"{selected_batch['latest_avg_weight_g']} g"
        density = round(selected_batch["estimated_biomass_kg"] / max(1.0, float(selected_pond["capacity"])), 2)
        density_str = f"{density} kg/m³"
        feed_status = "● 正常"
    else:
        sp_name = "空闲/尾水维护"
        b_code = "--"
        bio_kg = "0.0 kg"
        spec_g = "--"
        density_str = "0.0 kg/m³"
        feed_status = "⏸️ 待命"

    fish_html = f'<div style="width:42%; text-align:center;"><img src="data:image/png;base64,{b64_fish}" style="width:100%; max-width:145px; border-radius:6px; border:1px solid rgba(0,240,255,0.3);"></div>' if b64_fish else ""

    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">养殖信息 · {selected_pond['pond_code']}</span>
<span class="tech-card-action">{b_code} <a href="?jump_to=04" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<div style="display:flex; align-items:center; justify-content:space-between; gap:10px;">
<div style="width:58%; font-size:0.8rem; line-height:1.75;">
<div style="display:flex; justify-content:space-between;"><span>养殖品种：</span><span style="color:#00f0ff; font-weight:700;">{sp_name[:8]}</span></div>
<div style="display:flex; justify-content:space-between;"><span>当前存量：</span><span style="color:#fff; font-weight:700;">{bio_kg}</span></div>
<div style="display:flex; justify-content:space-between;"><span>平均规格：</span><span style="color:#fff;">{spec_g}</span></div>
<div style="display:flex; justify-content:space-between;"><span>养殖密度：</span><span style="color:#ffb703;">{density_str}</span></div>
<div style="display:flex; justify-content:space-between;"><span>投喂状态：</span><span style="color:#06d6a0;">{feed_status}</span></div>
<div style="display:flex; justify-content:space-between;"><span>下次投喂：</span><span style="color:#9cc2ff;">16:30 (自动估算)</span></div>
</div>
{fish_html}
</div>
</div>""",
        unsafe_allow_html=True,
    )
