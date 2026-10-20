# -*- coding: utf-8 -*-
"""
智渔云 —— 智慧养殖数字孪生管理平台 主入口 (app.py V3.9 像素级等高对齐与零重叠版)
"""

from datetime import datetime
import random
import pandas as pd
import streamlit as st
from config.settings import ASSETS_DIR, POND_STATUS_LABELS, ALERT_STATUS_LABELS, SEVERITY_LABELS, EQUIPMENT_STATUS_LABELS, get_metric_label_cn
from components.theme import init_page, render_tech_image
from components.metrics import render_kpi_card
from components.charts import (
    apply_dark_tech_layout,
    build_3d_digital_twin_scene,
    build_batch_comparison_bar,
    build_donut_chart,
    build_dual_metric_spline_chart,
    build_multi_pond_wq_chart,
)
from repositories.water_quality_repo import WaterQualityRepository
from services.report_service import ReportService
from services.water_quality_service import WaterQualityService

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

init_page("智慧养殖数字孪生管理平台", "智慧养殖总览")

overview = ReportService.get_dashboard_overview()
active_batches = overview["active_batches"]
all_batches = overview["all_batch_metrics"]
alerts = overview["alerts"]
eq_summary = overview["equipment_summary"]
all_wq_df = WaterQualityRepository.query_records_df()
latest_all_wq = WaterQualityRepository.get_latest_all_ponds()

# ==================== 1. 顶部 6 大核心经营与监控 KPI 卡片 (固定 104px 等高，绝不折行) ====================
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    render_kpi_card("在养/总池数", f"{overview['in_use_ponds']}/{overview['total_ponds']}", "池", "循环水+生态塘", "up", "🌊", "#00f0ff")
with c2:
    render_kpi_card("当前在养批次", f"{overview['active_batches_count']}", "批", "鱼虾蟹协同在养", "up", "🐟", "#06d6a0")
with c3:
    render_kpi_card("在池估算存量", f"{overview['total_estimated_biomass_kg']:,.0f}", "kg", "按最新抽样复算", "up", "⚖️", "#00bbf9")
with c4:
    render_kpi_card("累计出塘产量", f"{overview['total_harvested_kg']:,.0f}", "kg", f"营收 ¥{overview['total_harvest_revenue_cny']:,.0f}", "up", "🚚", "#06d6a0")
with c5:
    alert_cnt = overview["unhandled_alerts_count"]
    render_kpi_card("未处理告警", f"{alert_cnt}", "条", f"累计告警 {len(alerts)} 条", "alert" if alert_cnt > 0 else "down", "🚨", "#ff3366" if alert_cnt > 0 else "#06d6a0")
with c6:
    render_kpi_card("设备在线率", f"{overview['equipment_online_rate_pct']}", "%", f"在线 {eq_summary['online']}/{eq_summary['total']} 台", "up", "📡", "#ffb703")

st.write("")

# ==================== 2. 首页核心三栏图表与数字孪生驾驶舱 ====================
col_left, col_center, col_right = st.columns([1.22, 1.56, 1.22])

# -------------------- 左栏：水质变化趋势曲线 + 批次存量柱状图 --------------------
with col_left:
    st.markdown(
        """<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">📈 水质变化趋势曲线</span>
<span class="tech-card-action">24h监测 <a href="?jump_to=02" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
</div>""",
        unsafe_allow_html=True,
    )
    wq_view_mode = st.radio(
        "水质曲线模式：",
        options=["MULTI_DO", "MULTI_NH3", "SINGLE_COUPLED"],
        format_func=lambda m: "💧 溶氧对比" if m == "MULTI_DO" else ("⚗️ 氨氮对比" if m == "MULTI_NH3" else "🌡️ 温氧耦合"),
        horizontal=True,
        label_visibility="collapsed",
    )
    if wq_view_mode == "MULTI_DO":
        fig_wq = build_multi_pond_wq_chart(all_wq_df, "dissolved_oxygen_mg_l", "溶解氧(mg/L)", threshold_val=5.0, height=240)
    elif wq_view_mode == "MULTI_NH3":
        fig_wq = build_multi_pond_wq_chart(all_wq_df, "ammonia_mg_l", "氨氮(mg/L)", threshold_val=0.40, height=240)
    else:
        focus_pid = st.session_state.get("selected_pond_id", 1)
        focus_df = WaterQualityRepository.query_records_df(pond_id=focus_pid)
        fig_wq = build_dual_metric_spline_chart(
            focus_df if not focus_df.empty else all_wq_df,
            metric_a="water_temp_c",
            label_a="水温(°C)",
            color_a="#00f0ff",
            metric_b="dissolved_oxygen_mg_l",
            label_b="溶氧(mg/L)",
            color_b="#06d6a0",
            title="",
            height=240,
        )
    st.plotly_chart(fig_wq, use_container_width=True)

    # 左下：在养批次存量 vs 投喂 vs 出塘对比柱状图
    st.markdown(
        """<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">📊 批次存量、投喂与出塘对比</span>
<span class="tech-card-action">生产核算 <a href="?jump_to=04" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
</div>""",
        unsafe_allow_html=True,
    )
    fig_batch_bar = build_batch_comparison_bar(active_batches, height=240)
    st.plotly_chart(fig_batch_bar, use_container_width=True)

