"""Metrics engine — zero dependencies.

Uses only Python stdlib (time, json, collections, math).
Provides counters, gauges, histograms, timers, summaries, export.
"""
import time
import json
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional


class MetricsEngine:
    """Metrics operations with zero external dependencies."""

    @staticmethod
    def create_registry() -> Dict:
        return {"counters": {}, "gauges": {}, "histograms": {}, "timers": {}, "summaries": {}}

    @staticmethod
    def counter_inc(reg: Dict, name: str, by: int = 1, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["counters"]:
            reg["counters"][key] = {"name": name, "labels": labels, "value": 0, "created": time.time()}
        reg["counters"][key]["value"] += by
        return {"success": True, "name": name, "labels": labels, "value": reg["counters"][key]["value"]}

    @staticmethod
    def counter_get(reg: Dict, name: str, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["counters"]:
            return {"success": True, "name": name, "labels": labels, "value": 0, "found": False}
        return {"success": True, "name": name, "labels": labels, "value": reg["counters"][key]["value"], "found": True}

    @staticmethod
    def counter_reset(reg: Dict, name: str, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key in reg["counters"]:
            old = reg["counters"][key]["value"]
            reg["counters"][key]["value"] = 0
            return {"success": True, "name": name, "old_value": old, "new_value": 0}
        return {"success": False, "error": f"Counter '{key}' not found"}

    @staticmethod
    def gauge_set(reg: Dict, name: str, value: float, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        old = reg["gauges"].get(key, {}).get("value")
        reg["gauges"][key] = {"name": name, "labels": labels, "value": value, "updated": time.time()}
        return {"success": True, "name": name, "labels": labels, "old_value": old, "new_value": value}

    @staticmethod
    def gauge_get(reg: Dict, name: str, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["gauges"]:
            return {"success": True, "name": name, "value": None, "found": False}
        return {"success": True, "name": name, "value": reg["gauges"][key]["value"], "found": True}

    @staticmethod
    def gauge_inc(reg: Dict, name: str, by: float = 1, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["gauges"]:
            reg["gauges"][key] = {"name": name, "labels": labels, "value": 0, "updated": time.time()}
        reg["gauges"][key]["value"] += by
        return {"success": True, "name": name, "value": reg["gauges"][key]["value"]}

    @staticmethod
    def gauge_dec(reg: Dict, name: str, by: float = 1, labels: str = "") -> Dict:
        return MetricsEngine.gauge_inc(reg, name, -by, labels)

    @staticmethod
    def histogram_observe(reg: Dict, name: str, value: float, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["histograms"]:
            reg["histograms"][key] = {"name": name, "labels": labels, "values": [], "count": 0, "sum": 0}
        h = reg["histograms"][key]
        h["values"].append(value)
        h["count"] += 1
        h["sum"] += value
        if len(h["values"]) > 10000:
            h["values"] = h["values"][-10000:]
        return {"success": True, "name": name, "count": h["count"]}

    @staticmethod
    def histogram_stats(reg: Dict, name: str, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["histograms"]:
            return {"success": True, "name": name, "count": 0}
        h = reg["histograms"][key]
        vals = sorted(h["values"])
        n = len(vals)
        if n == 0:
            return {"success": True, "name": name, "count": 0}
        return {
            "success": True, "name": name, "count": n, "sum": round(h["sum"], 6),
            "min": vals[0], "max": vals[-1], "mean": round(h["sum"] / n, 6),
            "median": round(vals[n // 2], 6),
            "p50": round(vals[n // 2], 6),
            "p90": round(vals[min(int(n * 0.9), n - 1)], 6),
            "p95": round(vals[min(int(n * 0.95), n - 1)], 6),
            "p99": round(vals[min(int(n * 0.99), n - 1)], 6),
            "stddev": round(math.sqrt(sum((v - h["sum"] / n) ** 2 for v in vals) / n), 6) if n > 1 else 0,
        }

    @staticmethod
    def timer_start(reg: Dict, name: str, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["timers"]:
            reg["timers"][key] = {"name": name, "labels": labels, "start": time.time(), "durations": []}
        else:
            reg["timers"][key]["start"] = time.time()
        return {"success": True, "name": name, "started": True}

    @staticmethod
    def timer_stop(reg: Dict, name: str, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["timers"] or reg["timers"][key]["start"] is None:
            return {"success": False, "error": f"Timer '{key}' not started"}
        elapsed = time.time() - reg["timers"][key]["start"]
        reg["timers"][key]["durations"].append(elapsed)
        reg["timers"][key]["start"] = None
        if len(reg["timers"][key]["durations"]) > 10000:
            reg["timers"][key]["durations"] = reg["timers"][key]["durations"][-10000:]
        return {"success": True, "name": name, "elapsed": round(elapsed, 6), "elapsed_ms": round(elapsed * 1000, 3), "count": len(reg["timers"][key]["durations"])}

    @staticmethod
    def timer_stats(reg: Dict, name: str, labels: str = "") -> Dict:
        key = f"{name}:{labels}" if labels else name
        if key not in reg["timers"]:
            return {"success": True, "name": name, "count": 0}
        durations = reg["timers"][key]["durations"]
        if not durations:
            return {"success": True, "name": name, "count": 0}
        s = sorted(durations)
        n = len(s)
        return {
            "success": True, "name": name, "count": n,
            "min_ms": round(s[0] * 1000, 3), "max_ms": round(s[-1] * 1000, 3),
            "mean_ms": round(sum(s) / n * 1000, 3),
            "median_ms": round(s[n // 2] * 1000, 3),
            "p99_ms": round(s[min(int(n * 0.99), n - 1)] * 1000, 3),
        }

    @staticmethod
    def list_counters(reg: Dict) -> Dict:
        return {"success": True, "counters": {k: v["value"] for k, v in reg["counters"].items()}, "count": len(reg["counters"])}

    @staticmethod
    def list_gauges(reg: Dict) -> Dict:
        return {"success": True, "gauges": {k: v["value"] for k, v in reg["gauges"].items()}, "count": len(reg["gauges"])}

    @staticmethod
    def list_histograms(reg: Dict) -> Dict:
        return {"success": True, "histograms": {k: v["count"] for k, v in reg["histograms"].items()}, "count": len(reg["histograms"])}

    @staticmethod
    def list_timers(reg: Dict) -> Dict:
        return {"success": True, "timers": {k: len(v["durations"]) for k, v in reg["timers"].items()}, "count": len(reg["timers"])}

    @staticmethod
    def export(reg: Dict, format: str = "json") -> Dict:
        data = {
            "counters": {k: v["value"] for k, v in reg["counters"].items()},
            "gauges": {k: v["value"] for k, v in reg["gauges"].items()},
            "histograms": {k: {"count": v["count"], "sum": v["sum"]} for k, v in reg["histograms"].items()},
            "timers": {k: len(v["durations"]) for k, v in reg["timers"].items()},
        }
        if format == "json":
            return {"success": True, "format": "json", "data": json.dumps(data, indent=2, default=str)}
        elif format == "prometheus":
            lines = []
            for k, v in reg["counters"].items():
                lines.append(f"# TYPE {v['name']} counter")
                lines.append(f"{v['name']}{{{v['labels']}}} {v['value']}")
            for k, v in reg["gauges"].items():
                lines.append(f"# TYPE {v['name']} gauge")
                lines.append(f"{v['name']}{{{v['labels']}}} {v['value']}")
            return {"success": True, "format": "prometheus", "data": "\n".join(lines)}
        return {"success": False, "error": f"Unknown format: {format}"}

    @staticmethod
    def stats(reg: Dict) -> Dict:
        return {
            "success": True,
            "counter_count": len(reg["counters"]),
            "gauge_count": len(reg["gauges"]),
            "histogram_count": len(reg["histograms"]),
            "timer_count": len(reg["timers"]),
            "total_observations": sum(v["count"] for v in reg["histograms"].values()) + sum(len(v["durations"]) for v in reg["timers"].values()),
        }

    @staticmethod
    def reset(reg: Dict) -> Dict:
        old = MetricsEngine.stats(reg)
        reg["counters"] = {}
        reg["gauges"] = {}
        reg["histograms"] = {}
        reg["timers"] = {}
        reg["summaries"] = {}
        return {"success": True, "reset": old}
