# -*- coding: utf-8 -*-
"""
公共 Plotly 深蓝科技风图表组件 (V4.0 环形图内嵌百分比防截断 + 标题与图例零重叠版)。
"""

from typing import Any, Dict, List, Optional
import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

    class _DummyTrace(dict):
        pass

    class _DummyFig:
        def __init__(self, data=None, **kwargs):
            self.data = list(data) if data else []
            self.layout = kwargs

        def add_trace(self, tr):
            self.data.append(tr)

        def add_hline(self, **kw):
            pass

        def update_yaxes(self, **kw):
            pass

        def update_xaxes(self, **kw):
            pass

        def update_layout(self, **kw):
            self.layout.update(kw)
            return self

    class go:
        Figure = _DummyFig
        Scatter = _DummyTrace
        Scatter3d = _DummyTrace
        Bar = _DummyTrace
        Pie = _DummyTrace

    class px:
        @staticmethod
        def line(*a, **kw):
            f = _DummyFig()
            f.add_trace({"type": "line"})
            return f


def _short_time_labels(series: pd.Series) -> List[str]:
    """将 YYYY-MM-DD HH:MM:SS 转为简短的 HH:MM 刻度，避免 Plotly 渲染英文月份(Oct 19)并倾斜重叠。"""
    res = []
    for val in series:
        s = str(val).strip()
        if len(s) >= 16 and s[4] == "-" and s[10] == " ":
            res.append(s[11:16])
        elif len(s) >= 10:
            res.append(s[5:16])
        else:
            res.append(s)
    return res


def apply_dark_tech_layout(fig: Any, title: str = "", height: int = 240) -> Any:
    """
    核心防重叠布局准则：
    - 当存在 title 时：title 居左上 (y=0.95)，legend 置于底部居中 (y=-0.20)，上下彻底分离，绝不重叠；
    - 当 title 为空时：legend 置于顶部居中 (y=1.02)，紧凑美观。
    """
    has_title = bool(title and title.strip())
    legend_cfg = (
        dict(orientation="h", yanchor="top", y=-0.20, xanchor="center", x=0.5, font=dict(size=10.5, color="#f0f8ff"), bgcolor="rgba(0,0,0,0)")
        if has_title
        else dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10.5, color="#f0f8ff"), bgcolor="rgba(0,0,0,0)")
    )
    top_m = 36 if has_title else 28
    bot_m = 48 if has_title else 30

    fig.update_layout(
        title=dict(
            text=title if has_title else "",
            font=dict(color="#00f0ff", size=12.5, family="Microsoft YaHei"),
            x=0.02,
            y=0.95,
            xanchor="left",
            yanchor="top",
        ),
        height=height,
        paper_bgcolor="rgba(6, 24, 52, 0.78)",
        plot_bgcolor="rgba(3, 14, 32, 0.58)",
        font=dict(color="#f0f8ff", family="Microsoft YaHei, sans-serif"),
        margin=dict(l=38, r=16, t=top_m, b=bot_m),
        xaxis=dict(
            gridcolor="rgba(0, 212, 255, 0.12)",
            zerolinecolor="rgba(0, 212, 255, 0.2)",
            tickfont=dict(size=10.5, color="#d9ecff"),
            tickangle=0,
            automargin=True,
        ),
        yaxis=dict(
            gridcolor="rgba(0, 212, 255, 0.12)",
            zerolinecolor="rgba(0, 212, 255, 0.2)",
            tickfont=dict(size=10.5, color="#d9ecff"),
            automargin=True,
        ),
        legend=legend_cfg,
    )
    return fig


