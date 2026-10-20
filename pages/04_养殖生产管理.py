# -*- coding: utf-8 -*-
"""
pages/04_养殖生产管理.py (V3.7 修复 NameError: fc1 缩进问题 + 支持跨页焦点池塘联动 + 完整六大生产台账)
"""

from datetime import datetime
import streamlit as st
import pandas as pd
from config.settings import SOURCE_LABELS
from components.theme import init_page
from components.metrics import render_kpi_card
from repositories.farm_repo import FarmRepository
from repositories.production_repo import ProductionRepository
from services.production_service import ProductionService

init_page("养殖生产管理", "养殖生产管理")

batch_metrics = ProductionService.list_all_batch_metrics()
active_batches = [b for b in batch_metrics if b["status"] == "ACTIVE"]

total_alive_kg = sum(b["estimated_biomass_kg"] for b in active_batches)
total_harvest_kg = sum(b["harvested_weight_kg"] for b in batch_metrics)
avg_survival = round(sum(b["biological_survival_rate_pct"] for b in batch_metrics) / len(batch_metrics), 1) if batch_metrics else 96.8
total_feed = sum(b["total_feed_kg"] for b in batch_metrics)

# 1. 顶部 5 大核心生产 KPI 卡片
pk1, pk2, pk3, pk4, pk5 = st.columns(5)
with pk1:
    render_kpi_card("养殖批次总数", f"{len(batch_metrics)}", "批", f"在养 {len(active_batches)} | 结束 {len(batch_metrics)-len(active_batches)}", "up", "📋", "#00f0ff")
with pk2:
    render_kpi_card("在池估算存量", f"{total_alive_kg:,.0f}", "kg", "按抽样均重复算", "up", "🐟", "#06d6a0")
with pk3:
    render_kpi_card("累计出塘产量", f"{total_harvest_kg:,.0f}", "kg", "出塘记录重量汇总", "up", "⚖️", "#00bbf9")
with pk4:
    render_kpi_card("综合成活率", f"{avg_survival}", "%", "扣除死亡损耗均值", "up", "📈", "#ffb703")
with pk5:
    render_kpi_card("累计饲料消耗", f"{total_feed:,.0f}", "kg", "锁定历史单价核算", "up", "🍽️", "#9d4edd")

st.write("")

# 2. 六大生产子模块标签页
t_batch, t_feed, t_growth, t_dead, t_harvest, t_cost = st.tabs([
    "📋 养殖批次台账与建档",
    "🍽️ 投喂记录与登记",
    "📏 生长抽样与测重",
    "⚠️ 死亡损耗登记",
    "🚚 出塘销售登记",
    "💰 专项成本登记",
])

batch_map = {b["batch_id"]: f"{b['batch_code']} - {b['pond_name']} ({b['species_name']} | 在池存活:{b['current_alive_count']})" for b in active_batches}

