"""MCP Server for metrics — counters, gauges, histograms, timers, export."""
import json, sys, argparse
from typing import Any, Dict, List, Optional
from .metrics_engine import MetricsEngine

_store = MetricsEngine.create_registry()

TOOL_DEFS = [
    {"name":"counter_inc","description":"Increment a counter.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"by":{"type":"integer","default":1},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"counter_get","description":"Get a counter value.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"counter_reset","description":"Reset a counter to zero.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"gauge_set","description":"Set a gauge value.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"value":{"type":"number"},"labels":{"type":"string","default":""}},"required":["name","value"]}},
    {"name":"gauge_get","description":"Get a gauge value.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"gauge_inc","description":"Increment a gauge.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"by":{"type":"number","default":1},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"gauge_dec","description":"Decrement a gauge.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"by":{"type":"number","default":1},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"histogram_observe","description":"Observe a value in a histogram.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"value":{"type":"number"},"labels":{"type":"string","default":""}},"required":["name","value"]}},
    {"name":"histogram_stats","description":"Get histogram statistics (min, max, mean, percentiles).","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"timer_start","description":"Start a timer.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"timer_stop","description":"Stop a timer and record elapsed time.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"timer_stats","description":"Get timer statistics.","inputSchema":{"type":"object","properties":{"name":{"type":"string"},"labels":{"type":"string","default":""}},"required":["name"]}},
    {"name":"list_counters","description":"List all counters.","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"list_gauges","description":"List all gauges.","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"list_histograms","description":"List all histograms.","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"list_timers","description":"List all timers.","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"export","description":"Export metrics as JSON or Prometheus format.","inputSchema":{"type":"object","properties":{"format":{"type":"string","default":"json"}},"required":[]}},
    {"name":"stats","description":"Get overall metrics statistics.","inputSchema":{"type":"object","properties":{},"required":[]}},
    {"name":"reset","description":"Reset all metrics.","inputSchema":{"type":"object","properties":{},"required":[]}},
]

class MCPMetricsToolsServer:
    def __init__(self,name="mcp-metrics-tools",version="1.0.0"):
        self.name=name;self.version=version
    def list_tools(self):return TOOL_DEFS
    def manifest(self):return{"server":{"name":self.name,"version":self.version},"capabilities":{"tools":{"listChanged":False},"resources":{},"prompts":{}},"tools":self.list_tools()}
    def handle_tool_call(self,name,args):
        try:
            L=args.get("labels","")
            if name=="counter_inc":return json.dumps(MetricsEngine.counter_inc(_store,args["name"],args.get("by",1),L))
            elif name=="counter_get":return json.dumps(MetricsEngine.counter_get(_store,args["name"],L))
            elif name=="counter_reset":return json.dumps(MetricsEngine.counter_reset(_store,args["name"],L))
            elif name=="gauge_set":return json.dumps(MetricsEngine.gauge_set(_store,args["name"],args["value"],L))
            elif name=="gauge_get":return json.dumps(MetricsEngine.gauge_get(_store,args["name"],L))
            elif name=="gauge_inc":return json.dumps(MetricsEngine.gauge_inc(_store,args["name"],args.get("by",1),L))
            elif name=="gauge_dec":return json.dumps(MetricsEngine.gauge_dec(_store,args["name"],args.get("by",1),L))
            elif name=="histogram_observe":return json.dumps(MetricsEngine.histogram_observe(_store,args["name"],args["value"],L))
            elif name=="histogram_stats":return json.dumps(MetricsEngine.histogram_stats(_store,args["name"],L))
            elif name=="timer_start":return json.dumps(MetricsEngine.timer_start(_store,args["name"],L))
            elif name=="timer_stop":return json.dumps(MetricsEngine.timer_stop(_store,args["name"],L))
            elif name=="timer_stats":return json.dumps(MetricsEngine.timer_stats(_store,args["name"],L))
            elif name=="list_counters":return json.dumps(MetricsEngine.list_counters(_store))
            elif name=="list_gauges":return json.dumps(MetricsEngine.list_gauges(_store))
            elif name=="list_histograms":return json.dumps(MetricsEngine.list_histograms(_store))
            elif name=="list_timers":return json.dumps(MetricsEngine.list_timers(_store))
            elif name=="export":return json.dumps(MetricsEngine.export(_store,args.get("format","json")))
            elif name=="stats":return json.dumps(MetricsEngine.stats(_store))
            elif name=="reset":return json.dumps(MetricsEngine.reset(_store))
            else:return json.dumps({"error":f"Unknown tool: {name}"})
        except KeyError as e:return json.dumps({"error":f"Missing required parameter: {e}","tool":name})
        except Exception as e:return json.dumps({"error":str(e),"tool":name})

def _run_stdio():
    server=MCPMetricsToolsServer()
    for line in sys.stdin:
        line=line.strip()
        if not line:continue
        try:request=json.loads(line)
        except json.JSONDecodeError:print(json.dumps({"jsonrpc":"2.0","error":{"code":-32700,"message":"Parse error"}}),flush=True);continue
        method=request.get("method","");req_id=request.get("id");params=request.get("params",{})
        if method=="initialize":response={"jsonrpc":"2.0","id":req_id,"result":{"server":server.name,"version":server.version}}
        elif method=="tools/list":response={"jsonrpc":"2.0","id":req_id,"result":{"tools":server.list_tools()}}
        elif method=="tools/call":
            result=server.handle_tool_call(params.get("name",""),params.get("arguments",{}))
            response={"jsonrpc":"2.0","id":req_id,"result":{"content":[{"type":"text","text":result}]}}
        elif method=="shutdown":response={"jsonrpc":"2.0","id":req_id,"result":{}};print(json.dumps(response),flush=True);break
        else:response={"jsonrpc":"2.0","id":req_id,"error":{"code":-32601,"message":f"Method not found: {method}"}}
        print(json.dumps(response),flush=True)

def main():
    parser=argparse.ArgumentParser(description="MCP Metrics Tools Server")
    parser.add_argument("--stdio",action="store_true")
    parser.add_argument("--manifest",action="store_true")
    args=parser.parse_args()
    if args.manifest:print(json.dumps(MCPMetricsToolsServer().manifest(),indent=2))
    elif args.stdio:_run_stdio()
    else:parser.print_help()

if __name__=="__main__":main()
