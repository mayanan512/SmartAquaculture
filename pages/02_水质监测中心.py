# -*- coding: utf-8 -*-
"""
02 水质监测中心 (V3.4 跨页上下文同步 + 左右等高并排双趋势图 + 预警联动版)
"""

from datetime import datetime
import streamlit as st
import pandas as pd
from config.settings import ASSETS_DIR, SOURCE_LABELS, QUALITY_LABELS, ALERT_STATUS_LABELS, get_metric_label_cn
from components.theme import init_page, render_tech_image
from components.charts import build_dual_metric_spline_chart, build_donut_chart, apply_dark_tech_layout
from repositories.alert_repo import AlertRepository
from repositories.farm_repo import FarmRepository
from repositories.water_quality_repo import WaterQualityRepository
from services.water_quality_service import WaterQualityService

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

init_page("水质监测中心", "水质监测中心")

areas = FarmRepository.list_areas()
area_map = {a["area_id"]: f"{a['area_code']} - {a['area_name']}" for a in areas}
all_ponds = FarmRepository.list_ponds()

# 1. 顶部查询筛选栏（支持承接大屏带入的 selected_pond_id）
sc1, sc2, sc3, sc4 = st.columns([1.2, 1.35, 1.1, 1.0])
with sc1:
    sel_area_id = st.selectbox("养殖区域：", options=[0] + list(area_map.keys()), format_func=lambda aid: "全部养殖区域" if aid == 0 else area_map[aid])
with sc2:
    avail_ponds = [p for p in all_ponds if sel_area_id == 0 or p["area_id"] == sel_area_id]
    pond_map = {p["pond_id"]: f"{p['pond_code']} - {p['pond_name']}" for p in avail_ponds}
    pond_opts = [0] + list(pond_map.keys())
    ctx_pid = st.session_state.get("selected_pond_id", 0)
    default_idx = pond_opts.index(ctx_pid) if ctx_pid in pond_opts else 0
    sel_pid = st.selectbox("养殖池（已同步大屏焦点）：", options=pond_opts, index=default_idx, format_func=lambda x: "当前区域全部水池" if x == 0 else pond_map[x])
    if sel_pid != 0:
        st.session_state["selected_pond_id"] = sel_pid
with sc3:
    src_filter = st.selectbox("数据来源：", options=["ALL", "SIMULATED", "MANUAL", "SENSOR"], format_func=lambda s: "全部数据来源" if s == "ALL" else SOURCE_LABELS.get(s, s))

df_wq = WaterQualityRepository.query_records_df(
    pond_id=None if sel_pid == 0 else sel_pid,
    source_type=None if src_filter == "ALL" else src_filter,
)
if sel_area_id != 0 and sel_pid == 0 and not df_wq.empty:
    allowed_pids = {p["pond_id"] for p in avail_ponds}
    df_wq = df_wq[df_wq["pond_id"].isin(allowed_pids)].reset_index(drop=True)

with sc4:
    st.markdown("<div style=\"height:28px;\"></div>", unsafe_allow_html=True)
    if not df_wq.empty:
        csv_bytes = df_wq.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 导出当前筛选数据 (CSV)", data=csv_bytes, file_name="water_quality_records.csv", mime="text/csv", use_container_width=True)
    else:
        st.button("📥 暂无数据可导出", disabled=True, use_container_width=True)

# 2. 顶部 5 大实时水质卡片 (对标 ui/水质监测.png 顶栏 5 卡结构)
if not df_wq.empty:
    latest = df_wq.iloc[0]
    t_val = f"{latest['water_temp_c']:.1f}" if pd.notna(latest["water_temp_c"]) else "缺失"
    do_val = f"{latest['dissolved_oxygen_mg_l']:.2f}" if pd.notna(latest["dissolved_oxygen_mg_l"]) else "缺失"
    ph_val = f"{latest['ph']:.2f}" if pd.notna(latest["ph"]) else "缺失"
    nh3_val = f"{latest['ammonia_mg_l']:.2f}" if pd.notna(latest["ammonia_mg_l"]) else "缺失(待补录)"
    q_val = QUALITY_LABELS.get(latest["quality_status"], latest["quality_status"])
    pond_label = latest["pond_code"]
    rec_time = latest["recorded_at"]
