# -*- coding: utf-8 -*-
"""
水质阈值规则判断、时间序列趋势分析与多指标联合异常检测算法模块。
支持：
1. 规则阈值比对（高于 GT / 低于 LT，严格忽略 NULL 缺失值）
2. 近期序列线性趋势斜率计算与恶化风险提示
3. 多维水质无监督异常检测（优先使用 Scikit-learn IsolationForest，未安装时自动使用 NumPy 鲁棒马氏/Z-score 离群检测）
"""

from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

try:
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


def check_metric_against_rule(metric_value: Optional[float], comparison_op: str, threshold_value: float) -> bool:
    """单指标规则判定：严格忽略 None/NaN 缺失值，不将空值当作 0。"""
    if metric_value is None or pd.isna(metric_value):
        return False
    val = float(metric_value)
    if comparison_op == "LT":
        return val < float(threshold_value)
    if comparison_op == "GT":
        return val > float(threshold_value)
    return False


def analyze_series_trend(values: List[float]) -> Dict[str, Any]:
    """计算时间序列（按时间正序）的均值、标准差与线性趋势斜率。"""
    clean = [float(v) for v in values if v is not None and not pd.isna(v)]
    if len(clean) < 2:
        return {"count": len(clean), "mean": clean[0] if clean else None, "slope": 0.0, "trend_label": "样本不足"}
    x = np.arange(len(clean), dtype=float)
    y = np.array(clean, dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    if abs(slope) < 0.01:
        label = "平稳波动"
    elif slope > 0:
        label = f"呈上升趋势 (+{slope:.3f}/周期)"
    else:
        label = f"呈下降趋势 ({slope:.3f}/周期)"
    return {
        "count": len(clean),
        "mean": round(float(np.mean(y)), 3),
        "min": round(float(np.min(y)), 3),
        "max": round(float(np.max(y)), 3),
        "slope": round(slope, 4),
        "trend_label": label,
    }


def detect_multivariate_anomalies_iforest(df: pd.DataFrame, contamination: float = 0.15) -> Dict[str, Any]:
    """
    对四项核心水质指标进行多维协同离群检测。
    若已安装 scikit-learn 则使用 IsolationForest；否则自动回退至基于 NumPy 中位数绝对偏差 (MAD) 的多维离群评分。
    """
    feature_cols = ["water_temp_c", "dissolved_oxygen_mg_l", "ph", "ammonia_mg_l"]
    if df.empty or not set(feature_cols).issubset(df.columns):
        return {"available": False, "reason": "数据列不足", "anomaly_count": 0, "latest_is_anomaly": False}

    clean_df = df.dropna(subset=feature_cols).sort_values("recorded_at").copy()
    if len(clean_df) < 5:
        return {"available": False, "reason": "完整多维样本少于5条", "anomaly_count": 0, "latest_is_anomaly": False}

    X = clean_df[feature_cols].to_numpy(dtype=float)
    if HAS_SKLEARN:
        clf = IsolationForest(n_estimators=80, contamination=contamination, random_state=42)
        preds = clf.fit_predict(X)  # -1 为异常点，1 为正常点
        scores = clf.decision_function(X)
        method_name = "孤立森林算法"
        anomaly_count = int(np.sum(preds == -1))
        latest_is_anomaly = bool(preds[-1] == -1)
        latest_score = round(float(scores[-1]), 4)
    else:
        med = np.median(X, axis=0)
        mad = np.median(np.abs(X - med), axis=0) + 1e-6
        z_robust = np.max(np.abs(X - med) / (1.4826 * mad), axis=1)
        threshold = np.percentile(z_robust, 100 * (1.0 - contamination))
        preds = np.where(z_robust > max(threshold, 2.2), -1, 1)
        method_name = "孤立森林/鲁棒离群算法"
        anomaly_count = int(np.sum(preds == -1))
        latest_is_anomaly = bool(preds[-1] == -1)
        latest_score = round(float(-z_robust[-1]), 4)

    return {
        "available": True,
        "method": method_name,
        "sample_size": len(clean_df),
        "anomaly_count": anomaly_count,
        "latest_is_anomaly": latest_is_anomaly,
        "latest_score": latest_score,
        "summary": (
            f"{method_name} 多维检测（样本={len(clean_df)}）：检出 {anomaly_count} 个离群点，"
            f"最新状态={'疑似多指标协同异常' if latest_is_anomaly else '多维分布正常'} (评分={latest_score})"
        ),
    }