def build_dual_metric_spline_chart(
    df: pd.DataFrame,
    metric_a: str = "water_temp_c",
    label_a: str = "水温(°C)",
    color_a: str = "#00f0ff",
    metric_b: str = "dissolved_oxygen_mg_l",
    label_b: str = "溶氧(mg/L)",
    color_b: str = "#06d6a0",
    title: str = "",
    height: int = 225,
) -> Any:
    if df.empty:
        return apply_dark_tech_layout(go.Figure(), title=title, height=height)
    plot_df = df.sort_values("recorded_at").tail(12)
    x_labels = _short_time_labels(plot_df["recorded_at"])
    fig = go.Figure()
    if metric_a in plot_df.columns:
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=list(plot_df[metric_a]),
            name=label_a,
            mode="lines+markers",
            line=dict(color=color_a, width=2.4, shape="spline"),
            marker=dict(size=5, color=color_a),
            fill="tozeroy",
            fillcolor="rgba(0, 240, 255, 0.08)",
        ))
    if metric_b in plot_df.columns and metric_b != metric_a:
        fig.add_trace(go.Scatter(
            x=x_labels,
            y=list(plot_df[metric_b]),
            name=label_b,
            mode="lines+markers",
            line=dict(color=color_b, width=2.4, shape="spline"),
            marker=dict(size=5, color=color_b),
            fill="tozeroy",
            fillcolor="rgba(6, 214, 160, 0.08)",
        ))
    return apply_dark_tech_layout(fig, title=title, height=height)


def build_donut_chart(labels: List[str], values: List[float], title: str = "", center_text: str = "", height: int = 230) -> Any:
    """
    构建环形图：
    - 锁定 textposition="inside" 并设置 domain=dict(y=[0.12, 0.92])，
      彻底杜绝小扇区百分比(如 7.69% 或 0%)甩到环外顶部被画布边缘截断！
    """
    colors = ["#00f0ff", "#06d6a0", "#ffb703", "#fb8500", "#ff3366", "#9d4edd"]
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        domain=dict(x=[0.04, 0.96], y=[0.14, 0.94]),
        marker=dict(colors=colors[:max(1, len(labels))], line=dict(color="#061a38", width=2)),
        textinfo="percent",
        textposition="inside",
        insidetextorientation="horizontal",
        textfont=dict(size=11, color="#ffffff"),
        hoverinfo="label+value+percent",
    )])
    if center_text:
        fig.update_layout(annotations=[dict(text=center_text, x=0.5, y=0.54, font_size=13, font_color="#ffffff", showarrow=False)])
    fig = apply_dark_tech_layout(fig, title=title, height=height)
    fig.update_layout(
        margin=dict(l=12, r=12, t=28 if title else 14, b=38),
        legend=dict(orientation="h", yanchor="top", y=0.02, xanchor="center", x=0.5, font=dict(size=10.5, color="#f0f8ff")),
    )
    return fig


def build_water_quality_line_chart(
    df: pd.DataFrame,
    metric_col: str,
    metric_label: str,
    unit: str,
    threshold_min: Optional[float] = None,
    threshold_max: Optional[float] = None,
) -> Any:
    if df.empty or metric_col not in df.columns:
        return apply_dark_tech_layout(go.Figure(), f"{metric_label}趋势")
    plot_df = df.dropna(subset=[metric_col]).sort_values("recorded_at").copy()
    plot_df["short_time"] = _short_time_labels(plot_df["recorded_at"])
    fig = px.line(
        plot_df,
        x="short_time",
        y=metric_col,
        color="pond_code" if "pond_code" in plot_df.columns and plot_df["pond_code"].nunique() > 1 else None,
        markers=True,
        labels={"short_time": "时间", metric_col: f"{metric_label}({unit})", "pond_code": "池号"},
    )
    if threshold_min is not None:
        fig.add_hline(y=threshold_min, line_dash="dash", line_color="#ffb703", annotation_text=f"下限 {threshold_min}{unit}", annotation_position="bottom left")
    if threshold_max is not None:
        fig.add_hline(y=threshold_max, line_dash="dash", line_color="#ff3366", annotation_text=f"上限 {threshold_max}{unit}", annotation_position="top left")
    return apply_dark_tech_layout(fig, "")