with t_batch:
    # 初始化或重置级联筛选 session_state
    if st.session_state.get("_reset_prod_filters"):
        st.session_state["prod_sel_p"] = "ALL"
        st.session_state["prod_sel_s"] = "ALL"
        st.session_state["prod_sel_b"] = "ALL"
        st.session_state["_reset_prod_filters"] = False

    fc1, fc2, fc3, fc4 = st.columns([1.35, 1.35, 1.35, 0.95])
    with fc1:
        pond_names = sorted(list({b["pond_name"] for b in batch_metrics}))
        sel_p = st.selectbox("① 按养殖池筛选：", options=["ALL"] + pond_names, format_func=lambda x: "全部养殖池" if x == "ALL" else x, key="prod_sel_p")

    # 根据所选池塘智能级联过滤可选品种与批次
    pool_filtered = [b for b in batch_metrics if sel_p == "ALL" or b["pond_name"] == sel_p]

    with fc2:
        sp_names = sorted(list({b["species_name"] for b in pool_filtered}))
        if st.session_state.get("prod_sel_s") not in (["ALL"] + sp_names):
            st.session_state["prod_sel_s"] = "ALL"
        sel_s = st.selectbox("② 按养殖品种筛选（自动联动）：", options=["ALL"] + sp_names, format_func=lambda x: "当前可选全部品种" if x == "ALL" else x, key="prod_sel_s")

    sp_filtered = [b for b in pool_filtered if sel_s == "ALL" or b["species_name"] == sel_s]

    with fc3:
        b_codes = [b["batch_code"] for b in sp_filtered]
        if st.session_state.get("prod_sel_b") not in (["ALL"] + b_codes):
            st.session_state["prod_sel_b"] = "ALL"
        sel_b = st.selectbox("③ 按批次编号筛选（自动联动）：", options=["ALL"] + b_codes, format_func=lambda x: "当前可选全部批次" if x == "ALL" else x, key="prod_sel_b")

    with fc4:
        st.markdown("<div style=\"height:28px;\"></div>", unsafe_allow_html=True)
        if st.button("🔄 重置全部筛选", use_container_width=True):
            st.session_state["_reset_prod_filters"] = True
            st.rerun()

    filtered_batches = [b for b in sp_filtered if sel_b == "ALL" or b["batch_code"] == sel_b]

    st.markdown(
        f'<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">养殖批次实时核算列表 (当前展示 {len(filtered_batches)} / {len(batch_metrics)} 批)</span><span class="tech-card-action"><a href="?jump_to=06" target="_self" class="card-jump-btn">查看效益报表 →</a></span></div></div>',
        unsafe_allow_html=True,
    )
    if filtered_batches:
        b_df = pd.DataFrame([
            {
                "批次编号": b["batch_code"],
                "养殖池": b["pond_name"],
                "养殖品种": b["species_name"],
                "放养日期": b["stocking_date"],
                "初始放养(尾/只)": b["initial_count"],
                "累计死亡": b["total_dead"],
                "已出塘数": b["harvested_count"],
                "当前存活数": b["current_alive_count"],
                "综合成活率(%)": b["biological_survival_rate_pct"],
                "最新均重(g)": b["latest_avg_weight_g"],
                "估算存量(kg)": b["estimated_biomass_kg"],
                "累计出塘(kg)": b["harvested_weight_kg"],
                "累计投喂(kg)": b["total_feed_kg"],
                "总成本(元)": b["total_cost_cny"],
                "状态": "● 在养中" if b["status"] == "ACTIVE" else "● 已结束",
            }
            for b in filtered_batches
        ])
        st.dataframe(b_df, use_container_width=True, hide_index=True)

    with st.expander("➕ 新建养殖批次并登记初始放养（同一养殖池同时仅允许一个在养批次）"):
        all_ponds = FarmRepository.list_ponds()
        all_species = FarmRepository.list_species()
        with st.form("new_batch_v37"):
            c1, c2, c3 = st.columns(3)
            with c1:
                n_code = st.text_input("新批次编号", value=f"BATCH-{datetime.now().strftime('%Y%m%d')}-A03")
                n_pond = st.selectbox("关联养殖池", options=[p["pond_id"] for p in all_ponds], format_func=lambda pid: next(f"{p['pond_code']} - {p['pond_name']} ({'空闲可投产' if not p['active_batch_id'] else '已有在养:' + p['active_batch_code']})" for p in all_ponds if p["pond_id"] == pid))
            with c2:
                n_sp = st.selectbox("养殖品种", options=[s["species_id"] for s in all_species], format_func=lambda sid: next(s["species_name"] for s in all_species if s["species_id"] == sid))
                n_cnt = st.number_input("初始放养数量 (尾/只)", min_value=100, value=6000, step=500)
            with c3:
                n_wt = st.number_input("初始放养总重量 (kg)", min_value=1.0, value=180.0, step=10.0)
                n_dt = st.text_input("放养日期 (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
            if st.form_submit_button("✅ 创建批次并生成放养记录"):
                try:
                    ProductionService.create_batch(n_code, n_pond, n_sp, n_dt, int(n_cnt), n_wt, "2026-12-31")
                    st.cache_data.clear()
                    st.success(f"新批次 `{n_code}` 创建成功！")
                    st.rerun()
                except Exception as exc:
                    st.error(f"创建失败：{exc}")

with t_feed:
    col1, col2 = st.columns([1.05, 1.65])
    with col1:
        with st.form("add_feed_v37"):
            st.markdown("#### ➕ 新增日常投喂记录")
            f_bid = st.selectbox("选择在养批次", options=list(batch_map.keys()), format_func=lambda k: batch_map[k])
            f_type = st.text_input("饲料名称/规格", value="高蛋白膨化配合饲料")
            f_kg = st.number_input("投喂重量 (kg)", min_value=0.5, value=30.0, step=1.0)
            f_price = st.number_input("当时饲料单价 (元/kg)", min_value=0.0, value=9.5, step=0.5)
            f_op = st.text_input("操作人", value="张工")
            if st.form_submit_button("✅ 保存投喂记录"):
                try:
                    ProductionService.add_feeding_record(f_bid, f_type, f_kg, f_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f_op)
                    st.cache_data.clear()
                    st.success("投喂记录已保存，饲料消耗与成本已实时更新！")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败：{e}")
    with col2:
        st.markdown("#### 📋 最近投喂记录台账")
        feeds = ProductionRepository.list_feeding_records()[:30]
        if feeds:
            st.dataframe(
                pd.DataFrame([
                    {
                        "记录ID": r["feeding_id"],
                        "批次编号": r["batch_code"],
                        "养殖池": r["pond_name"],
                        "饲料类型": r["feed_type"],
                        "投喂重量(kg)": r["feed_weight_kg"],
                        "单价(元/kg)": r["unit_price_cny"],
                        "当餐成本(元)": round(r["feed_weight_kg"] * r["unit_price_cny"], 2),
                        "投喂时间": r["fed_at"],
                        "操作人": r["operator_name"] or "--",
                    }
                    for r in feeds
                ]),
                use_container_width=True,
                hide_index=True,
            )

with t_growth:
    col1, col2 = st.columns([1.05, 1.65])
    with col1:
        with st.form("add_growth_v37"):
            st.markdown("#### ➕ 新增生长抽样记录（自动更新存量估算）")
            g_bid = st.selectbox("选择在养批次", options=list(batch_map.keys()), format_func=lambda k: batch_map[k], key="gr_bid")
            g_cnt = st.number_input("抽样样本数 (尾/只)", min_value=1, value=50, step=5)
            g_wt = st.number_input("平均单体重量 (g)", min_value=0.1, value=310.0, step=5.0)
            g_len = st.number_input("平均体长 (cm)", min_value=0.1, value=26.5, step=0.5)
            g_op = st.text_input("抽样人", value="张工")
            if st.form_submit_button("✅ 保存生长抽样记录"):
                try:
                    ProductionService.add_growth_record(g_bid, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(g_cnt), g_wt, g_len, g_op)
                    st.cache_data.clear()
                    st.success("生长抽样已保存，池塘估算存量已自动重算！")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败：{e}")
    with col2:
        st.markdown("#### 📋 历史生长抽样记录")
        growths = ProductionRepository.list_growth_records()
        if growths:
            st.dataframe(
                pd.DataFrame([
                    {
                        "抽样ID": r["growth_id"],
                        "批次编号": r["batch_code"],
                        "养殖池": r["pond_name"],
                        "抽样时间": r["sampled_at"],
                        "样本数量(尾/只)": r["sample_count"],
                        "平均体重(g)": r["avg_weight_g"],
                        "平均体长(cm)": r["avg_length_cm"] or "--",
                        "抽样人": r["operator_name"] or "--",
                        "备注": r["remark"] or "--",
                    }
                    for r in growths
                ]),
                use_container_width=True,
                hide_index=True,
            )

with t_dead:
    col1, col2 = st.columns([1.05, 1.65])
    with col1:
        with st.form("add_dead_v37"):
            st.markdown("#### ➕ 登记死亡损耗（防负库存校验）")
            m_bid = st.selectbox("选择在养批次", options=list(batch_map.keys()), format_func=lambda k: batch_map[k], key="m_bid")
            m_cnt = st.number_input("死亡数量 (尾/只)", min_value=1, value=10, step=1)
            m_cause = st.text_input("死亡原因说明", value="换水轻度应激损耗")
            m_disp = st.text_input("无害化处理方式", value="无害化深埋处理")
            m_op = st.text_input("登记人", value="张工")
            if st.form_submit_button("✅ 保存死亡损耗记录"):
                try:
                    ProductionService.add_mortality_record(m_bid, int(m_cnt), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), m_cause, m_disp, m_op)
                    st.cache_data.clear()
                    st.success("死亡损耗已登记，当前存活数与成活率已更新！")
                    st.rerun()
                except Exception as e:
                    st.error(f"拦截提示：{e}")
    with col2:
        st.markdown("#### 📋 历史死亡损耗台账")
        deads = ProductionRepository.list_mortality_records()
        if deads:
            st.dataframe(
                pd.DataFrame([
                    {
                        "记录ID": r["mortality_id"],
                        "批次编号": r["batch_code"],
                        "养殖池": r["pond_name"],
                        "死亡数量(尾/只)": r["dead_count"],
                        "记录时间": r["recorded_at"],
                        "原因分析": r["cause"] or "--",
                        "处理方式": r["disposal_method"] or "--",
                        "登记人": r["operator_name"] or "--",
                    }
                    for r in deads
                ]),
                use_container_width=True,
                hide_index=True,
            )

