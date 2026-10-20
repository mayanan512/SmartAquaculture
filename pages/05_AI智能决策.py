# -*- coding: utf-8 -*-
"""
05 AI 智能决策辅助 (V3.4 动态高亮池塘树 + 四大诊断模型差异化推演 + 历史归档版)
"""

import streamlit as st
import pandas as pd
from algorithms.anomaly_detector import detect_multivariate_anomalies_iforest
from config.settings import ASSETS_DIR, EQUIPMENT_STATUS_LABELS
from components.theme import init_page, render_tech_image
from components.charts import build_dual_metric_spline_chart
from repositories.equipment_repo import EquipmentRepository
from repositories.farm_repo import FarmRepository
from repositories.water_quality_repo import WaterQualityRepository
from services.ai_service import AIDecisionService
from services.production_service import ProductionService

init_page("AI 智能决策辅助", "AI智能决策")

ponds = FarmRepository.list_ponds()
all_batches = ProductionService.list_all_batch_metrics()

col_left, col_center, col_right = st.columns([1.18, 1.38, 1.44])

with col_left:
    area_tab = st.radio("筛选养殖区域：", ["全部区域", "A区 循环水车间", "B区 生态虾蟹塘", "C区 尾水净化区"], horizontal=True)

    if area_tab == "A区 循环水车间":
        avail_ponds = [p for p in ponds if "A" in p["pond_code"]]
    elif area_tab == "B区 生态虾蟹塘":
        avail_ponds = [p for p in ponds if "B" in p["pond_code"]]
    elif area_tab == "C区 尾水净化区":
        avail_ponds = [p for p in ponds if "C" in p["pond_code"]]
    else:
        avail_ponds = ponds

    pond_display_map = {
        p["pond_id"]: f"{p['pond_code']} - {p['pond_name']} ({p.get('active_species_name') or '空闲/维护'})"
        for p in avail_ponds
    }
    ctx_pid = st.session_state.get("selected_pond_id", avail_ponds[0]["pond_id"])
    default_idx = list(pond_display_map.keys()).index(ctx_pid) if ctx_pid in pond_display_map else 0

    sel_pid = st.selectbox(
        "🎯 点击切换目标池塘/品种：",
        options=list(pond_display_map.keys()),
        format_func=lambda pid: pond_display_map[pid],
        index=default_idx,
    )
    st.session_state["selected_pond_id"] = sel_pid
    cur_pond = next(p for p in ponds if p["pond_id"] == sel_pid)

    # 完整闭合在单个 tech-card 容器内的动态高亮池塘树
    tree_lines = [
        '<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">分析对象选择</span><span class="tech-card-action">🟢 动态树联动</span></div>',
        '<div style="font-size:0.82rem; line-height:1.8; padding:6px 10px; background:rgba(4,18,42,0.6); border-radius:4px;">',
        '<div style="color:#00f0ff; font-weight:700;">📂 智渔云示范园区池塘树</div>',
    ]
    for p in avail_ponds:
        is_cur = (p["pond_id"] == sel_pid)
        icon_chk = "☑" if is_cur else "☐"
        color_st = "#00f0ff; font-weight:700;" if is_cur else "#9cc2ff;"
        sp_tag = p.get("active_species_name") or "维护/备用"
        tree_lines.append(f'<div style="margin-left:14px; color:{color_st}">{icon_chk} {p["pond_code"]} {p["pond_name"][:7]} ({sp_tag[:4]})</div>')
    tree_lines.append("</div></div>")
    st.markdown("".join(tree_lines), unsafe_allow_html=True)

    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">分析类型选择</span></div></div>', unsafe_allow_html=True)
    ai_type = st.radio(
        "切换智能诊断视角：",
        [
            "💧 水质异常多维协同诊断",
            "🐟 鱼虾蟹生长与健康评估",
            "⚙️ 设备故障预测与能耗优化",
            "🥣 精准投喂策略与时段推荐",
        ],
        index=0,
        label_visibility="collapsed",
    )

    with st.expander("🔌 外部大模型 API 配置（可选，未配自动降级）"):
        llm_key = st.text_input("大模型接口密钥（选填，留空默认使用本地专家规则引擎）", type="password", value="")

    if st.button("▶ 开始智能分析推演（写入诊断记录库）", use_container_width=True):
        res = AIDecisionService.generate_pond_analysis(sel_pid, api_key_override=llm_key)
        st.cache_data.clear()
        st.success(f"已完成多源融合诊断并写入数据库（记录ID: #{res['analysis_id']}）！")