def build_3d_digital_twin_scene(
    ponds: List[Dict[str, Any]],
    latest_wq_list: List[Dict[str, Any]],
    active_batches: List[Dict[str, Any]],
    alerts: List[Dict[str, Any]],
    selected_pond_id: Optional[int] = None,
) -> Any:
    """构建 3D 数字孪生智慧养殖园区空间水体剖面与浮标态势图"""
    wq_map = {w["pond_id"]: w for w in latest_wq_list}
    batch_map = {b["pond_id"]: b for b in active_batches}
    active_alert_ponds = {a["pond_id"] for a in alerts if a["status"] in ("NEW", "ACKNOWLEDGED") and a.get("pond_id")}

    fig = go.Figure()
    surface_x, surface_y, surface_z = [], [], []
    surface_text, surface_color, surface_size = [], [], []
    bottom_x, bottom_y, bottom_z = [], [], []
    bottom_text, bottom_color = [], []

    for p in ponds:
        pid = p["pond_id"]
        p_code = p.get("pond_code", "")
        p_name = p.get("pond_name", "")
        p_type = p.get("pond_type", "标准池")
        cx = float(p.get("map_x") or 50.0)
        cy = float(p.get("map_y") or 50.0)
        wq = wq_map.get(pid, {})
        batch = batch_map.get(pid)
        has_alert = pid in active_alert_ponds
        is_sel = (pid == selected_pond_id)

        do_val = wq.get("dissolved_oxygen_mg_l")
        nh3_val = wq.get("ammonia_mg_l")
        temp_val = wq.get("water_temp_c")

        node_color = "#ff3366" if has_alert else ("#00f5d4" if p.get("status") == "IN_USE" else "#8ab4f8")
        status_tag = "🚨 告警活动" if has_alert else ("✅ 运行正常" if p.get("status") == "IN_USE" else "⏸️ 空闲/维护")

        dx, dy = 8.5, 9.5
        depth = -2.2 if "循环水" in p_type else -2.8
        corners_x = [cx - dx, cx + dx, cx + dx, cx - dx, cx - dx]
        corners_y = [cy - dy, cy - dy, cy + dy, cy + dy, cy - dy]
        fig.add_trace(go.Scatter3d(
            x=corners_x, y=corners_y, z=[0.0] * 5, mode="lines",
            line=dict(color="#00f0ff" if is_sel else node_color, width=5 if is_sel else 2.5),
            name=p_code, showlegend=False, hoverinfo="skip",
        ))

        sp_str = batch.get("species_name", "无") if batch else "无"
        bio_str = batch.get("estimated_biomass_kg", 0) if batch else 0
        t_str = f"{temp_val} °C" if temp_val is not None else "缺失"
        do_str = f"{do_val} mg/L" if do_val is not None else "缺失"
        nh3_str = f"{nh3_val} mg/L" if nh3_val is not None else "缺失"

        surface_x.append(cx)
        surface_y.append(cy)
        surface_z.append(0.25)
        surface_color.append(node_color)
        surface_size.append(18 if is_sel else 12)
        surface_text.append(
            f"<b>{p_name} ({p_code})</b><br>"
            f"状态: {status_tag} | 模式: {p_type}<br>"
            f"在养品种: {sp_str} | 估算存量: {bio_str} kg<br>"
            f"水温: {t_str} | 溶氧: {do_str} | 氨氮: {nh3_str}"
        )

        bottom_x.append(cx)
        bottom_y.append(cy)
        bottom_z.append(depth + 0.3)
        bottom_color.append("#ffb703" if (do_val is not None and do_val < 5.0) else "#00bbf9")
        bottom_text.append(f"<b>{p_code} 底层水体剖面 (水深 {abs(depth):.1f}m)</b>")

    fig.add_trace(go.Scatter3d(
        x=surface_x, y=surface_y, z=surface_z, mode="markers+text",
        marker=dict(size=surface_size, color=surface_color, symbol="diamond", line=dict(color="#ffffff", width=1.5)),
        text=[p.get("pond_code", "") for p in ponds], textposition="top center",
        hovertext=surface_text, hoverinfo="text", name="表层水质浮标",
    ))
    fig.add_trace(go.Scatter3d(
        x=bottom_x, y=bottom_y, z=bottom_z, mode="markers",
        marker=dict(size=7, color=bottom_color, symbol="circle"),
        hovertext=bottom_text, hoverinfo="text", name="池底曝气层",
    ))

    fig.update_layout(
        title=dict(text="🧊 三维水体剖面与浮标态势 (可拖拽旋转)", font=dict(color="#00f0ff", size=13), x=0.02, y=0.96),
        height=390,
        paper_bgcolor="rgba(6, 22, 48, 0.85)",
        font=dict(color="#f0f8ff", family="Microsoft YaHei, sans-serif"),
        margin=dict(l=0, r=0, t=32, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.98, bgcolor="rgba(4,15,35,0.6)"),
        scene=dict(
            bgcolor="rgba(4, 15, 35, 0.9)",
            xaxis=dict(title="东西向 X (m)", range=[5, 95], backgroundcolor="rgba(8,28,60,0.4)", gridcolor="rgba(0,212,255,0.2)"),
            yaxis=dict(title="南北向 Y (m)", range=[10, 90], backgroundcolor="rgba(8,28,60,0.4)", gridcolor="rgba(0,212,255,0.2)"),
            zaxis=dict(title="水深 Z (m)", range=[-3.5, 1.2], backgroundcolor="rgba(0,90,150,0.25)", gridcolor="rgba(0,212,255,0.25)"),
            camera=dict(eye=dict(x=1.45, y=-1.55, z=0.95)),
            aspectratio=dict(x=1.5, y=1.1, z=0.55),
        ),
    )
    return fig


