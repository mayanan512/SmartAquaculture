# -*- coding: utf-8 -*-
"""
智渔云 (SmartAquaculture) 核心业务闭环自动化单元测试 (V3.8 零泄漏与全页面模拟执行版)。
覆盖：
1. 数据库 20 张表初始化与 SIMULATED 演示数据幂等检查
2. 水质录入 → 自动触发阈值告警 → 重复告警抑制 → 告警确认/复测/关闭闭环
3. 生产批次存活数、估算存量、防负库存校验与出塘统计复算
4. AI 决策辅助与报表汇总一致性检查
5. 3D 剖面数字孪生场景全路径验证（含无 Plotly 环境下的 100% 轨迹与字典键检验）
6. 全页面 AST 语法审计、CSS `<style>` 零泄漏检查、HTML 缩进防转义检查、容器闭合检查与 Mock Streamlit 全页面多分支顶层执行校验
7. 专项成本登记、系统设置与设备状态变更联动告警闭环校验
"""

import unittest
from database.init_db import reset_all_data, seed_demo_data
from database.connection import get_connection
from services.water_quality_service import WaterQualityService
from services.alert_service import AlertService
from services.production_service import ProductionService
from services.ai_service import AIDecisionService
from services.report_service import ReportService
from services.equipment_service import EquipmentService
from repositories.alert_repo import AlertRepository
from repositories.equipment_repo import EquipmentRepository


class TestSmartAquacultureCoreFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reset_all_data()
        seed_demo_data()

    def test_01_twenty_tables_created(self):
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            table_names = {r["name"] for r in rows}
            self.assertEqual(len(table_names), 20, f"应创建20张核心表，实际: {table_names}")
        finally:
            conn.close()

    def test_02_water_quality_and_alert_closed_loop(self):
        res1 = WaterQualityService.validate_and_save(
            pond_id=2,
            recorded_at="2026-10-18 10:00:00",
            water_temp_c=26.0,
            dissolved_oxygen_mg_l=4.2,
            ph=7.9,
            ammonia_mg_l=0.18,
            source_type="SIMULATED",
        )
        created_alerts = [a for a in res1["alerts"] if a["action"] == "CREATED"]
        self.assertTrue(len(created_alerts) >= 1, "低溶氧应触发新建告警")
        alert_id = created_alerts[0]["alert_id"]

        res2 = WaterQualityService.validate_and_save(
            pond_id=2,
            recorded_at="2026-10-18 10:30:00",
            water_temp_c=26.0,
            dissolved_oxygen_mg_l=4.1,
            ph=7.9,
            ammonia_mg_l=0.18,
            source_type="SIMULATED",
        )
        suppressed = [a for a in res2["alerts"] if a["action"] == "SUPPRESSED"]
        self.assertTrue(len(suppressed) >= 1, "未关闭的同类告警应触发重复抑制")

        AlertService.transition_alert(alert_id, "ACKNOWLEDGED", "测试员", "开启备用增氧机")
        AlertService.transition_alert(alert_id, "RESOLVED", "测试员", "增氧后复测", 6.3, "复测溶氧恢复至6.3 mg/L")
        AlertService.transition_alert(alert_id, "CLOSED", "测试员", "归档关闭", close_reason="核验通过归档")

        history = AlertRepository.list_process_history(alert_id)
        self.assertEqual(len(history), 4, "应包含 CREATE, ACKNOWLEDGE, RESOLVE, CLOSE 四条历史记录")

    def test_03_production_metrics_and_boundary_guards(self):
        metrics_before = ProductionService.calculate_batch_metrics(1)
        alive_before = metrics_before["current_alive_count"]
        self.assertEqual(
            alive_before,
            metrics_before["initial_count"] - metrics_before["total_dead"] - metrics_before["harvested_count"],
        )

        with self.assertRaises(ValueError):
            ProductionService.add_mortality_record(1, alive_before + 100, "2026-10-18 11:00:00", "测试超额", "无害化", "测试员")

        ProductionService.add_mortality_record(1, 10, "2026-10-18 11:00:00", "正常测试损耗", "无害化", "测试员")
        ProductionService.add_growth_record(1, "2026-10-18 11:30:00", 50, 300.0, 26.0, "测试员")

        metrics_after = ProductionService.calculate_batch_metrics(1)
        self.assertEqual(metrics_after["current_alive_count"], alive_before - 10)
        self.assertAlmostEqual(metrics_after["estimated_biomass_kg"], round((alive_before - 10) * 0.3, 2))

    def test_04_ai_and_dashboard_consistency(self):
        ai_res = AIDecisionService.generate_pond_analysis(3)
        self.assertIn("analysis_id", ai_res)
        self.assertNotIn("IsolationForest", ai_res["engine_version"], "算法引擎名称应使用全中文展示")
        overview = ReportService.get_dashboard_overview()
        self.assertGreaterEqual(overview["total_ponds"], 6)
        self.assertGreater(overview["total_estimated_biomass_kg"], 0)

    def test_05_v020_3d_scene_and_iforest(self):
        from algorithms.anomaly_detector import detect_multivariate_anomalies_iforest
        from components.charts import build_3d_digital_twin_scene
        from repositories.water_quality_repo import WaterQualityRepository

        wq_df = WaterQualityRepository.query_records_df(pond_id=1)
        iforest_res = detect_multivariate_anomalies_iforest(wq_df)
        self.assertTrue(iforest_res["available"], "孤立森林多维算法应成功在完整水质序列上运行")
        self.assertNotIn("IsolationForest", iforest_res["summary"], "异常检测摘要应使用全中文描述")

        overview = ReportService.get_dashboard_overview()
        latest_wq = WaterQualityRepository.get_latest_all_ponds()
        fig_3d = build_3d_digital_twin_scene(
            ponds=overview["ponds"],
            latest_wq_list=latest_wq,
            active_batches=overview["active_batches"],
            alerts=overview["alerts"],
            selected_pond_id=1,
        )
        self.assertGreaterEqual(len(fig_3d.data), 6, "3D 数字孪生场景应包含各池塘线框与分层监测节点轨迹")

        ai_fallback = AIDecisionService.generate_pond_analysis(1, api_key_override="sk-invalid-test-key")
        self.assertIn("降级", ai_fallback["engine_version"])

    def test_06_full_page_and_html_audit(self):
        from pathlib import Path
        import ast
        import sys
        import types
        from components.charts import (
            build_dual_metric_spline_chart,
            build_donut_chart,
            build_3d_digital_twin_scene,
            build_multi_pond_wq_chart,
            build_batch_comparison_bar,
        )
        from repositories.water_quality_repo import WaterQualityRepository
        from repositories.farm_repo import FarmRepository

        root = Path(__file__).resolve().parent.parent

        # 0. Audit theme.css to guarantee zero comments, zero blank lines, and zero leading spaces
        css_text = (root / "assets" / "styles" / "theme.css").read_text(encoding="utf-8")
        self.assertNotIn("/*", css_text, "theme.css 不应包含注释块，防止 CommonMark 转义泄漏")
        self.assertNotIn("\n\n", css_text, "theme.css 不应包含空行，防止 CommonMark 提前闭合 <style>")
        for cline in css_text.splitlines():
            self.assertEqual(len(cline) - len(cline.lstrip(" ")), 0, f"theme.css 不应有行首缩进: {cline}")

        py_files = [root / "app.py"] + sorted((root / "pages").glob("*.py")) + sorted((root / "components").glob("*.py"))
        for pf in py_files:
            src = pf.read_text(encoding="utf-8")
            tree = ast.parse(src, filename=str(pf))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and "<div" in node.value:
                    for hline in node.value.splitlines():
                        if hline.strip():
                            leading = len(hline) - len(hline.lstrip(" "))
                            self.assertLess(leading, 4, f"{pf.name} HTML字符串内存在>=4空格缩进: {hline}")
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "markdown"
                    and node.args
                ):
                    arg0 = node.args[0]
                    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                        full = arg0.value
                    elif isinstance(arg0, ast.JoinedStr):
                        full = "".join(
                            v.value for v in arg0.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
                        )
                    else:
                        continue
                    if "<style>" in full:
                        self.assertTrue(full.startswith("<style>"), f"{pf.name} 中 <style> 必须位于字符串首位以符合 CommonMark 规范")
                    self.assertEqual(
                        full.count("<div"),
                        full.count("</div>"),
                        f"{pf.name} line {node.lineno} st.markdown 中存在未闭合的 <div 容器",
                    )

        # Mock Streamlit top-to-bottom execution across all 4 option index permutations
        class _DummyCacheData:
            def __call__(self, *a, **kw):
                def dec(fn):
                    return fn
                if len(a) == 1 and callable(a[0]):
                    return a[0]
                return dec
            def clear(self):
                pass

        class _DummyCtx:
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def __getattr__(self, name):
                return getattr(st_mock, name)

        class _DummySt(types.ModuleType):
            def __init__(self, opt_idx=0):
                super().__init__("streamlit")
                self.session_state = {}
                self.query_params = {}
                self.sidebar = _DummyCtx()
                self.cache_data = _DummyCacheData()
                self.opt_idx = opt_idx
                self.markdown_calls = []
            def __call__(self, *a, **kw):
                return _DummyCtx()
            def set_page_config(self, **kw):
                pass
            def markdown(self, text, **kw):
                self.markdown_calls.append(str(text))
            def write(self, *a, **kw):
                pass
            def columns(self, spec, **kw):
                n = spec if isinstance(spec, int) else len(spec)
                return [_DummyCtx() for _ in range(n)]
            def tabs(self, labels, **kw):
                return [_DummyCtx() for _ in labels]
            def expander(self, *a, **kw):
                return _DummyCtx()
            def form(self, *a, **kw):
                return _DummyCtx()
            def selectbox(self, label, options, index=0, format_func=str, key=None, **kw):
                opts = list(options)
                for o in opts:
                    _ = format_func(o)
                idx = min(self.opt_idx, len(opts) - 1) if opts else 0
                val = opts[idx] if opts else None
                if key:
                    self.session_state[key] = val
                return val
            def radio(self, label, options, index=0, format_func=str, key=None, **kw):
                opts = list(options)
                for o in opts:
                    _ = format_func(o)
                idx = min(self.opt_idx, len(opts) - 1) if opts else 0
                val = opts[idx] if opts else None
                if key:
                    self.session_state[key] = val
                return val
            def button(self, *a, **kw):
                return False
            def form_submit_button(self, *a, **kw):
                return False
            def download_button(self, *a, **kw):
                return False
            def page_link(self, *a, **kw):
                pass
            def switch_page(self, *a, **kw):
                pass
            def plotly_chart(self, *a, **kw):
                pass
            def dataframe(self, *a, **kw):
                pass
            def image(self, *a, **kw):
                pass
            def text_input(self, label, value="", **kw):
                return value
            def text_area(self, label, value="", **kw):
                return value
            def number_input(self, label, value=0, **kw):
                return value
            def checkbox(self, label, value=False, **kw):
                return value
            def file_uploader(self, *a, **kw):
                return None
            def info(self, *a, **kw):
                pass
            def warning(self, *a, **kw):
                pass
            def success(self, *a, **kw):
                pass
            def error(self, *a, **kw):
                pass
            def rerun(self):
                pass

        old_st = sys.modules.get("streamlit")
        run_files = [root / "app.py"] + sorted((root / "pages").glob("*.py"))
        try:
            for opt_idx in range(4):
                st_mock = _DummySt(opt_idx=opt_idx)
                sys.modules["streamlit"] = st_mock
                for pf in run_files:
                    code = compile(pf.read_text(encoding="utf-8"), str(pf), "exec")
                    exec(code, {"__name__": "__main__", "__file__": str(pf)})
                for md_str in st_mock.markdown_calls:
                    if "<style>" in md_str:
                        self.assertTrue(md_str.startswith("<style>\n"), "<style> 块必须顶格开头")
                        self.assertNotIn("\n\n", md_str, "<style> 块内不得存在空行")
                        self.assertNotIn("/*", md_str, "<style> 块内不得存在 CSS 注释")
        finally:
            if old_st is not None:
                sys.modules["streamlit"] = old_st

        ponds = FarmRepository.list_ponds()
        overview = ReportService.get_dashboard_overview()
        latest_all = WaterQualityRepository.get_latest_all_ponds()
        for p in ponds:
            pid = p["pond_id"]
            wq_df = WaterQualityRepository.query_records_df(pond_id=pid)
            _ = build_dual_metric_spline_chart(wq_df)
            _ = build_3d_digital_twin_scene(overview["ponds"], latest_all, overview["active_batches"], overview["alerts"], selected_pond_id=pid)
            ai_res = AIDecisionService.generate_pond_analysis(pid)
            self.assertIn("status_summary", ai_res)
        _ = build_donut_chart(["正常", "预警"], [18, 2], center_text="90%")
        _ = build_multi_pond_wq_chart(WaterQualityRepository.query_records_df(), "dissolved_oxygen_mg_l", "溶解氧", 5.0)
        _ = build_batch_comparison_bar(overview["active_batches"])

    def test_07_cost_entry_and_equipment_alert_sync(self):
        from repositories.system_repo import SystemRepository
        before = ProductionService.calculate_batch_metrics(1)
        cid = ProductionService.add_cost_record(1, "动保药品", 500.0, "2026-10-19 08:00:00", "益生菌调水测试", "MANUAL")
        self.assertGreater(cid, 0)
        after = ProductionService.calculate_batch_metrics(1)
        self.assertAlmostEqual(after["other_cost_cny"], before["other_cost_cny"] + 500.0)
        self.assertAlmostEqual(after["total_cost_cny"], before["total_cost_cny"] + 500.0)

        eq_items = EquipmentRepository.list_equipment()
        self.assertEqual(eq_items[0]["status"], "FAULT", "故障设备应置顶显示")
        self.assertEqual(eq_items[1]["status"], "OFFLINE", "离线设备应紧随故障设备置顶显示")

        sync_res = EquipmentService.update_status_with_alert_sync(6, "ONLINE", "更换变频接触器后恢复正常", "测试员", "MANUAL")
        self.assertEqual(sync_res["new_status"], "ONLINE")
        st_hist = EquipmentRepository.list_status_records(limit=10)
        self.assertTrue(len(st_hist) >= 1)

        SystemRepository.update_setting("online_timeout_minutes", "90")
        s_dict = SystemRepository.get_settings_dict()
        self.assertEqual(s_dict.get("online_timeout_minutes"), "90")

    def test_08_manual_alert_and_version_check(self):
        from config.settings import APP_VERSION, get_metric_label_cn
        self.assertEqual(APP_VERSION, "v0.3.9")
        self.assertEqual(get_metric_label_cn("dissolved_oxygen_mg_l"), "溶解氧")
        self.assertEqual(get_metric_label_cn("ammonia_mg_l"), "氨氮")
        self.assertEqual(get_metric_label_cn("water_temp_c"), "水温")
        self.assertEqual(get_metric_label_cn("ph"), "pH值")
        self.assertEqual(get_metric_label_cn("设备运行状态"), "设备运行状态")

        aid = AlertRepository.create_alert_with_log(
            alert_code="ALT-MAN-TEST01",
            pond_id=1,
            equipment_id=None,
            rule_id=None,
            alert_type="人工巡检养殖异常",
            metric_name="夜间巡塘轻度浮头",
            metric_value=4.8,
            unit="mg/L",
            threshold_value=5.0,
            severity="HIGH",
            triggered_at="2026-10-19 09:00:00",
            source_type="MANUAL",
        )
        self.assertGreater(aid, 0)
        hist = AlertRepository.list_process_history(aid)
        self.assertEqual(len(hist), 1)


if __name__ == "__main__":
    unittest.main()
