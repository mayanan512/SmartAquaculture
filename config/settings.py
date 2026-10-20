# -*- coding: utf-8 -*-
"""
系统全局配置、枚举常量、单位定义与默认参数。
所有模块必须统一引用此文件中的枚举值，避免各页面硬编码不同字符串。
"""

from pathlib import Path

# 项目根目录与数据库路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "smart_aquaculture.db"
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"
ASSETS_DIR = PROJECT_ROOT / "assets"

# 系统元信息
APP_NAME = "智渔云 —— 智慧养殖数字孪生管理平台"
APP_VERSION = "v0.3.9"

# 1. 数据来源枚举 (source_type)
SOURCE_SIMULATED = "SIMULATED"
SOURCE_MANUAL = "MANUAL"
SOURCE_SENSOR = "SENSOR"

SOURCE_LABELS = {
    SOURCE_SIMULATED: "模拟数据",
    SOURCE_MANUAL: "人工录入",
    SOURCE_SENSOR: "传感器采集",
}

# 2. 水质数据质量状态 (quality_status)
QUALITY_VALID = "VALID"
QUALITY_SUSPICIOUS = "SUSPICIOUS"
QUALITY_MISSING = "MISSING"

QUALITY_LABELS = {
    QUALITY_VALID: "正常有效",
    QUALITY_SUSPICIOUS: "疑似异常",
    QUALITY_MISSING: "部分缺失",
}

# 3. 告警状态枚举 (alert_records.status)
ALERT_STATUS_NEW = "NEW"
ALERT_STATUS_ACK = "ACKNOWLEDGED"
ALERT_STATUS_RESOLVED = "RESOLVED"
ALERT_STATUS_CLOSED = "CLOSED"

ALERT_STATUS_LABELS = {
    ALERT_STATUS_NEW: "待确认",
    ALERT_STATUS_ACK: "处理中",
    ALERT_STATUS_RESOLVED: "已解决",
    ALERT_STATUS_CLOSED: "已关闭",
}

# 4. 风险等级枚举 (severity)
SEVERITY_LOW = "LOW"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

SEVERITY_LABELS = {
    SEVERITY_LOW: "一般关注",
    SEVERITY_MEDIUM: "中度预警",
    SEVERITY_HIGH: "高危告警",
    SEVERITY_CRITICAL: "紧急严重",
}

SEVERITY_COLORS = {
    SEVERITY_LOW: "#00d4ff",
    SEVERITY_MEDIUM: "#ffb703",
    SEVERITY_HIGH: "#fb8500",
    SEVERITY_CRITICAL: "#ff3366",
}

# 5. 养殖池状态枚举 (fishponds.status)
POND_STATUS_IN_USE = "IN_USE"
POND_STATUS_IDLE = "IDLE"
POND_STATUS_MAINTENANCE = "MAINTENANCE"

POND_STATUS_LABELS = {
    POND_STATUS_IN_USE: "在养运行",
    POND_STATUS_IDLE: "空闲待命",
    POND_STATUS_MAINTENANCE: "清塘维护",
}

# 6. 养殖批次状态枚举 (culture_batches.status)
BATCH_STATUS_ACTIVE = "ACTIVE"
BATCH_STATUS_COMPLETED = "COMPLETED"
BATCH_STATUS_PLANNED = "PLANNED"

BATCH_STATUS_LABELS = {
    BATCH_STATUS_ACTIVE: "在养中",
    BATCH_STATUS_COMPLETED: "已出塘结束",
    BATCH_STATUS_PLANNED: "计划放养",
}

# 7. 设备状态枚举 (equipment.status)
EQUIPMENT_ONLINE = "ONLINE"
EQUIPMENT_OFFLINE = "OFFLINE"
EQUIPMENT_FAULT = "FAULT"

EQUIPMENT_STATUS_LABELS = {
    EQUIPMENT_ONLINE: "在线正常",
    EQUIPMENT_OFFLINE: "离线失联",
    EQUIPMENT_FAULT: "故障异常",
}

# 8. 核心水质指标规范与单位
WATER_METRICS = {
    "water_temp_c": {"label": "水温", "unit": "°C", "default_min": 18.0, "default_max": 30.0},
    "dissolved_oxygen_mg_l": {"label": "溶解氧", "unit": "mg/L", "default_min": 5.0, "default_max": 14.0},
    "ph": {"label": "pH值", "unit": "", "default_min": 7.0, "default_max": 8.6},
    "ammonia_mg_l": {"label": "氨氮", "unit": "mg/L", "default_min": 0.0, "default_max": 0.5},
}

# 9. 大模型 API 默认配置（兼容 OpenAI / DeepSeek / 通义千问 DashScope 接口）
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_LLM_MODEL = "deepseek-chat"


def get_metric_label_cn(metric_name: str) -> str:
    """将英文或混合指标名统一映射为标准简体中文名称"""
    if not metric_name:
        return "综合指标"
    if metric_name in WATER_METRICS:
        return WATER_METRICS[metric_name]["label"]
    extra_map = {
        "water_temp_c": "水温",
        "dissolved_oxygen_mg_l": "溶解氧",
        "ammonia_mg_l": "氨氮",
        "ph": "pH值",
        "equipment_status": "设备运行状态",
    }
    return extra_map.get(metric_name, metric_name)
