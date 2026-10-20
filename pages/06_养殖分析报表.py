# -*- coding: utf-8 -*-
"""
06 养殖分析报表 (V3.3 智能级联筛选 + 6大图表100%实时读取数据库动态联动版)
- 选择养殖池后，品种下拉框自动收敛为该池塘匹配的品种，避免选出矛盾空结果
- 6 张统计图表（出塘产量、品种存量占比、各批次成活率对比、成本结构分析、告警与损耗分布、各批次存量vs投喂vs出塘对比）100% 绑定数据库并随筛选实时重绘
"""

import streamlit as st
import pandas as pd
from components.theme import init_page
from components.metrics import render_kpi_card
from components.charts import build_donut_chart, apply_dark_tech_layout
from repositories.alert_repo import AlertRepository
from repositories.production_repo import ProductionRepository
from services.production_service import ProductionService
from services.report_service import ReportService

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

init_page("养殖分析报表", "养殖分析报表")

batches = ProductionService.list_all_batch_metrics()
all_alerts = AlertRepository.list_alerts()

# 1. 智能级联筛选条
fc1, fc2, fc3, fc4 = st.columns([1.35, 1.35, 1.3, 1.0])
with fc1:
    all_ponds_names = sorted(list({b["pond_name"] for b in batches}))
    sel_p = st.selectbox("① 按养殖池筛选：", options=["全部养殖池"] + all_ponds_names, key="rep_sel_p")

pool_batches = [b for b in batches if sel_p == "全部养殖池" or b["pond_name"] == sel_p]

with fc2:
    avail_sp_names = sorted(list({b["species_name"] for b in pool_batches}))
    if st.session_state.get("rep_sel_s") not in (["全部品种"] + avail_sp_names):
        st.session_state["rep_sel_s"] = "全部品种"
    sel_s = st.selectbox("② 按品种筛选（自动联动）：", options=["全部品种"] + avail_sp_names, key="rep_sel_s")

filtered_b = [b for b in pool_batches if sel_s == "全部品种" or b["species_name"] == sel_s]
filtered_batch_ids = {b["batch_id"] for b in filtered_b}
filtered_pond_ids = {b["pond_id"] for b in filtered_b}

with fc3:
    period_mode = st.selectbox("③ 产量汇总粒度：", options=["day", "week", "month"], format_func=lambda x: {"day": "按日汇总出塘", "week": "按周汇总出塘", "month": "按月汇总出塘"}[x])

with fc4:
    st.markdown("<div style=\"height:28px;\"></div>", unsafe_allow_html=True)
    if filtered_b:
        export_df = pd.DataFrame([
            {
                "批次编号": b["batch_code"],
                "养殖池": b["pond_name"],
                "养殖品种": b["species_name"],
                "初始放养数": b["initial_count"],
                "累计死亡数": b["total_dead"],
                "当前存活数": b["current_alive_count"],
                "在池成活率(%)": b["survival_rate_pct"],
                "综合成活率(%)": b["biological_survival_rate_pct"],
                "估算在池存量(kg)": b["estimated_biomass_kg"],
                "累计出塘产量(kg)": b["harvested_weight_kg"],
                "累计饲料消耗(kg)": b["total_feed_kg"],
                "饲料成本(元)": b["total_feed_cost_cny"],
                "其他成本(元)": b["other_cost_cny"],
                "总成本(元)": b["total_cost_cny"],
                "出塘销售收入(元)": b["harvest_revenue_cny"],
            }
            for b in filtered_b
        ])
        csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 导出当前报表 (CSV)", data=csv_bytes, file_name="aquaculture_analysis_report.csv", mime="text/csv", use_container_width=True)

# 2. 顶部 4 大核心经营 KPI 卡片 (100% 响应筛选结果)
disp_harvest_kg = sum(b["harvested_weight_kg"] for b in filtered_b)
disp_revenue = sum(b["harvest_revenue_cny"] for b in filtered_b)
disp_biomass_kg = sum(b["estimated_biomass_kg"] for b in filtered_b)
disp_cost = sum(b["total_cost_cny"] for b in filtered_b)
disp_surv = round(sum(b["biological_survival_rate_pct"] for b in filtered_b) / len(filtered_b), 1) if filtered_b else 0.0

