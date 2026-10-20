# -*- coding: utf-8 -*-
"""
07 养殖场与设备管理 (V3.7 旗舰完善版)
- 首标签页直达【📡 传感与增氧设备管理】，完美承接大屏“设备管理 -> 查看详情”跳转
- 支持按养殖池、运行状态（故障异常/离线失联/在线正常）、设备类型多维筛选与一键重置
- 新增设备状态分布环形图与设备类型统计柱状图
- 设备状态修改自动联动告警闭环（故障修复上线自动将对应设备告警标记为【已解决】；新标记故障自动触发异常告警）
- 完整展示【设备状态变更与巡检历史记录】与【新增传感/控制设备建档】
"""

from datetime import datetime
import pandas as pd
import streamlit as st
from config.settings import POND_STATUS_LABELS, EQUIPMENT_STATUS_LABELS, SOURCE_LABELS
from components.theme import init_page
from components.metrics import render_kpi_card
from components.charts import build_donut_chart, apply_dark_tech_layout
from repositories.farm_repo import FarmRepository
from repositories.equipment_repo import EquipmentRepository
from services.equipment_service import EquipmentService

try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

init_page("养殖场与设备管理", "养殖场与设备管理")

ponds = FarmRepository.list_ponds()
species = FarmRepository.list_species()
eq_summary = EquipmentService.get_equipment_summary()

# 1. 顶部 4 大核心 KPI 卡片
k1, k2, k3, k4 = st.columns(4)
with k1:
    render_kpi_card("物联设备总数", f"{eq_summary['total']}", "台", f"在线 {eq_summary['online']} | 异常 {eq_summary['fault'] + eq_summary['offline']}", "up", "📡", "#00f0ff")
with k2:
    render_kpi_card("设备实时在线率", f"{eq_summary['online_rate_pct']}", "%", f"故障 {eq_summary['fault']} | 离线 {eq_summary['offline']}", "alert" if eq_summary["fault"] > 0 else "up", "⚡", "#ffb703" if eq_summary["fault"] > 0 else "#06d6a0")
with k3:
    render_kpi_card("园区养殖池数", f"{len(ponds)}", "池", f"在养运行 {sum(1 for p in ponds if p['status']=='IN_USE')} 池", "up", "🏞️", "#00bbf9")
with k4:
    render_kpi_card("建档养殖品种", f"{len(species)}", "种", "鱼虾蟹水质标准库", "up", "🐟", "#06d6a0")

st.write("")

# 2. 三大管理标签页（将【📡 传感与增氧设备管理】置为首标签页，方便从大屏“设备管理 -> 查看详情”直达）
t_equip, t_pond, t_species = st.tabs([
    "📡 传感与增氧设备管理",
    "🏞️ 养殖池与区域档案",
    "🐟 养殖品种与适宜水质参数",
])

