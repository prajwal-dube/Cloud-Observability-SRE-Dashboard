#!/usr/bin/env python3
import argparse
import json
from urllib.parse import urlencode
from urllib.request import urlopen
p=argparse.ArgumentParser();p.add_argument('--prometheus',default='http://127.0.0.1:9090');p.add_argument('--grafana',default='http://127.0.0.1:3000');args=p.parse_args()
def query(expr):
    with urlopen(args.prometheus+'/api/v1/query?'+urlencode({'query':expr}),timeout=5) as response:payload=json.load(response)
    if payload.get('status')!='success':raise SystemExit('Prometheus query failed')
    return payload['data']['result']
up=query('up{job="netops-api",namespace="netops"}')
if not up or not any(float(s['value'][1])==1 for s in up):raise SystemExit('No healthy NetOps scrape target; check instrumentation/selectors/network policy')
requests=query('netops_http_requests_total{job="netops-api",namespace="netops"}')
if not requests:raise SystemExit('No API request metrics yet; request /api/targets and wait one scrape interval')
with urlopen(args.grafana+'/api/health',timeout=5) as response:
    if json.load(response).get('database')!='ok':raise SystemExit('Grafana health failed')
print('PASS: a NetOps metrics target is up, request metrics exist, and Grafana responds. This does not validate dashboard rendering or notification delivery.')
