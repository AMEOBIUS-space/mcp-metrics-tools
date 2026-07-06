"""Tests for MCP Metrics Tools — counters, gauges, histograms, timers, export."""
import json, pytest, os, sys, time
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.server import MCPMetricsToolsServer, TOOL_DEFS
from src.metrics_engine import MetricsEngine

class TestToolDefs:
    def test_names(self):
        for t in TOOL_DEFS: assert "name" in t and len(t["name"])>0
    def test_descs(self):
        for t in TOOL_DEFS: assert "description" in t and len(t["description"])>10
    def test_schema(self):
        for t in TOOL_DEFS: assert "inputSchema" in t and t["inputSchema"]["type"]=="object"
    def test_count(self):
        assert len(TOOL_DEFS)==19
    def test_required(self):
        names={t["name"] for t in TOOL_DEFS}
        expected={"counter_inc","counter_get","counter_reset","gauge_set","gauge_get","gauge_inc","gauge_dec","histogram_observe","histogram_stats","timer_start","timer_stop","timer_stats","list_counters","list_gauges","list_histograms","list_timers","export","stats","reset"}
        assert names==expected

class TestManifest:
    def test_manifest(self):
        s=MCPMetricsToolsServer();m=s.manifest()
        assert m["server"]["name"]=="mcp-metrics-tools"
        assert len(m["tools"])==19

class TestCounters:
    def test_inc_get(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"requests")
        MetricsEngine.counter_inc(r,"requests",by=5)
        assert MetricsEngine.counter_get(r,"requests")["value"]==6
    def test_labels(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"requests",labels="method=GET")
        MetricsEngine.counter_inc(r,"requests",labels="method=POST")
        assert MetricsEngine.counter_get(r,"requests",labels="method=GET")["value"]==1
        assert MetricsEngine.counter_get(r,"requests",labels="method=POST")["value"]==1
    def test_not_found(self):
        r=MetricsEngine.create_registry()
        assert MetricsEngine.counter_get(r,"nonexistent")["found"] is False
    def test_reset(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"x",10)
        result=MetricsEngine.counter_reset(r,"x")
        assert result["old_value"]==10

class TestGauges:
    def test_set_get(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.gauge_set(r,"temp",72.5)
        assert MetricsEngine.gauge_get(r,"temp")["value"]==72.5
    def test_inc_dec(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.gauge_set(r,"count",10)
        MetricsEngine.gauge_inc(r,"count",5)
        assert MetricsEngine.gauge_get(r,"count")["value"]==15
        MetricsEngine.gauge_dec(r,"count",3)
        assert MetricsEngine.gauge_get(r,"count")["value"]==12
    def test_not_found(self):
        r=MetricsEngine.create_registry()
        assert MetricsEngine.gauge_get(r,"nonexistent")["found"] is False

class TestHistograms:
    def test_observe_stats(self):
        r=MetricsEngine.create_registry()
        for v in [1,2,3,4,5]:
            MetricsEngine.histogram_observe(r,"latency",v)
        s=MetricsEngine.histogram_stats(r,"latency")
        assert s["count"]==5
        assert s["min"]==1
        assert s["max"]==5
        assert s["mean"]==3.0
    def test_empty(self):
        r=MetricsEngine.create_registry()
        s=MetricsEngine.histogram_stats(r,"nonexistent")
        assert s["count"]==0

class TestTimers:
    def test_start_stop(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.timer_start(r,"op")
        time.sleep(0.01)
        result=MetricsEngine.timer_stop(r,"op")
        assert result["elapsed"]>0
    def test_not_started(self):
        r=MetricsEngine.create_registry()
        result=MetricsEngine.timer_stop(r,"nonexistent")
        assert result["success"] is False
    def test_stats(self):
        r=MetricsEngine.create_registry()
        for _ in range(3):
            MetricsEngine.timer_start(r,"op")
            time.sleep(0.001)
            MetricsEngine.timer_stop(r,"op")
        s=MetricsEngine.timer_stats(r,"op")
        assert s["count"]==3

class TestLists:
    def test_list_counters(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"a")
        MetricsEngine.counter_inc(r,"b")
        assert MetricsEngine.list_counters(r)["count"]==2
    def test_list_gauges(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.gauge_set(r,"x",1)
        assert MetricsEngine.list_gauges(r)["count"]==1
    def test_list_histograms(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.histogram_observe(r,"h",1)
        assert MetricsEngine.list_histograms(r)["count"]==1
    def test_list_timers(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.timer_start(r,"t")
        MetricsEngine.timer_stop(r,"t")
        assert MetricsEngine.list_timers(r)["count"]==1

class TestExport:
    def test_json(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"x",5)
        result=MetricsEngine.export(r,"json")
        assert result["format"]=="json"
        assert '"x": 5' in result["data"]
    def test_prometheus(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"requests")
        result=MetricsEngine.export(r,"prometheus")
        assert "requests" in result["data"]
    def test_unknown(self):
        r=MetricsEngine.create_registry()
        result=MetricsEngine.export(r,"xml")
        assert result["success"] is False

class TestStatsReset:
    def test_stats(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"a")
        MetricsEngine.gauge_set(r,"g",1)
        s=MetricsEngine.stats(r)
        assert s["counter_count"]==1
        assert s["gauge_count"]==1
    def test_reset(self):
        r=MetricsEngine.create_registry()
        MetricsEngine.counter_inc(r,"a")
        result=MetricsEngine.reset(r)
        assert result["reset"]["counter_count"]==1
        assert MetricsEngine.stats(r)["counter_count"]==0

class TestDispatch:
    def test_unknown(self):
        s=MCPMetricsToolsServer();assert "error" in json.loads(s.handle_tool_call("nope",{}))
    def test_missing(self):
        s=MCPMetricsToolsServer();assert "error" in json.loads(s.handle_tool_call("counter_inc",{}))
    def test_counter_dispatch(self):
        s=MCPMetricsToolsServer()
        r=json.loads(s.handle_tool_call("counter_inc",{"name":"test","by":3}))
        assert r["value"]==3

class TestSTDIO:
    def test_manifest_flag(self,capsys):
        from src.server import main
        with patch("sys.argv",["server","--manifest"]):main()
        parsed=json.loads(capsys.readouterr().out.strip())
        assert parsed["server"]["name"]=="mcp-metrics-tools"