rk1, rk2, rk3, rk4 = st.columns(4)
with rk1:
    render_kpi_card("累计出塘产量", f"{disp_harvest_kg:,.1f}", "kg", f"销售收入 ¥{disp_revenue:,.0f}", "up", "🐟", "#00f0ff")
with rk2:
    render_kpi_card("综合生物学成活率", f"{disp_surv:.1f}", "%", f"涵盖 {len(filtered_b)} 个筛选批次", "up", "📈", "#06d6a0")
with rk3:
    render_kpi_card("当前在池估算存量", f"{disp_biomass_kg:,.1f}", "kg", "按最新生长抽样复算", "up", "⚖️", "#00bbf9")
with rk4:
    render_kpi_card("养殖累计总成本", f"{disp_cost:,.0f}", "元", "含饲料 + 苗种 + 能耗 + 动保", "down", "💰", "#ffb703")

st.write("")

# 3. 第一图表行：真实出塘产量与销售额趋势 + 品种在池存量占比环形图 + 各批次成活率对比
c1, c2, c3 = st.columns([1.3, 1.1, 1.3])

with c1:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">分批出塘产量与营收统计</span></div></div>', unsafe_allow_html=True)
    if HAS_PLOTLY:
        harvests = [h for h in ProductionRepository.list_harvest_records() if h["batch_id"] in filtered_batch_ids]
        fig_prod = go.Figure()
        if harvests:
            h_sorted = sorted(harvests, key=lambda x: x["harvested_at"])
            x_labels = [f"{h['harvested_at'][:10]} ({h['pond_name'][:3]})" for h in h_sorted]
            fig_prod.add_trace(go.Bar(x=x_labels, y=[h["total_weight_kg"] for h in h_sorted], name="出塘重量 (kg)", marker=dict(color="#00f0ff")))
            fig_prod.add_trace(go.Scatter(x=x_labels, y=[h["total_amount_cny"] / 10.0 for h in h_sorted], name="销售额 (×10元)", mode="lines+markers", line=dict(color="#06d6a0", width=2.5)))
        else:
            fig_prod.add_trace(go.Bar(x=[b["pond_name"][:6] for b in filtered_b], y=[b["estimated_biomass_kg"] for b in filtered_b], name="待出塘估算存量 (kg)", marker=dict(color="#00bbf9")))
        st.plotly_chart(apply_dark_tech_layout(fig_prod, "", height=230), use_container_width=True)

with c2:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">各品种在池估算存量占比</span></div></div>', unsafe_allow_html=True)
    donut_labels = [b["species_name"] for b in filtered_b] if filtered_b else ["暂无匹配"]
    donut_vals = [max(0.1, b["estimated_biomass_kg"]) for b in filtered_b] if filtered_b else [1]
    fig_sp_donut = build_donut_chart(
        labels=donut_labels,
        values=donut_vals,
        title="",
        center_text=f"{disp_biomass_kg:,.0f}<br>kg存量",
        height=230,
    )
    st.plotly_chart(fig_sp_donut, use_container_width=True)

with c3:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">各批次在池留存率与综合成活率</span></div></div>', unsafe_allow_html=True)
    if HAS_PLOTLY and filtered_b:
        b_names = [b["pond_name"][:6] for b in filtered_b]
        fig_surv = go.Figure()
        fig_surv.add_trace(go.Bar(x=b_names, y=[b["biological_survival_rate_pct"] for b in filtered_b], name="综合成活率 (%)", marker=dict(color="#06d6a0")))
        fig_surv.add_trace(go.Scatter(x=b_names, y=[b["survival_rate_pct"] for b in filtered_b], name="当前在池留存率 (%)", mode="lines+markers", line=dict(color="#00f0ff", width=2.5)))
        fig_surv.update_yaxes(range=[70, 102])
        st.plotly_chart(apply_dark_tech_layout(fig_surv, "", height=230), use_container_width=True)

# 4. 第二图表行：真实成本分类构成 + 告警与损耗分布 + 各批次存量/投喂/出塘三柱对比
r2_c1, r2_c2, r2_c3 = st.columns([1.3, 1.1, 1.3])