with t_harvest:
    col1, col2 = st.columns([1.05, 1.65])
    with col1:
        with st.form("add_harvest_v37"):
            st.markdown("#### ➕ 登记出塘销售（校验可出塘余额）")
            h_bid = st.selectbox("选择在养批次", options=list(batch_map.keys()), format_func=lambda k: batch_map[k], key="h_bid")
            h_cnt = st.number_input("出塘数量 (尾/只)", min_value=1, value=200, step=10)
            h_kg = st.number_input("出塘总重量 (kg)", min_value=0.5, value=62.0, step=5.0)
            h_price = st.number_input("销售单价 (元/kg)", min_value=0.0, value=38.0, step=1.0)
            h_buyer = st.text_input("采购客户/去向", value="智慧城市生鲜保供冷链中心")
            h_close = st.checkbox("本次出塘后结清并关闭该养殖批次")
            h_op = st.text_input("操作人", value="张工")
            if st.form_submit_button("✅ 保存出塘销售记录"):
                try:
                    ProductionService.add_harvest_record(h_bid, int(h_cnt), h_kg, h_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), h_buyer, h_op, h_close)
                    st.cache_data.clear()
                    st.success("出塘记录已保存，累计产量与销售营收已实时更新！")
                    st.rerun()
                except Exception as e:
                    st.error(f"拦截提示：{e}")
    with col2:
        st.markdown("#### 📋 历史出塘销售记录")
        harvests = ProductionRepository.list_harvest_records()
        if harvests:
            st.dataframe(
                pd.DataFrame([
                    {
                        "出塘ID": r["harvest_id"],
                        "批次编号": r["batch_code"],
                        "养殖池": r["pond_name"],
                        "出塘数量(尾/只)": r["harvest_count"],
                        "出塘总重(kg)": r["total_weight_kg"],
                        "单价(元/kg)": r["unit_price_cny"],
                        "销售总额(元)": r["total_amount_cny"],
                        "出塘时间": r["harvested_at"],
                        "采购方": r["buyer_name"] or "--",
                        "操作人": r["operator_name"] or "--",
                    }
                    for r in harvests
                ]),
                use_container_width=True,
                hide_index=True,
            )