else:
    t_val, do_val, ph_val, nh3_val, q_val, pond_label, rec_time = "--", "--", "--", "--", "--", "--", "--"

st.markdown(
    f"""<div style="display:grid; grid-template-columns: repeat(5, 1fr); gap:10px; margin-bottom:14px;">
<div class="tech-card" style="margin-bottom:0; border-left:4px solid #00f0ff;">
<div style="display:flex; justify-content:space-between; align-items:center;">
<span style="font-size:0.84rem; color:#9cc2ff;">🌡️ 水温 ({pond_label})</span>
<span style="font-size:0.72rem; color:#06d6a0;">{rec_time[11:16] if len(rec_time)>15 else rec_time}</span>
</div>
<div style="font-size:1.5rem; font-weight:800; color:#fff; margin:4px 0;">{t_val} <span style="font-size:0.82rem; color:#00f0ff;">°C</span></div>
<div style="font-size:0.72rem; color:#9cc2ff;">正常范围 18.0 ~ 30.0°C</div>
</div>
<div class="tech-card" style="margin-bottom:0; border-left:4px solid #06d6a0;">
<div style="display:flex; justify-content:space-between; align-items:center;">
<span style="font-size:0.84rem; color:#9cc2ff;">💧 溶解氧</span>
<span style="font-size:0.72rem; color:#06d6a0;">实时监测</span>
</div>
<div style="font-size:1.5rem; font-weight:800; color:#fff; margin:4px 0;">{do_val} <span style="font-size:0.82rem; color:#06d6a0;">mg/L</span></div>
<div style="font-size:0.72rem; color:#9cc2ff;">正常范围 &ge; 5.0 mg/L</div>
</div>
<div class="tech-card" style="margin-bottom:0; border-left:4px solid #00bbf9;">
<div style="display:flex; justify-content:space-between; align-items:center;">
<span style="font-size:0.84rem; color:#9cc2ff;">🧪 pH 值</span>
<span style="font-size:0.72rem; color:#06d6a0;">酸碱平衡</span>
</div>
<div style="font-size:1.5rem; font-weight:800; color:#fff; margin:4px 0;">{ph_val}</div>
<div style="font-size:0.72rem; color:#9cc2ff;">正常范围 7.0 ~ 8.6</div>
</div>
<div class="tech-card" style="margin-bottom:0; border-left:4px solid #ffb703;">
<div style="display:flex; justify-content:space-between; align-items:center;">
<span style="font-size:0.84rem; color:#9cc2ff;">⚗️ 氨氮</span>
<span style="font-size:0.72rem; color:#ffb703;">毒性监控</span>
</div>
<div style="font-size:1.5rem; font-weight:800; color:#fff; margin:4px 0;">{nh3_val} <span style="font-size:0.82rem; color:#ffb703;">{'' if '缺失' in nh3_val else 'mg/L'}</span></div>
<div style="font-size:0.72rem; color:#9cc2ff;">正常范围 &le; 0.40 mg/L</div>
</div>
<div class="tech-card" style="margin-bottom:0; border-left:4px solid #9d4edd;">
<div style="display:flex; justify-content:space-between; align-items:center;">
<span style="font-size:0.84rem; color:#9cc2ff;">🔬 数据质量状态</span>
<span style="font-size:0.72rem; color:#00f0ff;">完整性核验</span>
</div>
<div style="font-size:1.35rem; font-weight:800; color:#06d6a0; margin:6px 0;">{q_val}</div>
<div style="font-size:0.72rem; color:#9cc2ff;">拒绝将空值当成 0</div>
</div>
</div>""",
    unsafe_allow_html=True,
)

# 3. 中部布局 (左栏: 点位鸟瞰 + 达标环形图 + 水质预警条 | 右栏: 单指标趋势与多指标对比并排 + 历史表格)
mid_left, mid_right = st.columns([1.05, 1.95])

