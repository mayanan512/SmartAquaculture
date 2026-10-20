-- ============================================================================
-- 智渔云 (SmartAquaculture) 统一数据库表结构定义 (共 20 张核心表)
-- 数据库引擎: SQLite 3
-- 编码规范: 主键统一 *_id，时间统一 ISO 8601 (YYYY-MM-DD HH:MM:SS)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. 养殖场档案表 (aquaculture_farms)
CREATE TABLE IF NOT EXISTS aquaculture_farms (
    farm_id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_code TEXT NOT NULL UNIQUE,
    farm_name TEXT NOT NULL,
    location TEXT,
    manager_name TEXT,
    contact_phone TEXT,
    total_area_m2 REAL CHECK (total_area_m2 IS NULL OR total_area_m2 >= 0),
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 2. 养殖区域档案表 (aquaculture_areas)
CREATE TABLE IF NOT EXISTS aquaculture_areas (
    area_id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id INTEGER NOT NULL,
    area_code TEXT NOT NULL UNIQUE,
    area_name TEXT NOT NULL,
    area_type TEXT NOT NULL DEFAULT '标准养殖区',
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (farm_id) REFERENCES aquaculture_farms(farm_id)
);

-- 3. 养殖池档案表 (fishponds)
CREATE TABLE IF NOT EXISTS fishponds (
    pond_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pond_code TEXT NOT NULL UNIQUE,
    farm_id INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    pond_name TEXT NOT NULL,
    pond_type TEXT NOT NULL DEFAULT '室内循环水池',
    area_m2 REAL NOT NULL DEFAULT 100.0 CHECK (area_m2 >= 0),
    capacity REAL NOT NULL DEFAULT 150.0 CHECK (capacity >= 0),
    status TEXT NOT NULL DEFAULT 'IN_USE',
    map_x REAL DEFAULT 50.0,
    map_y REAL DEFAULT 50.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (farm_id) REFERENCES aquaculture_farms(farm_id),
    FOREIGN KEY (area_id) REFERENCES aquaculture_areas(area_id)
);

-- 4. 品种及适宜参数表 (species)
CREATE TABLE IF NOT EXISTS species (
    species_id INTEGER PRIMARY KEY AUTOINCREMENT,
    species_code TEXT NOT NULL UNIQUE,
    species_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '鱼类',
    growth_stage TEXT NOT NULL DEFAULT '成长期',
    temp_min_c REAL NOT NULL DEFAULT 18.0,
    temp_max_c REAL NOT NULL DEFAULT 30.0,
    do_min_mg_l REAL NOT NULL DEFAULT 5.0,
    ph_min REAL NOT NULL DEFAULT 7.0,
    ph_max REAL NOT NULL DEFAULT 8.6,
    ammonia_max_mg_l REAL NOT NULL DEFAULT 0.5,
    remark TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 5. 养殖批次表 (culture_batches)
CREATE TABLE IF NOT EXISTS culture_batches (
    batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_code TEXT NOT NULL UNIQUE,
    pond_id INTEGER NOT NULL,
    species_id INTEGER NOT NULL,
    stocking_date TEXT NOT NULL,
    stocking_count INTEGER NOT NULL CHECK (stocking_count >= 0),
    stocking_weight_kg REAL NOT NULL CHECK (stocking_weight_kg >= 0),
    expected_harvest_date TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    remark TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id),
    FOREIGN KEY (species_id) REFERENCES species(species_id)
);

-- 6. 水质监测记录表 (water_quality_records)
CREATE TABLE IF NOT EXISTS water_quality_records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pond_id INTEGER NOT NULL,
    batch_id INTEGER,
    recorded_at TEXT NOT NULL,
    water_temp_c REAL,
    dissolved_oxygen_mg_l REAL CHECK (dissolved_oxygen_mg_l IS NULL OR dissolved_oxygen_mg_l >= 0),
    ph REAL CHECK (ph IS NULL OR (ph >= 0 AND ph <= 14)),
    ammonia_mg_l REAL CHECK (ammonia_mg_l IS NULL OR ammonia_mg_l >= 0),
    source_type TEXT NOT NULL DEFAULT 'SIMULATED',
    quality_status TEXT NOT NULL DEFAULT 'VALID',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id),
    FOREIGN KEY (batch_id) REFERENCES culture_batches(batch_id)
);

-- 7. 预警规则表 (alert_rules)
CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_code TEXT NOT NULL UNIQUE,
    rule_name TEXT NOT NULL,
    species_id INTEGER,
    metric_name TEXT NOT NULL,
    comparison_op TEXT NOT NULL, -- 'LT' (低于), 'GT' (高于)
    threshold_value REAL NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'HIGH',
    is_enabled INTEGER NOT NULL DEFAULT 1,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (species_id) REFERENCES species(species_id)
);