def build_multi_pond_wq_chart(
    df: pd.DataFrame,
    metric_col: str = "dissolved_oxygen_mg_l",
    metric_label: str = "溶解氧(mg/L)",
    threshold_val: Optional[float] = 5.0,
    height: int = 235,
) -> Any:
    if df.empty or metric_col not in df.columns:
        return apply_dark_tech_layout(go.Figure(), title="", height=height)
    plot_df = df.dropna(subset=[metric_col]).sort_values("recorded_at")
    palette = ["#00f0ff", "#06d6a0", "#ff3366", "#ffb703", "#9d4edd", "#00bbf9"]
    fig = go.Figure()
    group_col = "pond_code" if "pond_code" in plot_df.columns else "pond_name"
    for idx, (p_key, grp) in enumerate(plot_df.groupby(group_col)):
        tail_grp = grp.tail(10)
        short_name = str(p_key).replace("POND-", "") + "池"
        fig.add_trace(go.Scatter(
            x=_short_time_labels(tail_grp["recorded_at"]),
            y=list(tail_grp[metric_col]),
            name=short_name[:6],
            mode="lines+markers",
            line=dict(color=palette[idx % len(palette)], width=2.3, shape="spline"),
            marker=dict(size=5),
        ))
    if threshold_val is not None:
        fig.add_hline(
            y=threshold_val,
            line_dash="dash",
            line_color="#ff3366",
            annotation_text=f"阈值 {threshold_val}",
            annotation_position="bottom left",
            annotation_font_color="#ff4d79",
            annotation_font_size=10,
        )
    return apply_dark_tech_layout(fig, title="", height=height)


def build_batch_comparison_bar(batches: List[Dict[str, Any]], height: int = 235) -> Any:
    if not batches:
        return apply_dark_tech_layout(go.Figure(), title="", height=height)
    x_labels = [str(b.get("pond_code", "")).replace("POND-", "") + "池" for b in batches]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x_labels,
        y=[b["estimated_biomass_kg"] for b in batches],
        name="在池存量",
        marker=dict(color="#00f0ff"),
    ))
    fig.add_trace(go.Bar(
        x=x_labels,
        y=[b["total_feed_kg"] for b in batches],
        name="累计投喂",
        marker=dict(color="#ffb703"),
    ))
    fig.add_trace(go.Bar(
        x=x_labels,
        y=[b["harvested_weight_kg"] for b in batches],
        name="已出塘量",
        marker=dict(color="#06d6a0"),
    ))
    fig.update_layout(barmode="group")
    return apply_dark_tech_layout(fig, title="", height=height)