with r2_c1:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">筛选批次养殖成本结构 (元)</span></div></div>', unsafe_allow_html=True)
    if HAS_PLOTLY:
        feed_cost_sum = round(sum(b["total_feed_cost_cny"] for b in filtered_b), 2)
        cost_rows = [c for c in ProductionRepository.list_cost_records() if c["batch_id"] in filtered_batch_ids]
        cat_map: dict = {"饲料投入": feed_cost_sum}
        for c in cost_rows:
            cat = c["cost_category"]
            cat_map[cat] = round(cat_map.get(cat, 0.0) + float(c["amount_cny"]), 2)
        fig_cost = go.Figure(data=[go.Bar(
            x=list(cat_map.keys()),
            y=list(cat_map.values()),
            marker=dict(color=["#00f0ff", "#00b4d8", "#ffb703", "#06d6a0", "#9d4edd"][:len(cat_map)]),
            text=[f"¥{v:,.0f}" for v in cat_map.values()],
            textposition="auto",
        )])
        st.plotly_chart(apply_dark_tech_layout(fig_cost, "", height=230), use_container_width=True)

with r2_c2:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">筛选池塘告警类型统计</span></div></div>', unsafe_allow_html=True)
    pond_alerts = [a for a in all_alerts if a.get("pond_id") in filtered_pond_ids]
    al_map: dict = {}
    for a in pond_alerts:
        k = a["alert_type"]
        al_map[k] = al_map.get(k, 0) + 1
    fig_abnormal = build_donut_chart(
        labels=list(al_map.keys()) if al_map else ["运行正常无告警"],
        values=list(al_map.values()) if al_map else [1],
        title="",
        center_text=f"{len(pond_alerts)}<br>关联告警",
        height=230,
    )
    st.plotly_chart(fig_abnormal, use_container_width=True)

with r2_c3:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">存量 vs 累计投喂 vs 已出塘 (kg)</span></div></div>', unsafe_allow_html=True)
    if HAS_PLOTLY and filtered_b:
        b_labels = [b["pond_name"][:6] for b in filtered_b]
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=b_labels, y=[b["estimated_biomass_kg"] for b in filtered_b], name="在池存量", marker=dict(color="#00f0ff")))
        fig_bar.add_trace(go.Bar(x=b_labels, y=[b["total_feed_kg"] for b in filtered_b], name="累计投喂", marker=dict(color="#ffb703")))
        fig_bar.add_trace(go.Bar(x=b_labels, y=[b["harvested_weight_kg"] for b in filtered_b], name="已出塘量", marker=dict(color="#06d6a0")))
        fig_bar.update_layout(barmode="group")
        st.plotly_chart(apply_dark_tech_layout(fig_bar, "", height=230), use_container_width=True)

# 5. 底部：报表记录全景表格
st.markdown(f'<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">养殖综合分析报表台账 (当前展示 {len(filtered_b)} 个批次)</span></div></div>', unsafe_allow_html=True)
if filtered_b:
    batch_df = pd.DataFrame([
        {
            "序号": i + 1,
            "批次编号": b["batch_code"],
            "养殖池": b["pond_name"],
            "养殖品种": b["species_name"],
            "初始放养(尾/只)": f"{b['initial_count']:,}",
            "当前存活(尾/只)": f"{b['current_alive_count']:,}",
            "在池成活率(%)": f"{b['survival_rate_pct']:.1f}%",
            "综合成活率(%)": f"{b['biological_survival_rate_pct']:.1f}%",
            "当前估算存量(kg)": f"{b['estimated_biomass_kg']:,.1f}",
            "累计出塘产量(kg)": f"{b['harvested_weight_kg']:,.1f}",
            "累计投喂(kg)": f"{b['total_feed_kg']:,.1f}",
            "饲料成本(元)": f"¥{b['total_feed_cost_cny']:,.0f}",
            "其他成本(元)": f"¥{b['other_cost_cny']:,.0f}",
            "养殖总成本(元)": f"¥{b['total_cost_cny']:,.0f}",
            "出塘销售收入(元)": f"¥{b['harvest_revenue_cny']:,.0f}",
        }
        for i, b in enumerate(filtered_b)
    ])
    st.dataframe(batch_df, use_container_width=True, hide_index=True)