# -------------------- 中栏：3D 数字孪生园区全景 + 池塘水质健康矩阵 --------------------
with col_center:
    st.markdown(
        """<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">🗺️ 数字孪生园区态势中枢</span>
<span class="tech-card-action">🟢 点位联动 <a href="?jump_to=01" target="_self" class="card-jump-btn">全屏总览 →</a></span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # 第一行：池塘选择下拉框 + 模拟采集按钮（均无顶置标签，像素级水平对齐且不截断文字）
    m_col1, m_col2 = st.columns([1.85, 1.0])
    with m_col1:
        pond_options = {p["pond_id"]: f"🎯 {p['pond_code']} · {p['pond_name']}" for p in overview["ponds"]}
        cur_pid = st.session_state.get("selected_pond_id", overview["ponds"][0]["pond_id"])
        if cur_pid not in pond_options:
            cur_pid = overview["ponds"][0]["pond_id"]
        sel_pid = st.selectbox(
            "聚焦池塘：",
            options=list(pond_options.keys()),
            format_func=lambda pid: pond_options[pid],
            index=list(pond_options.keys()).index(cur_pid),
            label_visibility="collapsed",
        )
        st.session_state["selected_pond_id"] = sel_pid
    with m_col2:
        if st.button("⚡ 模拟实时采集", use_container_width=True, help="为当前聚焦池塘生成一条最新水质记录并自动执行预警检查"):
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

    # 第二行：全宽水平铺开 3D/2D 场景模式切换单选框，彻底告别竖排折行
    home_scene = st.radio(
        "渲染视图：",
        options=["3D_RENDER", "3D_SCENE", "2D_MAP"],
        format_func=lambda m: "🏢 3D园区实景" if m == "3D_RENDER" else ("🧊 3D水体剖面" if m == "3D_SCENE" else "🗺️ 2D平面拓扑"),
        horizontal=True,
        label_visibility="collapsed",
    )

    park_img = ASSETS_DIR / "images" / "park_3d_render.png"
    if home_scene == "3D_RENDER" and park_img.exists():
        render_tech_image(park_img, caption="智渔云数字孪生示范园区三维实景总览 (A/B/C/D区循环水车间与控制中心)", max_height_px=295)
    elif home_scene == "3D_SCENE":
        fig_3d = build_3d_digital_twin_scene(overview["ponds"], latest_all_wq, active_batches, alerts, selected_pond_id=sel_pid)
        st.plotly_chart(fig_3d, use_container_width=True)
    else:
        svg_p = ASSETS_DIR / "images" / "park_map.svg"
        if svg_p.exists():
            render_tech_image(svg_p, caption="智渔云数字孪生示范园区 2D 矢量平面拓扑", max_height_px=295)

    # 中下：全园区池塘实时水质与批次健康矩阵表
    wq_by_pid = {w["pond_id"]: w for w in latest_all_wq}
    matrix_rows = []
    for p in overview["ponds"][:4]:
        w = wq_by_pid.get(p["pond_id"], {})
        do_v = w.get("dissolved_oxygen_mg_l")
        nh3_v = w.get("ammonia_mg_l")
        t_v = w.get("water_temp_c")
        is_warn = (do_v is not None and do_v < 5.0) or (nh3_v is not None and nh3_v > 0.40)
        st_color = "#ff3366" if is_warn else "#06d6a0"
        st_txt = "● 预警" if is_warn else "● 正常"
        nh3_txt = f"{nh3_v:.2f}" if nh3_v is not None else "缺失"
        matrix_rows.append(
            f'<tr style="font-size:0.8rem; border-bottom:1px solid rgba(0,212,255,0.1);">'
            f'<td style="padding:5px 0; color:#00f0ff; font-weight:700;">{p["pond_code"]}</td>'
            f'<td style="padding:5px 0; color:#fff;">{p.get("active_species_name") or "空闲"}</td>'
            f'<td style="text-align:center; color:#9cc2ff;">{t_v if t_v is not None else "--"}°C</td>'
            f'<td style="text-align:center; color:{st_color}; font-weight:700;">{do_v if do_v is not None else "--"} mg/L</td>'
            f'<td style="text-align:center; color:#ffb703;">{nh3_txt}</td>'
            f'<td style="text-align:right; color:{st_color}; font-weight:700;">{st_txt}</td></tr>'
        )
    st.markdown(
        f"""<div class="tech-card notranslate" translate="no" style="margin-top:4px;">
<div class="tech-card-header">
<span class="tech-card-title">🏞️ 在养池塘实时水质矩阵</span>
<span class="tech-card-action">缺失透明标注 <a href="?jump_to=02" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<table style="width:100%; border-collapse:collapse;">
<tr style="color:#9cc2ff; font-size:0.75rem; border-bottom:1px solid rgba(0,212,255,0.25);">
<th style="text-align:left; padding:3px 0;">池编号</th>
<th style="text-align:left; padding:3px 0;">在养品种</th>
<th style="text-align:center; padding:3px 0;">水温</th>
<th style="text-align:center; padding:3px 0;">溶解氧</th>
<th style="text-align:center; padding:3px 0;">氨氮</th>
<th style="text-align:right; padding:3px 0;">状态</th>
</tr>
{"".join(matrix_rows)}
</table>
</div>""",
        unsafe_allow_html=True,
    )

# -------------------- 右栏：告警分布图表 + 实时告警卡片 + 设备管理速览 --------------------
with col_right:
    st.markdown(
        """<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">🚨 告警分布统计图表</span>
<span class="tech-card-action">风险透视 <a href="?jump_to=03" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
</div>""",
        unsafe_allow_html=True,
    )
    alert_chart_mode = st.radio(
        "告警图表切换：",
        options=["STATUS_DONUT", "TYPE_DONUT", "SEV_BAR"],
        format_func=lambda m: "🍩 状态占比" if m == "STATUS_DONUT" else ("📊 类型占比" if m == "TYPE_DONUT" else "📶 等级分布"),
        horizontal=True,
        label_visibility="collapsed",
    )

    if alert_chart_mode == "STATUS_DONUT":
        st_map: dict = {}
        for a in alerts:
            lbl = ALERT_STATUS_LABELS.get(a["status"], a["status"])
            st_map[lbl] = st_map.get(lbl, 0) + 1
        fig_al = build_donut_chart(
            labels=list(st_map.keys()) if st_map else ["无告警"],
            values=list(st_map.values()) if st_map else [1],
            title="",
            center_text=f"{len(alerts)}条<br>总告警",
            height=225,
        )
        st.plotly_chart(fig_al, use_container_width=True)
    elif alert_chart_mode == "TYPE_DONUT":
        tp_map: dict = {}
        for a in alerts:
            tp = a["alert_type"]
            tp_map[tp] = tp_map.get(tp, 0) + 1
        fig_al = build_donut_chart(
            labels=list(tp_map.keys()) if tp_map else ["无告警"],
            values=list(tp_map.values()) if tp_map else [1],
            title="",
            center_text=f"{alert_cnt}条<br>待处理",
            height=225,
        )
        st.plotly_chart(fig_al, use_container_width=True)
    else:
        if HAS_PLOTLY:
            sev_keys = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            sev_lbls = [SEVERITY_LABELS[k] for k in sev_keys]
            sev_cnts = [sum(1 for a in alerts if a["severity"] == k) for k in sev_keys]
            fig_sev = go.Figure(data=[go.Bar(
                x=sev_lbls,
                y=sev_cnts,
                name="告警数",
                marker=dict(color=["#ff3366", "#fb8500", "#ffb703", "#00bbf9"]),
                text=sev_cnts,
                textposition="auto",
            )])
            st.plotly_chart(apply_dark_tech_layout(fig_sev, "", height=225), use_container_width=True)

    # 右下：最新实时预警推送 + 设备管理速览
    alert_strips_html = []
    for a in alerts[:3]:
        cls = "" if a["severity"] in ("CRITICAL", "HIGH") else "warn"
        t_color = "#ff4d79" if cls == "" else "#ffb703"
        st_lbl = ALERT_STATUS_LABELS.get(a["status"], a["status"])
        target_name = a["pond_name"] or a["equipment_name"] or "园区节点"
        val_desc = f"实测 {a['metric_value']}{a['unit'] or ''} (阈值 {a['threshold_value']}{a['unit'] or ''})" if a["metric_value"] is not None else a["alert_type"]
        alert_strips_html.append(
            f'<div class="alert-strip {cls}"><div><div class="alert-title" style="color:{t_color};">🚨 {target_name} · {get_metric_label_cn(a["metric_name"])}</div>'
            f'<div class="alert-desc">{val_desc} | 状态: {st_lbl}</div></div>'
            f'<div class="alert-time">{a["triggered_at"][11:16]}</div></div>'
        )
    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">🔔 最新告警实时跟踪</span>
<span class="tech-card-action">待处理 {alert_cnt} 条 <a href="?jump_to=03" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
{"".join(alert_strips_html)}
</div>""",
        unsafe_allow_html=True,
    )

    # 设备管理快捷概览卡片（带右上角查看详情跳转）
    st.markdown(
        f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">⚙️ 设备运行与巡检状态</span>
<span class="tech-card-action">在线率 {eq_summary['online_rate_pct']}% <a href="?jump_to=07" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#eaf4ff;">
<span>总设备: <b>{eq_summary['total']}</b> 台</span>
<span style="color:#06d6a0;">● 在线: <b>{eq_summary['online']}</b></span>
<span style="color:#ffb703;">● 离线: <b>{eq_summary['offline']}</b></span>
<span style="color:#ff3366;">● 故障: <b>{eq_summary['fault']}</b></span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

# ==================== 3. 底部：九大业务功能模块矩阵与折叠式架构说明 ====================
st.write("")
st.markdown('<div class="tech-card notranslate" translate="no"><div class="tech-card-header"><span class="tech-card-title">🧭 九大核心功能模块快速矩阵</span><span class="tech-card-action">点击卡片进入对应专题子系统</span></div></div>', unsafe_allow_html=True)

nav_c1, nav_c2, nav_c3 = st.columns(3)
with nav_c1:
    st.page_link("pages/01_智慧养殖总览.py", label="🖥️ 01 智慧养殖总览大屏 (3D园区/能耗/设备全景)", use_container_width=True)
    st.page_link("pages/04_养殖生产管理.py", label="🐟 04 养殖生产管理 (批次/投喂/抽样/死亡/出塘/成本)", use_container_width=True)
    st.page_link("pages/07_养殖场与设备管理.py", label="⚙️ 07 养殖场与设备管理 (传感设备/池塘/品种标准)", use_container_width=True)
with nav_c2:
    st.page_link("pages/02_水质监测中心.py", label="💧 02 水质监测中心 (多维过滤/单多指标曲线/CSV导出)", use_container_width=True)
    st.page_link("pages/05_AI智能决策.py", label="🤖 05 AI智能决策辅助 (全息脑图/孤立森林多维算法/四维诊断)", use_container_width=True)
    st.page_link("pages/08_数据管理中心.py", label="📂 08 数据管理中心 (CSV批量导入校验/模板/演示重置)", use_container_width=True)
with nav_c3:
    st.page_link("pages/03_智能预警中心.py", label="🚨 03 智能预警中心 (阈值告警/重复抑制/复测闭环/人工登记)", use_container_width=True)
    st.page_link("pages/06_养殖分析报表.py", label="📊 06 养殖分析报表 (级联筛选/六大动态图表/效益核算)", use_container_width=True)
    st.page_link("pages/09_系统设置.py", label="🛠️ 09 系统设置 (预警规则配置/全局参数修改/审计日志)", use_container_width=True)

with st.expander("📖 查看平台业务闭环逻辑与数据真实性规范说明"):
    st.markdown(
        """<div style="font-size:0.86rem; line-height:1.8; color:#c9e6ff;">
<b>1. 端到端业务闭环</b>：基础档案建档 → 养殖批次放养 → 水质录入/导入自动触发阈值预警 → 预警确认、处置与复测归档 → 日常投喂/生长/死亡/出塘/成本登记 → AI 多源融合辅助决策与报表复算。<br>
<b>2. 数据真实性与缺失值准则</b>：严格区分 <code>模拟演示数据</code>、<code>人工录入数据</code>与<code>传感器实时采集</code>；未采集指标显式标注为“缺失”，绝不静默替换为 0。
</div>""",
        unsafe_allow_html=True,
    )