with t_equip:
    if st.session_state.get("_reset_eq_filters"):
        st.session_state["eq_filter_pond"] = "ALL"
        st.session_state["eq_filter_status"] = "ALL"
        st.session_state["eq_filter_type"] = "ALL"
        st.session_state["_reset_eq_filters"] = False

    all_items = eq_summary["items"]

    # 2.1 多维筛选栏
    fc1, fc2, fc3, fc4 = st.columns([1.3, 1.2, 1.2, 0.9])
    with fc1:
        pond_opts = ["ALL"] + [p["pond_name"] for p in ponds]
        sel_eq_pond = st.selectbox("① 按关联养殖池筛选：", options=pond_opts, format_func=lambda x: "全部养殖池" if x == "ALL" else x, key="eq_filter_pond")
    with fc2:
        st_opts = ["ALL", "FAULT", "OFFLINE", "ONLINE"]
        sel_eq_st = st.selectbox("② 按运行状态筛选：", options=st_opts, format_func=lambda x: "全部状态 (异常置顶)" if x == "ALL" else EQUIPMENT_STATUS_LABELS.get(x, x), key="eq_filter_status")
    with fc3:
        type_opts = ["ALL"] + sorted(list({e["equipment_type"] for e in all_items}))
        sel_eq_type = st.selectbox("③ 按设备类型筛选：", options=type_opts, format_func=lambda x: "全部设备类型" if x == "ALL" else x, key="eq_filter_type")
    with fc4:
        st.markdown("<div style=\"height:28px;\"></div>", unsafe_allow_html=True)
        if st.button("🔄 重置设备筛选", use_container_width=True):
            st.session_state["_reset_eq_filters"] = True
            st.rerun()

    filtered_items = [
        e for e in all_items
        if (sel_eq_pond == "ALL" or e.get("pond_name") == sel_eq_pond)
        and (sel_eq_st == "ALL" or e["status"] == sel_eq_st)
        and (sel_eq_type == "ALL" or e["equipment_type"] == sel_eq_type)
    ]

    # 2.2 设备状态分布图 + 设备类型柱状图 + 实时异常提醒
    ch_col1, ch_col2, ch_col3 = st.columns([1.15, 1.35, 1.2])
    with ch_col1:
        st.markdown('<div class="tech-card notranslate" translate="no"><div class="tech-card-header"><span class="tech-card-title">设备运行状态占比</span></div></div>', unsafe_allow_html=True)
        fig_eq_donut = build_donut_chart(
            labels=["在线正常", "离线失联", "故障异常"],
            values=[eq_summary["online"], eq_summary["offline"], eq_summary["fault"]],
            title="",
            center_text=f"{eq_summary['online_rate_pct']}%<br>设备在线率",
            height=210,
        )
        st.plotly_chart(fig_eq_donut, use_container_width=True)

    with ch_col2:
        st.markdown('<div class="tech-card notranslate" translate="no"><div class="tech-card-header"><span class="tech-card-title">各类型设备在线与异常分布</span></div></div>', unsafe_allow_html=True)
        if HAS_PLOTLY:
            eq_types = sorted(list({e["equipment_type"] for e in all_items}))
            online_by_t = [sum(1 for e in all_items if e["equipment_type"] == t and e["status"] == "ONLINE") for t in eq_types]
            abn_by_t = [sum(1 for e in all_items if e["equipment_type"] == t and e["status"] != "ONLINE") for t in eq_types]
            fig_eq_bar = go.Figure()
            fig_eq_bar.add_trace(go.Bar(x=eq_types, y=online_by_t, name="在线正常", marker=dict(color="#06d6a0")))
            fig_eq_bar.add_trace(go.Bar(x=eq_types, y=abn_by_t, name="故障/离线", marker=dict(color="#ff3366")))
            fig_eq_bar.update_layout(barmode="stack")
            st.plotly_chart(apply_dark_tech_layout(fig_eq_bar, "", height=210), use_container_width=True)

    with ch_col3:
        abn_devices = [e for e in all_items if e["status"] != "ONLINE"]
        abn_strips = []
        for e in abn_devices:
            cls = "" if e["status"] == "FAULT" else "warn"
            t_col = "#ff3366" if e["status"] == "FAULT" else "#ffb703"
            st_lbl = EQUIPMENT_STATUS_LABELS.get(e["status"], e["status"])
            abn_strips.append(
                f'<div class="alert-strip {cls}"><div><div class="alert-title" style="color:{t_col};">⚙️ {e["equipment_name"]} ({e["equipment_code"]})</div>'
                f'<div class="alert-desc">位置: {e["pond_name"] or "公共"} · {e["install_location"]} | 状态: {st_lbl}</div></div>'
                f'<div class="alert-time">{e["last_reported_at"][11:16] if e.get("last_reported_at") else "--"}</div></div>'
            )
        if not abn_strips:
            abn_strips.append('<div style="color:#06d6a0; padding:12px 0; font-size:0.85rem;">✅ 当前全部传感与增氧设备均在线正常运行！</div>')
        st.markdown(
            f"""<div class="tech-card notranslate" translate="no">
<div class="tech-card-header">
<span class="tech-card-title">待检修/离线设备速览 ({len(abn_devices)}台)</span>
<span class="tech-card-action"><a href="?jump_to=03" target="_self" class="card-jump-btn">关联告警 →</a></span>
</div>
{"".join(abn_strips)}
</div>""",
            unsafe_allow_html=True,
        )

    # 2.3 传感与控制设备状态台账表格
    st.markdown(
        f'<div class="tech-card notranslate" translate="no"><div class="tech-card-header"><span class="tech-card-title">传感与控制设备状态台账 (当前展示 {len(filtered_items)} / {len(all_items)} 台，故障与离线置顶)</span></div></div>',
        unsafe_allow_html=True,
    )
    if filtered_items:
        st.dataframe(
            pd.DataFrame([
                {
                    "设备ID": e["equipment_id"],
                    "设备编号": e["equipment_code"],
                    "设备名称": e["equipment_name"],
                    "设备类型": e["equipment_type"],
                    "关联养殖池": e["pond_name"] or "园区公共",
                    "安装位置": e["install_location"],
                    "运行状态": f"● {EQUIPMENT_STATUS_LABELS.get(e['status'], e['status'])}",
                    "数据来源": SOURCE_LABELS.get(e["source_type"], e["source_type"]),
                    "最近上报时间": e["last_reported_at"],
                }
                for e in filtered_items
            ]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("当前筛选条件下暂无匹配的设备记录。")

    # 2.4 设备状态更新（联动告警闭环） + 设备状态变更历史记录
    op_col1, op_col2 = st.columns([1.15, 1.45])
    with op_col1:
        with st.form("update_eq_status_v37"):
            st.markdown("#### 🔄 更新设备状态与上报记录（自动联动告警闭环）")
            eq_id = st.selectbox(
                "选择目标设备",
                options=[e["equipment_id"] for e in all_items],
                format_func=lambda eid: next(
                    f"{e['equipment_code']} - {e['equipment_name']} (当前: {EQUIPMENT_STATUS_LABELS.get(e['status'], e['status'])})"
                    for e in all_items if e["equipment_id"] == eid
                ),
            )
            c_st, c_op = st.columns(2)
            with c_st:
                new_st = st.selectbox("变更为目标状态", options=["ONLINE", "OFFLINE", "FAULT"], format_func=lambda k: EQUIPMENT_STATUS_LABELS[k])
            with c_op:
                op_user = st.text_input("巡检/维护人", value="张工")
            remark = st.text_input("状态变更与检修说明", value="现场巡检维护完成，恢复在线正常上报")
            if st.form_submit_button("✅ 提交状态更新并同步告警"):
                res = EquipmentService.update_status_with_alert_sync(eq_id, new_st, remark, op_user, "MANUAL")
                st.cache_data.clear()
                st.success(f"设备 `{res['equipment_code']}` 状态已更新为【{EQUIPMENT_STATUS_LABELS[new_st]}】{res['sync_msg']}！")
                st.rerun()

        with st.expander("➕ 新增传感与控制设备档案"):
            with st.form("new_equip_form_v37"):
                ne1, ne2 = st.columns(2)
                with ne1:
                    n_eq_code = st.text_input("设备编号 (唯一)", value=f"EQ-SEN-{datetime.now().strftime('%H%M')}")
                    n_eq_name = st.text_input("设备名称", value="C01尾水多参数在线监测仪")
                    n_eq_type = st.selectbox("设备类型", options=["水质传感器", "增氧机", "循环水泵", "自动投饵机", "视频监控终端"])
                with ne2:
                    n_eq_pond = st.selectbox("关联养殖池", options=[p["pond_id"] for p in ponds], format_func=lambda pid: next(f"{p['pond_code']} - {p['pond_name']}" for p in ponds if p["pond_id"] == pid))
                    n_eq_loc = st.text_input("安装位置", value="C01池出水口监测站")
                    n_eq_st = st.selectbox("初始状态", options=["ONLINE", "OFFLINE", "FAULT"], format_func=lambda k: EQUIPMENT_STATUS_LABELS[k])
                if st.form_submit_button("✅ 保存新增设备档案"):
                    try:
                        EquipmentRepository.create_equipment(
                            n_eq_code.strip(),
                            n_eq_name.strip(),
                            n_eq_type,
                            n_eq_pond,
                            n_eq_loc.strip(),
                            n_eq_st,
                            "MANUAL",
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        )
                        st.cache_data.clear()
                        st.success(f"设备 `{n_eq_code}` 建档成功！")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"新增设备失败：{exc}")

    with op_col2:
        st.markdown("#### 📜 设备状态变更与巡检维护历史记录")
        st_records = EquipmentRepository.list_status_records(limit=25)
        if st_records:
            st.dataframe(
                pd.DataFrame([
                    {
                        "记录ID": r["status_record_id"],
                        "设备编号": r["equipment_code"],
                        "设备名称": r["equipment_name"],
                        "关联池位": r["pond_code"] or "公共",
                        "变更后状态": EQUIPMENT_STATUS_LABELS.get(r["status"], r["status"]),
                        "数据来源": SOURCE_LABELS.get(r["source_type"], r["source_type"]),
                        "上报/变更时间": r["reported_at"],
                        "巡检维护备注": r["remark"] or "--",
                    }
                    for r in st_records
                ]),
                use_container_width=True,
                hide_index=True,
            )

with t_pond:
    st.markdown('<div class="tech-card notranslate" translate="no"><div class="tech-card-header"><span class="tech-card-title">养殖池基础档案列表</span></div></div>', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame([
            {
                "池ID": p["pond_id"],
                "池编号": p["pond_code"],
                "池名称": p["pond_name"],
                "所属区域": p["area_name"],
                "养殖模式": p["pond_type"],
                "面积(m²)": p["area_m2"],
                "设计水体容量(m³)": p["capacity"],
                "状态": POND_STATUS_LABELS.get(p["status"], p["status"]),
                "当前在养批次": p["active_batch_code"] or "无",
                "当前在养品种": p.get("active_species_name") or "空闲/维护",
            }
            for p in ponds
        ]),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("➕ 新增养殖池档案"):
        areas = FarmRepository.list_areas()
        with st.form("new_pond_form_v37"):
            c1, c2, c3 = st.columns(3)
            with c1:
                p_code = st.text_input("养殖池编号 (唯一)", value="POND-B03")
                p_name = st.text_input("养殖池名称", value="B03号生态罗氏沼虾池")
            with c2:
                p_area_id = st.selectbox("所属区域", options=[a["area_id"] for a in areas], format_func=lambda aid: next(a["area_name"] for a in areas if a["area_id"] == aid))
                p_type = st.selectbox("养殖模式", options=["室内循环水池", "高位精养池", "生态大塘", "尾水监测池"])
            with c3:
                p_m2 = st.number_input("池塘面积 (m²)", min_value=10.0, value=400.0)
                p_cap = st.number_input("设计水体容量 (m³)", min_value=10.0, value=500.0)
            if st.form_submit_button("✅ 保存新增养殖池"):
                try:
                    FarmRepository.create_pond(p_code, 1, p_area_id, p_name, p_type, p_m2, p_cap)
                    st.cache_data.clear()
                    st.success(f"养殖池 `{p_code}` 创建成功！")
                    st.rerun()
                except Exception as exc:
                    st.error(f"创建失败：{exc}")

with t_species:
    st.markdown('<div class="tech-card notranslate" translate="no"><div class="tech-card-header"><span class="tech-card-title">养殖品种适宜水质范围标准库</span></div></div>', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame([
            {
                "品种编号": s["species_code"],
                "品种名称": s["species_name"],
                "类别": s["category"],
                "生长阶段": s["growth_stage"],
                "适宜水温(°C)": f"{s['temp_min_c']} ~ {s['temp_max_c']}",
                "最低溶解氧(mg/L)": s["do_min_mg_l"],
                "适宜pH范围": f"{s['ph_min']} ~ {s['ph_max']}",
                "氨氮上限(mg/L)": s["ammonia_max_mg_l"],
                "说明": s["remark"],
            }
            for s in species
        ]),
        use_container_width=True,
        hide_index=True,
    )
