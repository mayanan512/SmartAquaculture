# -*- coding: utf-8 -*-
"""
08 数据管理中心 (V3.2 科技视觉统一版)
"""

import pandas as pd
import streamlit as st
from config.settings import DATA_DIR
from components.theme import init_page
from database.init_db import reset_all_data, seed_demo_data
from repositories.system_repo import SystemRepository
from services.water_quality_service import WaterQualityService

init_page("数据管理中心", "数据管理中心")

col_import, col_reset = st.columns([1.4, 1.0])

with col_import:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">批量导入水质监测数据 (CSV / Excel)</span></div></div>', unsafe_allow_html=True)
    sample_csv = DATA_DIR / "sample_water_quality_import.csv"
    if sample_csv.exists():
        st.download_button(
            "📄 下载标准水质导入模板 (sample_water_quality_import.csv)",
            data=sample_csv.read_bytes(),
            file_name="sample_water_quality_import.csv",
            mime="text/csv",
        )

    uploaded = st.file_uploader("上传水质记录文件 (.csv 或 .xlsx)", type=["csv", "xlsx"])
    if uploaded is not None:
        try:
            imp_df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
            st.write("预览上传数据：", imp_df.head())
            if st.button("✅ 执行数据校验并批量入库"):
                ok_cnt, fail_cnt, errs = WaterQualityService.import_from_dataframe(imp_df)
                SystemRepository.log_operation("数据管理中心", "BATCH_IMPORT_WQ", uploaded.name, f"成功导入 {ok_cnt} 条，失败 {fail_cnt} 条")
                st.cache_data.clear()
                st.success(f"导入完成：成功 {ok_cnt} 条，失败 {fail_cnt} 条。")
                if errs:
                    st.warning("部分记录导入失败原因：\n" + "\n".join(errs[:10]))
        except Exception as exc:
            st.error(f"文件解析失败：{exc}")

with col_reset:
    st.markdown('<div class="tech-card"><div class="tech-card-header"><span class="tech-card-title">演示数据幂等重置（需二次确认）</span></div></div>', unsafe_allow_html=True)
    st.warning("⚠️ 重置演示数据将清除当前本地 SQLite 数据库中手工新增的记录，并恢复为标准【模拟演示数据】初始数据集。")
    confirm = st.checkbox("我已知晓重置将清空本地修改，确认执行重置")
    if st.button("🚨 重置为初始标准演示数据", disabled=not confirm):
        reset_all_data()
        seed_demo_data()
        st.cache_data.clear()
        st.success("本地数据库已成功重置为初始标准演示数据！")
        st.rerun()