with mid_left:
    park_small_img = ASSETS_DIR / "images" / "park_birds_eye.png"
    if park_small_img.exists():
        render_tech_image(park_small_img, caption="示范园区 A/B/C/D 区水质传感点位分布鸟瞰图")

    if not df_wq.empty:
        over_cnt = int(((df_wq["dissolved_oxygen_mg_l"] < 5.0) | (df_wq["ammonia_mg_l"] > 0.40)).sum())
        miss_cnt = int((df_wq["quality_status"] == "MISSING").sum())
        norm_cnt = max(0, len(df_wq) - over_cnt - miss_cnt)
        pass_rate = round(norm_cnt / len(df_wq) * 100)
    else:
        norm_cnt, over_cnt, miss_cnt, pass_rate = 1, 0, 0, 100

    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">水质状态分布</span></div></div>', unsafe_allow_html=True)
    fig_donut = build_donut_chart(
        labels=["正常达标", "超阈值预警", "指标缺失"],
        values=[norm_cnt, over_cnt, miss_cnt],
        title="",
        center_text=f"{pass_rate}%<br>水质达标率",
        height=195,
    )
    st.plotly_chart(fig_donut, use_container_width=True)

    # 左下：关联水质预警信息卡片（对齐 ui/水质监测.png 左下模块）
    wq_alerts = [a for a in AlertRepository.list_alerts() if "水质" in a["alert_type"]][:3]
    wq_alert_html = []
    for a in wq_alerts:
        cls = "" if a["severity"] in ("CRITICAL", "HIGH") else "warn"
        wq_alert_html.append(
            f'<div class="alert-strip {cls}"><div><div class="alert-title">🚨 {a["pond_name"]} · {get_metric_label_cn(a["metric_name"])}</div>'
            f'<div class="alert-desc">实测 {a["metric_value"]}{a["unit"] or ""} (阈值 {a["threshold_value"]}{a["unit"] or ""})</div></div>'
            f'<div class="alert-time">{ALERT_STATUS_LABELS.get(a["status"], a["status"])}</div></div>'
        )
    st.markdown(
        f"""<div class="tech-card">
<div class="tech-card-header">
<span class="tech-card-title">水质关联预警信息</span>
<span class="tech-card-action">实时同步 <a href="?jump_to=03" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
{"".join(wq_alert_html)}
</div>""",
        unsafe_allow_html=True,
    )