with t_cost:
    col1, col2 = st.columns([1.05, 1.65])
    with col1:
        with st.form("add_cost_v37"):
            st.markdown("#### ➕ 登记专项养殖成本（电费/苗种/动保/水源）")
            c_bid = st.selectbox("关联养殖批次", options=list(batch_map.keys()), format_func=lambda k: batch_map[k], key="c_bid")
            c_cat = st.selectbox("成本类别", options=["电费能耗", "动保药品", "苗种", "水源调水", "人工运维"])
            c_amt = st.number_input("费用金额 (元)", min_value=1.0, value=800.0, step=50.0)
            c_desc = st.text_input("费用明细说明", value="循环水车间阶段性电费与水质改良菌剂分摊")
            if st.form_submit_button("✅ 保存成本记录"):
                try:
                    ProductionService.add_cost_record(c_bid, c_cat, c_amt, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), c_desc, "MANUAL")
                    st.cache_data.clear()
                    st.success("专项成本记录已保存，报表总成本已实时更新！")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存失败：{e}")
    with col2:
        st.markdown("#### 📋 专项成本投入台账（饲料成本由投喂记录自动汇总）")
        costs = ProductionRepository.list_cost_records()
        if costs:
            st.dataframe(
                pd.DataFrame([
                    {
                        "成本ID": r["cost_id"],
                        "批次编号": r["batch_code"] or "园区公共",
                        "养殖池": r["pond_name"] or "园区公共",
                        "成本类别": r["cost_category"],
                        "金额(元)": r["amount_cny"],
                        "发生时间": r["occurred_at"],
                        "说明": r["description"] or "--",
                        "数据来源": SOURCE_LABELS.get(r["source_type"], r["source_type"]),
                    }
                    for r in costs
                ]),
                use_container_width=True,
                hide_index=True,
            )