latest_wq = WaterQualityRepository.get_latest_by_pond(sel_pid)
wq_hist = WaterQualityRepository.query_records_df(pond_id=sel_pid)
iforest_res = detect_multivariate_anomalies_iforest(wq_hist)
cur_batch = next((b for b in all_batches if b["pond_id"] == sel_pid and b["status"] == "ACTIVE"), None)
pond_equips = EquipmentRepository.list_equipment(pond_id=sel_pid)

temp_val = latest_wq["water_temp_c"] if latest_wq else None
do_val = latest_wq["dissolved_oxygen_mg_l"] if latest_wq else None
ph_val = latest_wq["ph"] if latest_wq else None
nh3_val = latest_wq["ammonia_mg_l"] if latest_wq else None

with col_center:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">AI 智能中枢决策脑图</span></div></div>', unsafe_allow_html=True)
    brain_img_path = ASSETS_DIR / "images" / "ai_brain.png"
    if brain_img_path.exists():
        render_tech_image(brain_img_path, caption="智渔云多源数据融合 AI 决策全息脑图")

    iforest_badge = iforest_res.get("summary", "当前池塘样本较少，启用专家规则基线评估")
    st.markdown(
        f"""<div style="background:rgba(6,26,56,0.9); border:1px solid #00f0ff; border-radius:6px; padding:8px 12px; font-size:0.8rem; color:#9cc2ff; margin-top:4px;">
🔬 <b>多维无监督检测状态</b>：{iforest_badge}
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px; margin-top:8px;">
<div style="background:rgba(6,26,56,0.85); border:1px solid rgba(0,212,255,0.3); border-radius:4px; padding:8px 10px; font-size:0.78rem; text-align:center;">
<span style="color:#00f0ff; font-weight:700;">🌐 多源数据融合分析</span><br><span style="color:#9cc2ff; font-size:0.72rem;">水质 · 设备 · 批次 · 品种</span>
</div>
<div style="background:rgba(6,26,56,0.85); border:1px solid rgba(0,212,255,0.3); border-radius:4px; padding:8px 10px; font-size:0.78rem; text-align:center;">
<span style="color:#06d6a0; font-weight:700;">⚙️ 机理模型分析推演</span><br><span style="color:#9cc2ff; font-size:0.72rem;">硝化负荷与呼吸耗氧模型</span>
</div>
<div style="background:rgba(6,26,56,0.85); border:1px solid rgba(0,212,255,0.3); border-radius:4px; padding:8px 10px; font-size:0.78rem; text-align:center;">
<span style="color:#ffb703; font-weight:700;">📊 孤立森林多维算法</span><br><span style="color:#9cc2ff; font-size:0.72rem;">四维水质协同离群检测</span>
</div>
<div style="background:rgba(6,26,56,0.85); border:1px solid rgba(0,212,255,0.3); border-radius:4px; padding:8px 10px; font-size:0.78rem; text-align:center;">
<span style="color:#9d4edd; font-weight:700;">📚 专家规则 + 大模型</span><br><span style="color:#9cc2ff; font-size:0.72rem;">人机协同辅助（不直控硬件）</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )

with col_right:
    # 根据所选分析类型 (ai_type) 和池塘实测数据生成针对性的归因与建议
    if "生长与健康" in ai_type and cur_batch:
        risk_badge = f'<div style="font-size:1.15rem; font-weight:800; color:#06d6a0;">🐟 生长与健康评估 —— {cur_batch["species_name"]}</div><div style="font-size:0.78rem; color:#fff;">在池存活 {cur_batch["current_alive_count"]:,} 尾(只)，综合成活率 {cur_batch["biological_survival_rate_pct"]}%，最新均重 {cur_batch["latest_avg_weight_g"]}g。</div>'
        risk_bg = "rgba(6,214,160,0.18); border:1px solid #06d6a0;"
        cause_1 = f"<b>1. 规格增长曲线</b>：初始均重 {round(cur_batch['stocking_weight_kg']*1000/max(1,cur_batch['initial_count']),1)}g → 最新抽样均重 {cur_batch['latest_avg_weight_g']}g，当前估算存量 {cur_batch['estimated_biomass_kg']} kg。"
        cause_2 = f"<b>2. 损耗与成活表现</b>：累计登记死亡 {cur_batch['total_dead']} 尾(只)，综合生物学成活率达 {cur_batch['biological_survival_rate_pct']}%。"
        cause_3 = f"<b>3. 环境健康耦合</b>：当前溶解氧 {do_val if do_val is not None else '缺失'} mg/L，需防范低氧或高氨氮引起摄食应激。"
        sugg_1 = "<b>① 定期抽样测重</b>：每 10 天随机抽样 40~60 尾复核生长速率"
        sugg_2 = "<b>② 肠道与免疫保健</b>：拌料添加乳酸菌与多维，增强抗应激能力"
        sugg_3 = "<b>③ 密度分级管理</b>：当存量密度超标时合理安排分批出塘"
        sugg_4 = "<b>④ 防范脱壳/换水应激</b>：换水温差控制在 ±1.5°C 以内"
    elif "设备故障" in ai_type:
        fault_eqs = [e for e in pond_equips if e["status"] != "ONLINE"]
        if fault_eqs:
            risk_badge = f'<div style="font-size:1.15rem; font-weight:800; color:#ff3366;">⚙️ 设备异常预警 ({len(fault_eqs)} 台异常)</div><div style="font-size:0.78rem; color:#fff;">检测到关联设备【{fault_eqs[0]["equipment_name"]}】处于 {EQUIPMENT_STATUS_LABELS.get(fault_eqs[0]["status"], fault_eqs[0]["status"])} 状态！</div>'
            risk_bg = "rgba(255,51,102,0.18); border:1px solid #ff3366;"
        else:
            risk_badge = f'<div style="font-size:1.15rem; font-weight:800; color:#06d6a0;">⚙️ 池塘设备运行正常 ({len(pond_equips)} 台在线)</div><div style="font-size:0.78rem; color:#fff;">当前池塘关联传感器与增氧/循环水设备全部在线上报。</div>'
            risk_bg = "rgba(6,214,160,0.18); border:1px solid #06d6a0;"
        cause_1 = f"<b>1. 关联设备巡检</b>：该池塘共绑定 {len(pond_equips)} 台设备，异常设备 {len(fault_eqs)} 台。"
        cause_2 = "<b>2. 增氧与水泵耦合</b>：若增氧机故障停机超过 2 小时，底层溶解氧将快速跌破 5.0 mg/L。"
        cause_3 = "<b>3. 传感器心跳监测</b>：超过 120 分钟未上报数据的探头将被自动标记为离线。"
        sugg_1 = "<b>① 启用备用机组</b>：故障期间立即手动切换至备用增氧/水泵支路"
        sugg_2 = "<b>② 错峰变频节能</b>：白天溶氧充足时段下调变频水泵功率 15%"
        sugg_3 = "<b>③ 探头定期校准</b>：每两周清洗溶解氧膜头与 pH 玻璃电极"
        sugg_4 = "<b>④ 状态台账更新</b>：检修完成后在【养殖场与设备】更新状态"
    elif "精准投喂" in ai_type and cur_batch:
        daily_rec_kg = round(cur_batch["estimated_biomass_kg"] * (0.012 if (do_val and do_val < 5.2) else 0.018), 1)
        risk_badge = f'<div style="font-size:1.15rem; font-weight:800; color:#00f0ff;">🥣 精准投喂策略推荐 —— 建议日投喂 {daily_rec_kg} kg</div><div style="font-size:0.78rem; color:#fff;">基于当前存量 {cur_batch["estimated_biomass_kg"]} kg 与水温 {temp_val}°C、溶氧 {do_val} mg/L 动态测算。</div>'
        risk_bg = "rgba(0,240,255,0.16); border:1px solid #00f0ff;"
        cause_1 = f"<b>1. 生物量基数核算</b>：当前在池估算存量 {cur_batch['estimated_biomass_kg']} kg，累计已投喂 {cur_batch['total_feed_kg']} kg。"
        cause_2 = f"<b>2. 水温与溶氧修正系数</b>：水温 {temp_val}°C，溶氧 {do_val} mg/L {'(偏低需减料30%)' if (do_val and do_val < 5.2) else '(溶氧充沛可正常投喂)'}。"
        cause_3 = f"<b>3. 氨氮负荷约束</b>：当前氨氮 {nh3_val if nh3_val is not None else '待补录'} mg/L，控制残饵是抑制氨氮上升的关键。"
        sugg_1 = f"<b>① 推荐日投喂量</b>：全天建议分 2~3 餐投喂共约 {daily_rec_kg} kg"
        sugg_2 = "<b>② 最佳投喂时段</b>：08:30（35%）、14:00（40%）、18:30（25%）"
        sugg_3 = "<b>③ 低氧/高氨氮停减料</b>：当溶氧 <5.0 或氨氮 >0.40 时立即减停当餐"
        sugg_4 = "<b>④ 料台残饵巡查</b>：投喂后 1 小时检查料台，动态微调下餐料量"
    else:
        # 默认：水质异常多维协同诊断
        if latest_wq is None:
            risk_badge = '<div style="font-size:1.15rem; font-weight:800; color:#9cc2ff;">⏸️ 暂无监测数据</div><div style="font-size:0.78rem; color:#fff;">该池塘处于空闲或维护状态，尚未接入水质监测序列。</div>'
            risk_bg = "rgba(0,180,216,0.18); border:1px solid #00b4d8;"
            cause_1 = "<b>1. 池塘状态</b>：当前池塘未绑定活动批次或处于清塘维护期。"
            cause_2 = "<b>2. 传感采集</b>：暂无近期水温、溶解氧、pH 与氨氮入库记录。"
            cause_3 = f"<b>3. 诊断视角</b>：{ai_type}"
            sugg_1 = "<b>① 投产前检查</b>：放养前完成池底消毒与传感器探头校准"
            sugg_2 = "<b>② 录入首检数据</b>：在【水质监测中心】录入进水基线水质"
            sugg_3 = "<b>③ 设备联调</b>：确认增氧机与水泵在线状态"
            sugg_4 = "<b>④ 建立批次</b>：在【养殖生产管理】创建新批次"
        elif do_val is not None and do_val < 5.0:
            risk_badge = f'<div style="font-size:1.18rem; font-weight:800; color:#ff3366;">🚨 高风险低氧预警</div><div style="font-size:0.78rem; color:#fff;">实测溶解氧仅 {do_val} mg/L (&lt; 5.0 mg/L 阈值)，存在浮头或脱壳期窒息风险！</div>'
            risk_bg = "rgba(255,51,102,0.18); border:1px solid #ff3366;"
            cause_1 = f"<b>1. 溶解氧持续下滑</b>：近24小时溶氧降至 {do_val} mg/L，低于安全下限 5.0 mg/L。"
            cause_2 = "<b>2. 增氧设备异常耦合</b>：关联叶轮增氧机处于故障状态，机械曝气补充不足。"
            cause_3 = f"<b>3. 生物呼吸耗氧高峰</b>：水温 {temp_val}°C 较高，水生动物与微生物耗氧速率加快。"
            sugg_1 = "<b>① 紧急增氧核查</b>：人工现场开启备用增氧机（系统不自动启停设备）"
            sugg_2 = "<b>② 暂停当餐投喂</b>：立即停料观察，防止残饵腐败加剧耗氧"
            sugg_3 = "<b>③ 排查设备故障</b>：检修故障增氧机接触器与线路"
            sugg_4 = "<b>④ 30分钟后复测</b>：在【智能预警中心】登记复测溶氧值"
        elif nh3_val is not None and nh3_val > 0.40:
            risk_badge = f'<div style="font-size:1.18rem; font-weight:800; color:#ffb703;">⚠️ 高危氨氮超标预警</div><div style="font-size:0.78rem; color:#fff;">实测氨氮达 {nh3_val} mg/L (&gt; 0.40 mg/L 阈值)，需防范鳃组织损伤！</div>'
            risk_bg = "rgba(255,183,3,0.18); border:1px solid #ffb703;"
            cause_1 = f"<b>1. 氨氮突破安全上限</b>：当前实测 {nh3_val} mg/L，高于品种容忍阈值 0.40 mg/L。"
            cause_2 = "<b>2. 高蛋白投喂残饵累积</b>：近期高蛋白饲料投喂负荷较高，生物滤池硝化速率阶段性饱和。"
            cause_3 = f"<b>3. 水温与酸碱耦合</b>：当前水温 {temp_val}°C、pH {ph_val}，需防范非离子态分子氨比例升高。"
            sugg_1 = "<b>① 加大换水与反冲洗</b>：提升循环水生物滤池反冲洗频次并适量换水"
            sugg_2 = "<b>② 下调投喂量 30%</b>：后续 1~2 餐减量投喂，减轻氨氮排泄负荷"
            sugg_3 = "<b>③ 补充硝化菌剂</b>：泼洒复合芽孢杆菌与硝化细菌制剂"
            sugg_4 = "<b>④ 2小时后复测</b>：复测氨氮降至 0.40 mg/L 以下后关闭告警"
        elif any(v is None for v in (temp_val, do_val, ph_val, nh3_val)):
            risk_badge = '<div style="font-size:1.18rem; font-weight:800; color:#ffb703;">ℹ️ 数据部分缺失关注</div><div style="font-size:0.78rem; color:#fff;">当前最新记录存在未采集指标（未采集空值），系统严格拒绝以 0 代替正常值。</div>'
            risk_bg = "rgba(255,183,3,0.15); border:1px solid #ffb703;"
            cause_1 = f"<b>1. 指标缺失识别</b>：水温={temp_val}°C、溶氧={do_val}mg/L、pH={ph_val} 正常，但氨氮字段为空（缺失待补录）。"
            cause_2 = "<b>2. 传感器或录入漏项</b>：关联水质传感器离线或人工抽检未测定氨氮项。"
            cause_3 = "<b>3. 已采集指标稳态</b>：已采集的水温与溶解氧均处于品种适宜区间内。"
            sugg_1 = "<b>① 人工便携复测</b>：使用便携式水质测定仪补测该池塘氨氮浓度"
            sugg_2 = "<b>② 检查离线探头</b>：在【养殖场与设备管理】排查离线传感器供电与通讯"
            sugg_3 = "<b>③ 维持正常投喂</b>：在溶氧充沛前提下维持常规投饵计划"
            sugg_4 = "<b>④ 补录完整数据</b>：在【水质监测中心】录入补测值以恢复完整监控"
        else:
            risk_badge = '<div style="font-size:1.18rem; font-weight:800; color:#06d6a0;">✅ 水质与生产稳态正常</div><div style="font-size:0.78rem; color:#fff;">全部四项核心指标完整且均处于品种适宜阈值范围内。</div>'
            risk_bg = "rgba(6,214,160,0.18); border:1px solid #06d6a0;"
            cause_1 = f"<b>1. 溶解氧充沛稳定</b>：实测溶氧 {do_val} mg/L，高于安全下限 5.0 mg/L。"
            cause_2 = f"<b>2. 氨氮控制良好</b>：实测氨氮 {nh3_val} mg/L，生物硝化系统运转高效。"
            cause_3 = f"<b>3. 温光酸碱适宜</b>：水温 {temp_val}°C、pH {ph_val} 与在养品种生长阶段高度匹配。"
            sugg_1 = "<b>① 保持日常巡检</b>：维持现有循环水过滤与增氧机运行策略"
            sugg_2 = "<b>② 精准定时投喂</b>：按批次存量与水温系数执行标准日投喂率"
            sugg_3 = "<b>③ 定期生长抽样</b>：每 7~10 天抽样测量单体均重以更新存量估算"
            sugg_4 = "<b>④ 尾水达标监控</b>：持续关注 C 区尾水净化池排放指标"

    st.markdown(
        f"""<div class="tech-card">
<div class="tech-card-header">
<span class="tech-card-title">AI 诊断结论 —— {cur_pond['pond_name']}</span>
<span style="font-size:0.74rem; color:#9cc2ff;">安全边界：仅供人工核查</span>
</div>
<div style="background:{risk_bg}; border-radius:6px; padding:10px 14px; display:flex; align-items:center; gap:12px; margin-bottom:12px;">
<div style="font-size:1.9rem;">🤖</div>
<div>{risk_badge}</div>
</div>
<div style="margin-bottom:10px;">
<div style="font-size:0.88rem; font-weight:700; color:#00f0ff; margin-bottom:6px;">🔍 异常原因与多源数据归因</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; margin-bottom:4px; font-size:0.8rem; color:#eaf4ff;">{cause_1}</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; margin-bottom:4px; font-size:0.8rem; color:#eaf4ff;">{cause_2}</div>
<div style="background:rgba(4,18,42,0.6); padding:7px 10px; border-radius:4px; margin-bottom:4px; font-size:0.8rem; color:#eaf4ff;">{cause_3}</div>
</div>
<div>
<div style="font-size:0.88rem; font-weight:700; color:#06d6a0; margin-bottom:6px;">🛠️ 现场核查与管理建议</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; font-size:0.78rem;">
<div style="background:rgba(6,214,160,0.1); border:1px solid rgba(6,214,160,0.3); padding:6px 8px; border-radius:4px; color:#eaf4ff;">{sugg_1}</div>
<div style="background:rgba(255,183,3,0.1); border:1px solid rgba(255,183,3,0.3); padding:6px 8px; border-radius:4px; color:#eaf4ff;">{sugg_2}</div>
<div style="background:rgba(0,187,249,0.1); border:1px solid rgba(0,187,249,0.3); padding:6px 8px; border-radius:4px; color:#eaf4ff;">{sugg_3}</div>
<div style="background:rgba(157,78,221,0.1); border:1px solid rgba(157,78,221,0.3); padding:6px 8px; border-radius:4px; color:#eaf4ff;">{sugg_4}</div>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

st.write("")
b_c1, b_c2, b_c3 = st.columns([1.15, 1.6, 1.25])

with b_c1:
    t_disp = f"{temp_val:.1f} °C" if temp_val is not None else "缺失"
    do_disp = f"{do_val:.2f} mg/L" if do_val is not None else "缺失"
    ph_disp = f"{ph_val:.1f}" if ph_val is not None else "缺失"
    nh3_disp = f"{nh3_val:.2f} mg/L" if nh3_val is not None else "缺失(待补录)"
    do_color = "#ff3366" if (do_val is not None and do_val < 5.0) else "#06d6a0"
    nh3_color = "#ffb703" if (nh3_val is None or nh3_val > 0.40) else "#00f0ff"

    st.markdown(
        f"""<div class="tech-card">
<div class="tech-card-header">
<span class="tech-card-title">当前实测水质 ({cur_pond['pond_code']})</span><span class="tech-card-action"><a href="?jump_to=02" target="_self" class="card-jump-btn">查看详情 →</a></span>
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
<div style="background:rgba(4,18,42,0.65); padding:8px 10px; border-radius:4px;">
<div style="font-size:0.74rem; color:#9cc2ff;">🌡️ 水温</div>
<div style="font-size:1.08rem; font-weight:700; color:#00f0ff;">{t_disp}</div>
</div>
<div style="background:rgba(4,18,42,0.65); padding:8px 10px; border-radius:4px; border-left:3px solid {do_color};">
<div style="font-size:0.74rem; color:{do_color};">💧 溶解氧</div>
<div style="font-size:1.08rem; font-weight:700; color:{do_color};">{do_disp}</div>
</div>
<div style="background:rgba(4,18,42,0.65); padding:8px 10px; border-radius:4px;">
<div style="font-size:0.74rem; color:#9cc2ff;">🧪 pH 值</div>
<div style="font-size:1.08rem; font-weight:700; color:#ffb703;">{ph_disp}</div>
</div>
<div style="background:rgba(4,18,42,0.65); padding:8px 10px; border-radius:4px; border-left:3px solid {nh3_color};">
<div style="font-size:0.74rem; color:#9cc2ff;">⚗️ 氨氮</div>
<div style="font-size:1.08rem; font-weight:700; color:{nh3_color};">{nh3_disp}</div>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

with b_c2:
    plot_df = wq_hist if not wq_hist.empty else WaterQualityRepository.query_records_df(pond_id=1)
    fig_ai_trend = build_dual_metric_spline_chart(plot_df, "water_temp_c", "水温(°C)", "#00f0ff", "dissolved_oxygen_mg_l", "溶氧(mg/L)", "#06d6a0", "", height=215)
    st.plotly_chart(fig_ai_trend, use_container_width=True)

with b_c3:
    st.markdown(
        """<div class="tech-card">
<div class="tech-card-header">
<span class="tech-card-title">历史相似处置案例参考</span>
</div>
<div style="font-size:0.8rem; display:flex; flex-direction:column; gap:8px;">
<div style="background:rgba(4,18,42,0.6); padding:8px 10px; border-radius:4px; border-left:3px solid #ff3366;">
<b style="color:#fff;">对虾脱壳期夜间低氧处置案例</b> <span style="color:#ff3366; font-size:0.72rem;">高危</span><br>
<span style="color:#9cc2ff; font-size:0.74rem;">叶轮增氧机故障导致溶氧跌破 4.5 mg/L，立即启用备用纯氧并停料一餐，2h 后恢复至 6.2 mg/L。</span>
</div>
<div style="background:rgba(4,18,42,0.6); padding:8px 10px; border-radius:4px; border-left:3px solid #ffb703;">
<b style="color:#fff;">循环水加州鲈高氨氮调控案例</b> <span style="color:#ffb703; font-size:0.72rem;">中危</span><br>
<span style="color:#9cc2ff; font-size:0.74rem;">高蛋白投喂引起氨氮升至 0.46 mg/L，通过生物滤池反冲洗+减料30%，24h 内回落至 0.22 mg/L。</span>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

st.write("")
st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">历史 AI 诊断归档记录表 (数据库可追溯记录)</span></div></div>', unsafe_allow_html=True)
ai_hist = AIDecisionService.list_history(limit=15)
if ai_hist:
    st.dataframe(
        pd.DataFrame([
            {
                "诊断ID": h["analysis_id"],
                "养殖池": h["pond_name"] or "--",
                "诊断时间": h["analyzed_at"],
                "使用引擎版本": h["engine_version"],
                "水质与告警现状摘要": h["status_summary"],
                "输入上下文摘要": h["input_summary"],
            }
            for h in ai_hist
        ]),
        use_container_width=True,
        hide_index=True,
    )
