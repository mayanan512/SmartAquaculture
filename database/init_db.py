# -*- coding: utf-8 -*-
"""
数据库安全初始化与演示数据生成脚本。
- 默认行为：幂等建表；仅当数据库为空（无养殖场记录）时插入带 SIMULATED 标记的演示数据。
- 重置命令：`python -m database.init_db --reset-demo` 可清空并重新生成标准演示数据。
"""

import argparse
from datetime import datetime, timedelta
from config.settings import SCHEMA_PATH, DB_PATH, SOURCE_SIMULATED, QUALITY_VALID, QUALITY_MISSING
from database.connection import db_transaction, get_connection, resolve_db_path


def create_tables() -> None:
    """执行 schema.sql 创建 20 张核心表（幂等安全）。"""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with db_transaction() as conn:
        conn.executescript(schema_sql)


def is_database_empty() -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM aquaculture_farms").fetchone()
        return (row["cnt"] if row else 0) == 0
    finally:
        conn.close()


def reset_all_data() -> None:
    """清空所有业务表并重建结构（仅供演示数据重置使用）。"""
    active_p = resolve_db_path()
    if active_p.exists():
        active_p.unlink()
    create_tables()


def seed_demo_data() -> None:
    """插入覆盖正常、临近阈值、超阈值告警、缺失值与设备离线的标准演示数据。"""
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    fmt = lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S")
    d_fmt = lambda dt: dt.strftime("%Y-%m-%d")

    with db_transaction() as conn:
        # 1. 养殖场与区域
        conn.execute(
            """INSERT INTO aquaculture_farms
            (farm_id, farm_code, farm_name, location, manager_name, contact_phone, total_area_m2, description)
            VALUES (1, 'FARM-001', '智渔云数字孪生示范基地', '智慧城市现代都市农业核心区A座', '林海涛', '13800138000', 12000.0,
                    '面向城市生鲜保供与绿色生态循环养殖的数字孪生示范基地（演示模式）')"""
        )
        areas = [
            (1, 1, 'AREA-A', 'A区-室内工厂化循环水车间', '循环水车间', '高密度微滤+生物滤池循环水系统'),
            (2, 1, 'AREA-B', 'B区-生态智慧虾蟹塘区', '生态池塘区', '配备风光互补增氧与多参数水质浮标'),
            (3, 1, 'AREA-C', 'C区-尾水净化与水源调配区', '尾水处理区', '三级生态沉淀与曝气生物净化池'),
        ]
        conn.executemany(
            "INSERT INTO aquaculture_areas (area_id, farm_id, area_code, area_name, area_type, description) VALUES (?, ?, ?, ?, ?, ?)",
            areas,
        )

        # 2. 养殖池 (6个养殖池，覆盖在养、维护等状态，附带园区点位坐标)
        ponds = [
            (1, 'POND-A01', 1, 1, 'A01号循环水加州鲈池', '室内循环水池', 120.0, 180.0, 'IN_USE', 22.0, 32.0),
            (2, 'POND-A02', 1, 1, 'A02号循环水石斑鱼池', '室内循环水池', 120.0, 180.0, 'IN_USE', 48.0, 32.0),
            (3, 'POND-B01', 1, 2, 'B01号南美白对虾精养池', '高位精养池', 500.0, 600.0, 'IN_USE', 22.0, 68.0),
            (4, 'POND-B02', 1, 2, 'B02号中华绒螯蟹生态池', '生态大塘', 800.0, 720.0, 'IN_USE', 48.0, 68.0),
            (5, 'POND-A03', 1, 1, 'A03号循环水备用育苗池', '室内循环水池', 100.0, 120.0, 'IDLE', 75.0, 32.0),
            (6, 'POND-C01', 1, 3, 'C01号生态尾水监测池', '尾水监测池', 300.0, 450.0, 'MAINTENANCE', 75.0, 68.0),
        ]
        conn.executemany(
            """INSERT INTO fishponds
            (pond_id, pond_code, farm_id, area_id, pond_name, pond_type, area_m2, capacity, status, map_x, map_y)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ponds,
        )

        # 3. 品种与适宜水质范围
        species_list = [
            (1, 'SP-BASS', '优鲈3号加州鲈', '鱼类', '成鱼育肥期', 20.0, 29.0, 5.5, 7.2, 8.5, 0.40, '高密度循环水养殖主力品种，对溶解氧和氨氮敏感'),
            (2, 'SP-GROUPER', '珍珠龙胆石斑鱼', '鱼类', '中鱼生长期', 22.0, 30.0, 5.2, 7.5, 8.6, 0.35, '暖水性名贵品种，需严格控制水温下限'),
            (3, 'SP-SHRIMP', '凡纳滨南美白对虾', '虾类', '快速生长期', 23.0, 31.0, 5.0, 7.6, 8.6, 0.30, '脱壳期对溶解氧、pH波动与氨氮尤为敏感'),
            (4, 'SP-CRAB', '中华绒螯蟹(大闸蟹)', '蟹类', '成蟹育肥期', 16.0, 28.0, 5.0, 7.2, 8.5, 0.45, '底栖甲壳类，需保持底部溶氧充足与水草生态平衡'),
        ]
        conn.executemany(
            """INSERT INTO species
            (species_id, species_code, species_name, category, growth_stage, temp_min_c, temp_max_c, do_min_mg_l, ph_min, ph_max, ammonia_max_mg_l, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            species_list,
        )

        # 4. 养殖批次 (4个在养批次)
        batches = [
            (1, 'BATCH-2026-A01', 1, 1, d_fmt(now - timedelta(days=45)), 12000, 600.0, d_fmt(now + timedelta(days=60)), 'ACTIVE', 'A01加州鲈秋季保供批次'),
            (2, 'BATCH-2026-A02', 2, 2, d_fmt(now - timedelta(days=60)), 8000, 480.0, d_fmt(now + timedelta(days=75)), 'ACTIVE', 'A02石斑鱼精品批次'),
            (3, 'BATCH-2026-B01', 3, 3, d_fmt(now - timedelta(days=35)), 80000, 160.0, d_fmt(now + timedelta(days=40)), 'ACTIVE', 'B01南美白对虾高产批次'),
            (4, 'BATCH-2026-B02', 4, 4, d_fmt(now - timedelta(days=50)), 15000, 375.0, d_fmt(now + timedelta(days=45)), 'ACTIVE', 'B02生态大闸蟹批次'),
        ]
        conn.executemany(
            """INSERT INTO culture_batches
            (batch_id, batch_code, pond_id, species_id, stocking_date, stocking_count, stocking_weight_kg, expected_harvest_date, status, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            batches,
        )

        # 5. 放养记录
        stockings = [
            (1, 1, 12000, 600.0, 50.0, '省级良种繁育中心', fmt(now - timedelta(days=45)), '张工', '鱼苗活力良好，消毒入池'),
            (2, 2, 8000, 480.0, 60.0, '南海海水种苗基地', fmt(now - timedelta(days=60)), '张工', '规格整齐'),
            (3, 3, 80000, 160.0, 2.0, 'SPF无特定病原虾苗场', fmt(now - timedelta(days=35)), '王工', 'P12淡化标粗苗'),
            (4, 4, 15000, 375.0, 25.0, '长江水系良种蟹苗基地', fmt(now - timedelta(days=50)), '李工', '扣蟹放养'),
        ]
        conn.executemany(
            """INSERT INTO stocking_records
            (batch_id, pond_id, stocking_count, stocking_weight_kg, avg_weight_g, fry_source, stocked_at, operator_name, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            stockings,
        )

        # 6. 投喂、生长、死亡与出塘记录
        feedings = []
        for day_offset in range(14, 0, -1):
            t_str = fmt(now - timedelta(days=day_offset, hours=2))
            feedings.extend([
                (1, 1, '加州鲈专用膨化料(48%蛋白)', 42.0, 9.5, t_str, '张工', '模拟日常投喂'),
                (2, 2, '海水鱼慢沉配合饲料', 34.0, 11.2, t_str, '张工', '模拟日常投喂'),
                (3, 3, '对虾2号全价配合料', 28.0, 10.0, t_str, '王工', '模拟日常投喂'),
                (4, 4, '河蟹生态育肥颗粒料', 22.0, 8.0, t_str, '李工', '模拟日常投喂'),
            ])
        conn.executemany(
            """INSERT INTO feeding_records
            (batch_id, pond_id, feed_type, feed_weight_kg, unit_price_cny, fed_at, operator_name, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            feedings,
        )

        growths = [
            (1, 1, fmt(now - timedelta(days=20)), 50, 185.0, 21.5, '张工', '中期抽样'),
            (1, 1, fmt(now - timedelta(days=2)), 50, 295.0, 25.8, '张工', '近期抽样，长势迅速'),
            (2, 2, fmt(now - timedelta(days=15)), 40, 240.0, 23.0, '张工', '中期抽样'),
            (2, 2, fmt(now - timedelta(days=1)), 40, 340.0, 27.2, '张工', '近期抽样'),
            (3, 3, fmt(now - timedelta(days=14)), 100, 9.5, 9.8, '王工', '中期抽样'),
            (3, 3, fmt(now - timedelta(days=1)), 100, 15.8, 12.1, '王工', '近期抽样'),
            (4, 4, fmt(now - timedelta(days=3)), 60, 115.0, 10.5, '李工', '育肥抽样'),
        ]
        conn.executemany(
            """INSERT INTO growth_records
            (batch_id, pond_id, sampled_at, sample_count, avg_weight_g, avg_length_cm, operator_name, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            growths,
        )

        mortalities = [
            (1, 1, 85, fmt(now - timedelta(days=30)), '入池初期应激损耗', '无害化处理', '张工'),
            (1, 1, 35, fmt(now - timedelta(days=10)), '个别机械擦伤', '无害化处理', '张工'),
            (2, 2, 60, fmt(now - timedelta(days=25)), '换水应激', '无害化处理', '张工'),
            (3, 3, 1200, fmt(now - timedelta(days=18)), '脱壳期自然损耗', '无害化处理', '王工'),
            (3, 3, 450, fmt(now - timedelta(days=1)), '夜间低氧轻度应激', '无害化处理', '王工'),
            (4, 4, 180, fmt(now - timedelta(days=15)), '蜕壳损耗', '无害化处理', '李工'),
        ]
        conn.executemany(
            """INSERT INTO mortality_records
            (batch_id, pond_id, dead_count, recorded_at, cause, disposal_method, operator_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            mortalities,
        )

        harvests = [
            (1, 1, 1500, 435.0, 36.0, 15660.0, fmt(now - timedelta(days=5)), '城配生鲜冷链中心', '张工'),
            (2, 2, 800, 272.0, 68.0, 18496.0, fmt(now - timedelta(days=3)), '智慧农贸直供中心', '张工'),
            (3, 3, 12000, 192.0, 52.0, 9984.0, fmt(now - timedelta(days=2)), '社区生鲜超市直采', '王工'),
        ]
        conn.executemany(
            """INSERT INTO harvest_records
            (batch_id, pond_id, harvest_count, total_weight_kg, unit_price_cny, total_amount_cny, harvested_at, buyer_name, operator_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            harvests,
        )

        # 7. 成本记录
        costs = [
            (1, 1, '苗种', 12000.0, fmt(now - timedelta(days=45)), '加州鲈大规格苗种采购', SOURCE_SIMULATED),
            (1, 1, '电费能耗', 3200.0, fmt(now - timedelta(days=7)), '循环水泵与纯氧机月度分摊电费', SOURCE_SIMULATED),
            (2, 2, '苗种', 16000.0, fmt(now - timedelta(days=60)), '珍珠龙胆石斑苗种采购', SOURCE_SIMULATED),
            (2, 2, '电费能耗', 3500.0, fmt(now - timedelta(days=7)), '恒温热泵与循环系统能耗', SOURCE_SIMULATED),
            (3, 3, '苗种', 6400.0, fmt(now - timedelta(days=35)), 'SPF虾苗采购', SOURCE_SIMULATED),
            (3, 3, '动保药品', 1450.0, fmt(now - timedelta(days=10)), '乳酸菌、有机酸及钙镁矿物补充剂', SOURCE_SIMULATED),
            (4, 4, '苗种', 9500.0, fmt(now - timedelta(days=50)), '优质扣蟹与伊乐藻种植', SOURCE_SIMULATED),
        ]
        conn.executemany(
            """INSERT INTO cost_records
            (batch_id, pond_id, cost_category, amount_cny, occurred_at, description, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            costs,
        )

        # 8. 预警规则 (alert_rules)
        rules = [
            (1, 'RULE-DO-LOW', '溶解氧过低高危预警', None, 'dissolved_oxygen_mg_l', 'LT', 5.0, 'mg/L', 'CRITICAL', 1, '溶解氧低于5.0 mg/L易引发浮头或脱壳期窒息风险'),
            (2, 'RULE-NH3-HIGH', '氨氮超标毒性预警', None, 'ammonia_mg_l', 'GT', 0.40, 'mg/L', 'HIGH', 1, '氨氮高于0.40 mg/L易导致鳃组织受损与摄食下降'),
            (3, 'RULE-TEMP-HIGH', '水温偏高预警', None, 'water_temp_c', 'GT', 30.5, '°C', 'MEDIUM', 1, '水温超过30.5°C加速耗氧并增加残饵腐败速率'),
            (4, 'RULE-TEMP-LOW', '水温偏低预警', None, 'water_temp_c', 'LT', 17.5, '°C', 'MEDIUM', 1, '水温低于17.5°C导致摄食明显减退'),
            (5, 'RULE-PH-LOW', 'pH值偏酸预警', None, 'ph', 'LT', 7.0, '', 'MEDIUM', 1, '水体偏酸影响甲壳类钙化及鱼类酸碱平衡'),
            (6, 'RULE-PH-HIGH', 'pH值偏碱预警', None, 'ph', 'GT', 8.7, '', 'MEDIUM', 1, 'pH偏高会显著提高分子态非离子氨毒性比例'),
        ]
        conn.executemany(
            """INSERT INTO alert_rules
            (rule_id, rule_code, rule_name, species_id, metric_name, comparison_op, threshold_value, unit, severity, is_enabled, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rules,
        )

        # 9. 设备档案 (覆盖在线、离线与故障状态)
        equipments = [
            (1, 'EQ-SEN-A01', 'A01多参数水质传感终端', '水质传感器', 1, 'A01池回水口', 'ONLINE', SOURCE_SIMULATED, fmt(now)),
            (2, 'EQ-OXY-A01', 'A01纳米微孔纯氧增氧机', '增氧机', 1, 'A01池底部中央', 'ONLINE', SOURCE_SIMULATED, fmt(now)),
            (3, 'EQ-SEN-A02', 'A02多参数水质传感终端', '水质传感器', 2, 'A02池回水口', 'ONLINE', SOURCE_SIMULATED, fmt(now)),
            (4, 'EQ-PMP-A02', 'A02变频循环水主泵', '循环水泵', 2, 'A区设备间2号位', 'ONLINE', SOURCE_SIMULATED, fmt(now)),
            (5, 'EQ-SEN-B01', 'B01浮标式水质监测仪', '水质传感器', 3, 'B01池中心浮标', 'ONLINE', SOURCE_SIMULATED, fmt(now)),
            (6, 'EQ-OXY-B01', 'B01叶轮式变频增氧机', '增氧机', 3, 'B01池东南侧', 'FAULT', SOURCE_SIMULATED, fmt(now - timedelta(hours=3))),
            (7, 'EQ-SEN-B02', 'B02蟹塘溶氧温度探头', '水质传感器', 4, 'B02池环沟区', 'OFFLINE', SOURCE_SIMULATED, fmt(now - timedelta(hours=8))),
            (8, 'EQ-FED-B02', 'B02轨道式智能投饵船', '自动投饵机', 4, 'B02池北岸码头', 'ONLINE', SOURCE_SIMULATED, fmt(now - timedelta(minutes=30))),
        ]
        conn.executemany(
            """INSERT INTO equipment
            (equipment_id, equipment_code, equipment_name, equipment_type, pond_id, install_location, status, source_type, last_reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            equipments,
        )

        # 10. 水质监测记录 (过去 24 小时，每 2 小时一条，覆盖正常、超阈值、缺失值场景)
        wq_rows = []
        for idx in range(12, -1, -1):
            t_rec = fmt(now - timedelta(hours=idx * 2))
            # Pond 1 (A01 加州鲈): 最新时刻氨氮略高触发预警 (0.46 mg/L)
            nh3_p1 = 0.46 if idx == 0 else round(0.22 + (12 - idx) * 0.015, 2)
            do_p1 = 6.4 if idx > 0 else 5.8
            wq_rows.append((1, 1, t_rec, round(24.5 + (idx % 3) * 0.2, 1), do_p1, 7.6, nh3_p1, SOURCE_SIMULATED, QUALITY_VALID))

            # Pond 2 (A02 石斑鱼): 全程稳定正常
            wq_rows.append((2, 2, t_rec, round(26.2 + (idx % 2) * 0.3, 1), round(6.8 - (idx % 3) * 0.1, 2), 7.9, 0.18, SOURCE_SIMULATED, QUALITY_VALID))

            # Pond 3 (B01 南美白对虾): 最新时刻溶解氧跌至 4.15 mg/L（低于 5.0 阈值触发紧急告警）
            do_p3 = 4.15 if idx == 0 else (4.85 if idx == 1 else round(6.1 - (12 - idx) * 0.08, 2))
            wq_rows.append((3, 3, t_rec, round(27.5 - (idx % 4) * 0.2, 1), do_p3, 8.1, 0.29, SOURCE_SIMULATED, QUALITY_VALID))

            # Pond 4 (B02 大闸蟹): 演示传感器部分指标缺失 (ammonia_mg_l 为 None)
            if idx == 0:
                wq_rows.append((4, 4, t_rec, 22.4, 6.2, 7.8, None, SOURCE_SIMULATED, QUALITY_MISSING))
            else:
                wq_rows.append((4, 4, t_rec, round(22.1 + (idx % 3) * 0.2, 1), 6.5, 7.8, 0.20, SOURCE_SIMULATED, QUALITY_VALID))

        conn.executemany(
            """INSERT INTO water_quality_records
            (pond_id, batch_id, recorded_at, water_temp_c, dissolved_oxygen_mg_l, ph, ammonia_mg_l, source_type, quality_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            wq_rows,
        )

        # 11. 告警记录与处理历史 (覆盖 NEW、ACKNOWLEDGED、RESOLVED、CLOSED 四种状态)
        alerts = [
            (
                1, 'ALT-2026-001', 3, 5, 1, '水质超阈值预警', 'dissolved_oxygen_mg_l', 4.15, 'mg/L', 5.0,
                'CRITICAL', 'NEW', fmt(now), None, None, None,
                None, None, None, None, SOURCE_SIMULATED
            ),
            (
                2, 'ALT-2026-002', 1, 1, 2, '水质超阈值预警', 'ammonia_mg_l', 0.46, 'mg/L', 0.40,
                'HIGH', 'ACKNOWLEDGED', fmt(now - timedelta(minutes=25)), fmt(now - timedelta(minutes=10)), None, None,
                '张工', '已加大生物滤池反冲洗频率并减少当餐投喂量30%，等待2小时后复测', None, None, SOURCE_SIMULATED
            ),
            (
                3, 'ALT-2026-003', 3, 6, None, '设备状态异常', '设备运行状态', None, '', None,
                'HIGH', 'ACKNOWLEDGED', fmt(now - timedelta(hours=3)), fmt(now - timedelta(hours=2)), None, None,
                '王工', '已开启备用增氧机，正在排查B01叶轮增氧机接触器故障', None, None, SOURCE_SIMULATED
            ),
            (
                4, 'ALT-2026-004', 2, 3, 3, '水质超阈值预警', 'water_temp_c', 30.8, '°C', 30.5,
                'MEDIUM', 'RESOLVED', fmt(now - timedelta(days=2)), fmt(now - timedelta(days=2, hours=-1)), fmt(now - timedelta(days=2, hours=-3)), None,
                '张工', '开启冷水机组调节车间环温并补充新水', '复测水温降至27.4°C，恢复正常范围', None, SOURCE_SIMULATED
            ),
            (
                5, 'ALT-2026-005', 4, 7, None, '数据长时间未更新', '传感器在线心跳', None, '', None,
                'LOW', 'CLOSED', fmt(now - timedelta(days=5)), fmt(now - timedelta(days=5, hours=-1)), fmt(now - timedelta(days=5, hours=-2)), fmt(now - timedelta(days=5, hours=-3)),
                '李工', '更换B02浮标太阳能供电稳压模块', '通讯恢复正常', '硬件维护完成并归档关闭', SOURCE_SIMULATED
            ),
        ]
        conn.executemany(
            """INSERT INTO alert_records
            (alert_id, alert_code, pond_id, equipment_id, rule_id, alert_type, metric_name, metric_value, unit, threshold_value,
             severity, status, triggered_at, acknowledged_at, resolved_at, closed_at,
             handler_name, latest_measure, retest_result, close_reason, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            alerts,
        )

        process_logs = [
            (1, 'CREATE', None, 'NEW', '系统预警引擎', '监测到B01池溶解氧 4.15 mg/L 低于阈值 5.0 mg/L，自动生成紧急告警', None, None, fmt(now)),
            (2, 'CREATE', None, 'NEW', '系统预警引擎', '监测到A01池氨氮 0.46 mg/L 高于阈值 0.40 mg/L，自动生成高危告警', None, None, fmt(now - timedelta(minutes=25))),
            (2, 'ACKNOWLEDGE', 'NEW', 'ACKNOWLEDGED', '张工', '确认告警，已加大生物滤池反冲洗频率并减料30%', None, '待2小时后复测', fmt(now - timedelta(minutes=10))),
            (4, 'CREATE', None, 'NEW', '系统预警引擎', '监测到A02池水温 30.8 °C 高于阈值 30.5 °C', None, None, fmt(now - timedelta(days=2))),
            (4, 'RESOLVE', 'ACKNOWLEDGED', 'RESOLVED', '张工', '开启冷水机组调节水温', 27.4, '复测水温27.4°C，恢复正常', fmt(now - timedelta(days=2, hours=-3))),
        ]
        conn.executemany(
            """INSERT INTO alert_process_records
            (alert_id, action_type, from_status, to_status, handler_name, action_measure, retest_value, retest_conclusion, processed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            process_logs,
        )

        # 12. 初始 AI 分析记录
        conn.execute(
            """INSERT INTO ai_analysis_records
            (pond_id, batch_id, alert_id, engine_version, input_summary, status_summary, cause_analysis, action_suggestions, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                3, 3, 1, 'RuleEngine-v1.0 (模拟数据辅助模式)',
                '养殖池: B01号南美白对虾精养池 | 批次: BATCH-2026-B01 | 当前溶解氧: 4.15 mg/L (阈值 >=5.0) | 氨氮: 0.29 mg/L | 水温: 27.5 °C',
                '【高危低氧预警】B01池溶解氧近4小时由 5.45 mg/L 持续下降至 4.15 mg/L，且关联设备 EQ-OXY-B01 处于故障状态。',
                '1. B01叶轮增氧机故障停机导致水体机械曝气量不足；2. 水温处于27.5°C较高水平，对虾处于快速生长期及夜间呼吸耗氧高峰。',
                '1. 立即启用备用增氧机或投放应急增氧颗粒（人工核查后执行，系统不自动操作设备）；2. 暂停当餐投喂，避免残饵加剧耗氧；3. 30分钟后复测底部溶解氧浓度。',
                fmt(now),
            ),
        )

        # 13. 系统设置
        settings = [
            ('data_mode', 'SIMULATED', 'DATA', '当前系统默认数据模式（SIMULATED=演示模拟模式，PRODUCTION=实测模式）'),
            ('ai_provider', 'RULE_TEMPLATE', 'AI', 'AI决策辅助引擎模式（RULE_TEMPLATE=本地规则与模板引擎，LLM_API=外部大模型接口）'),
            ('online_timeout_minutes', '120', 'EQUIPMENT', '设备在线判定超时时间（分钟），超过该时长未上报视为离线'),
            ('suppress_duplicate_alerts', 'true', 'ALERT', '是否开启同一池塘同一规则未关闭告警的重复抑制'),
            ('llm_api_base', 'https://api.deepseek.com/v1', 'AI', '大模型兼容接口地址 (支持 OpenAI / DeepSeek / 通义千问等)'),
            ('llm_model_name', 'deepseek-chat', 'AI', '大模型名称 (如 deepseek-chat / qwen-plus / gpt-4o-mini)'),
            ('llm_timeout_seconds', '15', 'AI', '大模型 API 请求超时秒数（超时自动降级至本地规则引擎）'),
        ]
        conn.executemany(
            "INSERT INTO system_settings (setting_key, setting_value, setting_group, description) VALUES (?, ?, ?, ?)",
            settings,
        )

        # 14. 操作日志
        conn.execute(
            "INSERT INTO operation_logs (module_name, action_type, target_ref, detail, operator_name) VALUES (?, ?, ?, ?, ?)",
            ('系统初始化', 'INIT_DEMO_DATA', 'SMART_AQUACULTURE_DB', '完成 20 张核心表结构创建与 SIMULATED 标准演示数据初始化', '系统初始化脚本'),
        )


def ensure_db_initialized() -> bool:
    """供 app.py 和各页面启动时调用：确保表结构存在，且空库时自动初始化演示数据。"""
    create_tables()
    if is_database_empty():
        seed_demo_data()
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="智渔云数据库安全初始化工具")
    parser.add_argument("--reset-demo", action="store_true", help="清空本地数据库并重新生成标准 SIMULATED 演示数据")
    args = parser.parse_args()

    if args.reset_demo:
        print("[init_db] 正在重置并重新生成标准演示数据...")
        reset_all_data()
        seed_demo_data()
        print("[init_db] 演示数据重置完成！")
    else:
        created = ensure_db_initialized()
        if created:
            print("[init_db] 检测到新环境，已完成建表与初始演示数据写入。")
        else:
            print("[init_db] 数据库表结构检查通过，保留现有业务数据。")


if __name__ == "__main__":
    main()