-- 8. 告警记录表 (alert_records)
CREATE TABLE IF NOT EXISTS alert_records (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_code TEXT NOT NULL UNIQUE,
    pond_id INTEGER,
    equipment_id INTEGER,
    rule_id INTEGER,
    alert_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    unit TEXT DEFAULT '',
    threshold_value REAL,
    severity TEXT NOT NULL DEFAULT 'HIGH',
    status TEXT NOT NULL DEFAULT 'NEW',
    triggered_at TEXT NOT NULL,
    acknowledged_at TEXT,
    resolved_at TEXT,
    closed_at TEXT,
    handler_name TEXT,
    latest_measure TEXT,
    retest_result TEXT,
    close_reason TEXT,
    source_type TEXT NOT NULL DEFAULT 'SIMULATED',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 9. 告警处理历史表 (alert_process_records)
CREATE TABLE IF NOT EXISTS alert_process_records (
    process_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    action_type TEXT NOT NULL, -- 'CREATE', 'ACKNOWLEDGE', 'PROCESS', 'RESOLVE', 'CLOSE'
    from_status TEXT,
    to_status TEXT NOT NULL,
    handler_name TEXT NOT NULL,
    action_measure TEXT,
    retest_value REAL,
    retest_conclusion TEXT,
    processed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (alert_id) REFERENCES alert_records(alert_id)
);

-- 10. 设备档案表 (equipment)
CREATE TABLE IF NOT EXISTS equipment (
    equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_code TEXT NOT NULL UNIQUE,
    equipment_name TEXT NOT NULL,
    equipment_type TEXT NOT NULL, -- '水质传感器', '增氧机', '循环水泵', '自动投饵机'
    pond_id INTEGER,
    install_location TEXT,
    status TEXT NOT NULL DEFAULT 'ONLINE',
    source_type TEXT NOT NULL DEFAULT 'SIMULATED',
    last_reported_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 11. 设备状态历史表 (equipment_status_records)
CREATE TABLE IF NOT EXISTS equipment_status_records (
    status_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'SIMULATED',
    reported_at TEXT NOT NULL,
    remark TEXT,
    FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
);

-- 12. 放养记录表 (stocking_records)
CREATE TABLE IF NOT EXISTS stocking_records (
    stocking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    pond_id INTEGER NOT NULL,
    stocking_count INTEGER NOT NULL CHECK (stocking_count > 0),
    stocking_weight_kg REAL NOT NULL CHECK (stocking_weight_kg > 0),
    avg_weight_g REAL NOT NULL CHECK (avg_weight_g > 0),
    fry_source TEXT,
    stocked_at TEXT NOT NULL,
    operator_name TEXT,
    remark TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_id) REFERENCES culture_batches(batch_id),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 13. 投喂记录表 (feeding_records)
CREATE TABLE IF NOT EXISTS feeding_records (
    feeding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    pond_id INTEGER NOT NULL,
    feed_type TEXT NOT NULL,
    feed_weight_kg REAL NOT NULL CHECK (feed_weight_kg > 0),
    unit_price_cny REAL NOT NULL DEFAULT 8.5 CHECK (unit_price_cny >= 0),
    fed_at TEXT NOT NULL,
    operator_name TEXT,
    remark TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_id) REFERENCES culture_batches(batch_id),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 14. 生长记录表 (growth_records)
CREATE TABLE IF NOT EXISTS growth_records (
    growth_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    pond_id INTEGER NOT NULL,
    sampled_at TEXT NOT NULL,
    sample_count INTEGER NOT NULL CHECK (sample_count > 0),
    avg_weight_g REAL NOT NULL CHECK (avg_weight_g > 0),
    avg_length_cm REAL CHECK (avg_length_cm IS NULL OR avg_length_cm > 0),
    operator_name TEXT,
    remark TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_id) REFERENCES culture_batches(batch_id),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 15. 死亡记录表 (mortality_records)
CREATE TABLE IF NOT EXISTS mortality_records (
    mortality_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    pond_id INTEGER NOT NULL,
    dead_count INTEGER NOT NULL CHECK (dead_count > 0),
    recorded_at TEXT NOT NULL,
    cause TEXT,
    disposal_method TEXT DEFAULT '无害化处理',
    operator_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_id) REFERENCES culture_batches(batch_id),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 16. 出塘记录表 (harvest_records)
CREATE TABLE IF NOT EXISTS harvest_records (
    harvest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL,
    pond_id INTEGER NOT NULL,
    harvest_count INTEGER NOT NULL CHECK (harvest_count > 0),
    total_weight_kg REAL NOT NULL CHECK (total_weight_kg > 0),
    unit_price_cny REAL NOT NULL CHECK (unit_price_cny >= 0),
    total_amount_cny REAL NOT NULL CHECK (total_amount_cny >= 0),
    harvested_at TEXT NOT NULL,
    buyer_name TEXT,
    operator_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_id) REFERENCES culture_batches(batch_id),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 17. 成本记录表 (cost_records)
CREATE TABLE IF NOT EXISTS cost_records (
    cost_id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER,
    pond_id INTEGER,
    cost_category TEXT NOT NULL, -- '饲料', '电费能耗', '水源调水', '动保药品', '苗种', '人工运维'
    amount_cny REAL NOT NULL CHECK (amount_cny >= 0),
    occurred_at TEXT NOT NULL,
    description TEXT,
    source_type TEXT NOT NULL DEFAULT 'SIMULATED',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (batch_id) REFERENCES culture_batches(batch_id),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 18. AI 分析记录表 (ai_analysis_records)
CREATE TABLE IF NOT EXISTS ai_analysis_records (
    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pond_id INTEGER,
    batch_id INTEGER,
    alert_id INTEGER,
    engine_version TEXT NOT NULL DEFAULT 'RuleEngine-v1.0',
    input_summary TEXT NOT NULL,
    status_summary TEXT NOT NULL,
    cause_analysis TEXT NOT NULL,
    action_suggestions TEXT NOT NULL,
    analyzed_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (pond_id) REFERENCES fishponds(pond_id)
);

-- 19. 系统设置表 (system_settings)
CREATE TABLE IF NOT EXISTS system_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    setting_group TEXT NOT NULL DEFAULT 'GENERAL',
    description TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 20. 关键操作日志表 (operation_logs)
CREATE TABLE IF NOT EXISTS operation_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_ref TEXT,
    detail TEXT NOT NULL,
    operator_name TEXT NOT NULL DEFAULT '系统管理员',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_wq_pond_time ON water_quality_records(pond_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_alert_status ON alert_records(status, triggered_at);
CREATE INDEX IF NOT EXISTS idx_batch_pond ON culture_batches(pond_id, status);
