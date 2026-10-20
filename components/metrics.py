# -*- coding: utf-8 -*-
"""
对标参考设计的高端发光科技 KPI 指标卡组件 (V3.9 像素级等高对齐 + 右下角内嵌趋势线防溢出)。
"""

import streamlit as st


def render_kpi_card(
    label: str,
    number_str: str,
    unit: str = "",
    trend_text: str = "",
    trend_type: str = "up",  # "up", "down", "alert"
    icon: str = "🐟",
    border_color: str = "#00f0ff",
) -> None:
    trend_class = "trend-up" if trend_type == "up" else ("trend-alert" if trend_type == "alert" else "trend-down")
    stroke_color = "#ff3366" if trend_type == "alert" else ("#06d6a0" if trend_type == "up" else "#00f0ff")
    pts = "0,20 11,16 22,18 33,11 44,13 54,4" if trend_type != "alert" else "0,15 11,13 22,6 33,12 44,3 54,8"

    st.markdown(
        f"""<div class="kpi-metric-box notranslate" translate="no" style="border-color:{border_color};" title="{label}: {number_str}{unit} ({trend_text})">
<div class="kpi-icon-circle" style="border-color:{border_color};">{icon}</div>
<div class="kpi-content">
<div class="kpi-label">{label}</div>
<div class="kpi-value-row">
<span class="kpi-number">{number_str}</span>
<span class="kpi-unit">{unit}</span>
</div>
<div class="kpi-trend {trend_class}">{trend_text}</div>
</div>
<div class="kpi-sparkline-bg">
<svg viewBox="0 0 56 24" width="54" height="22">
<polyline fill="none" stroke="{stroke_color}" stroke-width="2.2" points="{pts}" />
<circle cx="54" cy="{4 if trend_type != 'alert' else 8}" r="2.8" fill="{stroke_color}" />
</svg>
</div>
</div>""",
        unsafe_allow_html=True,
    )
