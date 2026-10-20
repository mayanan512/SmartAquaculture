# -*- coding: utf-8 -*-
"""
公共主题与全站未来感顶部横幅、气象时间挂件、主导航栏、跨页路由跳转与科技感图像容器组件 (V3.8 零泄漏版)。
"""

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import streamlit as st
from config.settings import ASSETS_DIR, APP_VERSION
from database.init_db import ensure_db_initialized
from repositories.system_repo import SystemRepository

_B64_CACHE: Dict[str, str] = {}

JUMP_PAGE_MAP = {
    "01": "pages/01_智慧养殖总览.py",
    "02": "pages/02_水质监测中心.py",
    "03": "pages/03_智能预警中心.py",
    "04": "pages/04_养殖生产管理.py",
    "05": "pages/05_AI智能决策.py",
    "06": "pages/06_养殖分析报表.py",
    "07": "pages/07_养殖场与设备管理.py",
    "08": "pages/08_数据管理中心.py",
    "09": "pages/09_系统设置.py",
}


def get_base64_asset(file_path: Path) -> str:
    key = str(file_path)
    if key not in _B64_CACHE and file_path.exists():
        _B64_CACHE[key] = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return _B64_CACHE.get(key, "")


def render_tech_image(
    file_path: Path,
    caption: str = "",
    max_height_px: Optional[int] = None,
) -> None:
    """将图片或 SVG 封装在带青蓝发光边框的科技感容器中渲染，兼容所有版本 Streamlit 且不暴露代码。"""
    if not file_path.exists():
        return
    b64_data = get_base64_asset(file_path)
    mime = "image/svg+xml" if file_path.suffix.lower() == ".svg" else "image/png"
    h_style = f"max-height:{max_height_px}px; object-fit:contain;" if max_height_px else "object-fit:cover;"
    cap_html = f'<div class="tech-img-caption">{caption}</div>' if caption else ""
    st.markdown(
        f"""<div class="tech-img-frame notranslate" translate="no">
<img src="data:{mime};base64,{b64_data}" style="width:100%; {h_style} border-radius:6px; display:block; margin:0 auto;" alt="{caption}">
{cap_html}
</div>""",
        unsafe_allow_html=True,
    )


def init_page(page_title: str, current_nav: str = "智慧养殖总览") -> None:
    st.set_page_config(
        page_title=f"{page_title} | 智渔云数字孪生管理平台",
        page_icon="🐟",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    ensure_db_initialized()

    # 处理卡片右上角“查看详情 →” (?jump_to=01..09) 跨页安全跳转
    try:
        qp = getattr(st, "query_params", None)
        if qp is not None and "jump_to" in qp:
            target_code = str(qp["jump_to"])
            if "pond_id" in qp:
                try:
                    st.session_state["selected_pond_id"] = int(qp["pond_id"])
                except ValueError:
                    pass
            qp.clear()
            if target_code in JUMP_PAGE_MAP and hasattr(st, "switch_page"):
                st.switch_page(JUMP_PAGE_MAP[target_code])
    except Exception:
        pass

    # 顶格注入无注释、无空行、无缩进的 <style> 块，彻底杜绝 CommonMark 将 CSS 解析为可见文本
    css_file = ASSETS_DIR / "styles" / "theme.css"
    if css_file.exists():
        raw_css = css_file.read_text(encoding="utf-8")
        clean_css = re.sub(r"/\*.*?\*/", "", raw_css, flags=re.S)
        clean_css = "\n".join(line.strip() for line in clean_css.splitlines() if line.strip())
        st.markdown(f"<style>\n{clean_css}\n</style>", unsafe_allow_html=True)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    settings = SystemRepository.get_settings_dict()
    data_mode = settings.get("data_mode", "SIMULATED")
    mode_tag = "模拟数据演示模式" if data_mode == "SIMULATED" else "实测生产模式"

    st.markdown(
        f"""<div class="glow-header-container notranslate" translate="no">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap;">
<div style="font-size:0.84rem; color:#9cc2ff; display:flex; align-items:center; gap:12px;">
<span>🕒 {now_str}</span>
<span>⛅ 示范园区 多云 24℃</span>
</div>
<div>
<div class="glow-title-text">🐟 智渔云 · 智慧养殖数字孪生管理平台</div>
<div class="glow-subtitle-text">数字孪生 · 智能感知 · 精准管理 · 科学养殖 ({APP_VERSION} | {mode_tag})</div>
</div>
<div style="font-size:0.84rem; color:#06d6a0; display:flex; align-items:center; gap:10px;">
<span>🌱 绿色养殖 · 科技赋能</span>
<span style="background:rgba(0,240,255,0.15); border:1px solid #00f0ff; padding:2px 8px; border-radius:4px; color:#00f0ff;">👤 管理员在线</span>
</div>
</div>
</div>""",
        unsafe_allow_html=True,
    )

    # 紧凑型 9 栏全站导航栏（4字短标题避免大屏列宽截断）
    nav_links = [
        ("pages/01_智慧养殖总览.py", "🖥️ 园区总览"),
        ("pages/02_水质监测中心.py", "💧 水质监测"),
        ("pages/03_智能预警中心.py", "🚨 智能预警"),
        ("pages/04_养殖生产管理.py", "🐟 养殖生产"),
        ("pages/05_AI智能决策.py", "🤖 AI决策"),
        ("pages/06_养殖分析报表.py", "📊 分析报表"),
        ("pages/07_养殖场与设备管理.py", "⚙️ 池塘设备"),
        ("pages/08_数据管理中心.py", "📂 数据中心"),
        ("pages/09_系统设置.py", "🛠️ 系统设置"),
    ]

    cols = st.columns(len(nav_links))
    for i, (page_path, label) in enumerate(nav_links):
        with cols[i]:
            st.page_link(page_path, label=label, use_container_width=True)