with mid_right:
    # 右上：单指标趋势分析 与 多指标历史趋势 并排双列（100% 还原 ui/水质监测.png 右上并排布局）
    chart_df = df_wq if not df_wq.empty else WaterQualityRepository.query_records_df(pond_id=1)
    sub_c1, sub_c2 = st.columns(2)
    with sub_c1:
        st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">单指标趋势分析</span></div></div>', unsafe_allow_html=True)
        m_choice = st.radio("选择单指标：", ["water_temp_c", "dissolved_oxygen_mg_l", "ph", "ammonia_mg_l"], format_func=lambda k: {"water_temp_c": "🌡️水温", "dissolved_oxygen_mg_l": "💧溶氧", "ph": "🧪pH值", "ammonia_mg_l": "⚗️氨氮"}[k], horizontal=True, label_visibility="collapsed")
        m_color = {"water_temp_c": "#00f0ff", "dissolved_oxygen_mg_l": "#06d6a0", "ph": "#00bbf9", "ammonia_mg_l": "#ffb703"}[m_choice]
        m_lbl = {"water_temp_c": "水温 (°C)", "dissolved_oxygen_mg_l": "溶解氧 (mg/L)", "ph": "pH 值", "ammonia_mg_l": "氨氮 (mg/L)"}[m_choice]
        st.plotly_chart(build_dual_metric_spline_chart(chart_df, m_choice, m_lbl, m_color, m_choice, "趋势包络", m_color, "", height=220), use_container_width=True)

    with sub_c2:
        st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">多指标历史趋势对比</span></div></div>', unsafe_allow_html=True)
        _ = st.radio("多指标维度：", ["ALL4", "DO_NH3"], format_func=lambda k: "📊 四项核心指标同轴" if k == "ALL4" else "💧 溶氧与氨氮对比", horizontal=True, label_visibility="collapsed")
        if HAS_PLOTLY:
            p_df = chart_df.sort_values("recorded_at").tail(10)
            x_t = [str(v)[11:16] if len(str(v))>=16 else str(v) for v in p_df["recorded_at"]]
            fig_m = go.Figure()
            fig_m.add_trace(go.Scatter(x=x_t, y=p_df["water_temp_c"], name="水温", mode="lines+markers", line=dict(color="#00f0ff", width=2)))
            fig_m.add_trace(go.Scatter(x=x_t, y=p_df["ph"], name="pH", mode="lines+markers", line=dict(color="#ffb703", width=2)))
            fig_m.add_trace(go.Scatter(x=x_t, y=p_df["dissolved_oxygen_mg_l"], name="溶氧", mode="lines+markers", line=dict(color="#06d6a0", width=2)))
            fig_m.add_trace(go.Scatter(x=x_t, y=p_df["ammonia_mg_l"], name="氨氮", mode="lines+markers", line=dict(color="#ff3366", width=2)))
            st.plotly_chart(apply_dark_tech_layout(fig_m, "", height=220), use_container_width=True)

    # 右下：历史监测记录表格与手工录入
    st.markdown(f'<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">历史监测记录 (当前筛选共 {len(df_wq)} 条)</span></div></div>', unsafe_allow_html=True)
    tab_records, tab_entry = st.tabs(["📋 历史监测数据表", "➕ 手工录入水质（自动触发预警检查）"])

    with tab_records:
        if not df_wq.empty:
            disp_df = df_wq.copy()
            disp_df["source_type"] = disp_df["source_type"].map(lambda x: SOURCE_LABELS.get(x, x))
            disp_df["quality_status"] = disp_df["quality_status"].map(lambda x: QUALITY_LABELS.get(x, x))
            st.dataframe(
                disp_df.rename(columns={
                    "record_id": "记录ID",
                    "pond_code": "池编号",
                    "pond_name": "养殖池",
                    "recorded_at": "监测时间",
                    "water_temp_c": "水温(°C)",
                    "dissolved_oxygen_mg_l": "溶氧(mg/L)",
                    "ph": "pH值",
                    "ammonia_mg_l": "氨氮(mg/L)",
                    "source_type": "数据来源",
                    "quality_status": "质量状态",
                }),
                use_container_width=True,
                hide_index=True,
                height=250,
            )
        else:
            st.info("当前筛选条件下暂无监测数据。")

    with tab_entry:
        full_pond_map = {p["pond_id"]: f"{p['pond_code']} - {p['pond_name']}" for p in all_ponds}
        with st.form("add_wq_record_v34"):
            c1, c2, c3, c4 = st.columns(4)
            with c1: in_pid = st.selectbox("选择养殖池", options=list(full_pond_map.keys()), format_func=lambda x: full_pond_map[x])
            with c2: in_temp = st.number_input("水温 (°C)", value=26.0, min_value=-5.0, max_value=45.0, step=0.1)
            with c3: in_do = st.number_input("溶解氧 (mg/L)", value=6.2, min_value=0.0, max_value=30.0, step=0.1)
            with c4: in_ph = st.number_input("pH 值", value=7.8, min_value=0.0, max_value=14.0, step=0.1)
            c5, c6 = st.columns(2)
            with c5: in_nh3 = st.number_input("氨氮 (mg/L)", value=0.22, min_value=0.0, max_value=20.0, step=0.02)
            with c6: in_src = st.selectbox("来源标记", options=["MANUAL", "SIMULATED", "SENSOR"], format_func=lambda k: SOURCE_LABELS[k])
            if st.form_submit_button("✅ 提交水质记录并执行预警检查"):
                try:
                    res = WaterQualityService.validate_and_save(in_pid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), in_temp, in_do, in_ph, in_nh3, in_src)
                    st.cache_data.clear()
                    st.success(f"水质记录保存成功（记录ID: {res['record_id']}）！")
                    for al in res["alerts"]:
                        if al["action"] == "CREATED":
                            st.warning(f"🚨 触发预警规则【{al['rule_name']}】，已自动生成告警单 `{al['alert_code']}`！")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败: {e}")
