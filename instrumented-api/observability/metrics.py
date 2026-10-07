"""Dependency-free Prometheus exposition, using atomic SQLite counters shared by workers.
A teaching exporter for a small lab; not a replacement for a mature client at scale.
"""
import math
import sqlite3
import time
from pathlib import Path

BUCKETS=(0.005,0.01,0.025,0.05,0.1,0.25,0.5,1.0,2.0,5.0,10.0)
ROUTES={'/api/targets','/api/history','/api/observations'}
METHODS={'GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS'}

def escape(value):
    return str(value).replace('\\','\\\\').replace('\n','\\n').replace('"','\\"')

def labels(**items):
    return '{'+','.join(f'{key}="{escape(value)}"' for key,value in items.items())+'}'

class Metrics:
    def __init__(self,path):
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        conn=self.connect()
        try:
            with conn:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('CREATE TABLE IF NOT EXISTS requests (method TEXT, route TEXT, status_class TEXT, value INTEGER, PRIMARY KEY(method,route,status_class))')
                conn.execute('CREATE TABLE IF NOT EXISTS latency (method TEXT, route TEXT, count INTEGER, total REAL, PRIMARY KEY(method,route))')
                conn.execute('CREATE TABLE IF NOT EXISTS bins (method TEXT, route TEXT, bin INTEGER, value INTEGER, PRIMARY KEY(method,route,bin))')
                conn.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value REAL)')
                conn.execute('INSERT OR IGNORE INTO metadata VALUES (?,?)',('started',time.time()))
        finally:conn.close()

    def connect(self):
        conn=sqlite3.connect(self.path,timeout=1)
        conn.execute('PRAGMA busy_timeout=1000')
        return conn

    def observe(self,method,path,status,duration):
        if path in ['/healthz','/readyz','/metrics']:return
        method=method if method in METHODS else 'OTHER'
        route=path if path in ROUTES else '__other__'
        if not isinstance(status,int) or not 100<=status<=599:status=500
        duration=float(duration)
        if not math.isfinite(duration) or duration<0:raise ValueError('Duration must be finite and nonnegative')
        status_class=str(status//100)+'xx'
        index=next((i for i,bucket in enumerate(BUCKETS) if duration<=bucket),len(BUCKETS))
        conn=self.connect()
        try:
            with conn:
                conn.execute('INSERT INTO requests VALUES (?,?,?,1) ON CONFLICT(method,route,status_class) DO UPDATE SET value=value+1',(method,route,status_class))
                conn.execute('INSERT INTO latency VALUES (?,?,1,?) ON CONFLICT(method,route) DO UPDATE SET count=count+1,total=total+excluded.total',(method,route,duration))
                conn.execute('INSERT INTO bins VALUES (?,?,?,1) ON CONFLICT(method,route,bin) DO UPDATE SET value=value+1',(method,route,index))
        finally:conn.close()

    def render(self,probe_rows=(),database_ok=True):
        conn=self.connect()
        try:
            # One snapshot prevents mismatched histogram counts during concurrent requests.
            conn.execute('BEGIN')
            requests=conn.execute('SELECT method,route,status_class,value FROM requests ORDER BY method,route,status_class').fetchall()
            hist=conn.execute('SELECT method,route,count,total FROM latency ORDER BY method,route').fetchall()
            bins=conn.execute('SELECT method,route,bin,value FROM bins').fetchall()
            started=conn.execute("SELECT value FROM metadata WHERE key='started'").fetchone()[0]
            conn.commit()
        finally:conn.close()
        output=['# HELP netops_http_requests_total Completed API requests, excluding probes and scrapes.',
                '# TYPE netops_http_requests_total counter']
        for method,route,status,count in requests:
            output.append('netops_http_requests_total'+labels(method=method,route=route,status_class=status)+' '+str(count))
        output+=['# HELP netops_http_request_duration_seconds API handling duration before telemetry commit.',
                 '# TYPE netops_http_request_duration_seconds histogram']
        bins={(m,r,i):v for m,r,i,v in bins}
        for method,route,count,total in hist:
            cumulative=0
            for i,bucket in enumerate(BUCKETS):
                cumulative+=bins.get((method,route,i),0)
                output.append('netops_http_request_duration_seconds_bucket'+labels(method=method,route=route,le=f'{bucket:g}')+' '+str(cumulative))
            output.append('netops_http_request_duration_seconds_bucket'+labels(method=method,route=route,le='+Inf')+' '+str(count))
            output.append('netops_http_request_duration_seconds_count'+labels(method=method,route=route)+' '+str(count))
            output.append('netops_http_request_duration_seconds_sum'+labels(method=method,route=route)+' '+format(total,'.12g'))
        output+=['# HELP netops_metrics_start_time_seconds Metrics store creation time, resets at container startup.',
                 '# TYPE netops_metrics_start_time_seconds gauge','netops_metrics_start_time_seconds '+str(started),
                 '# HELP netops_database_collect_success Whether shared probe observations could be read.',
                 '# TYPE netops_database_collect_success gauge','netops_database_collect_success '+('1' if database_ok else '0')]
        rows=list(probe_rows)
        output+=['# HELP netops_probe_targets_truncated More than twenty targets existed in the shared database.',
                 '# TYPE netops_probe_targets_truncated gauge','netops_probe_targets_truncated '+str(int(len(rows)>20))]
        for metric,description in [('netops_probe_healthy','Latest HTTP probe health, duplicated across API replicas.'),
                                    ('netops_probe_latency_seconds','Last HTTP probe latency in seconds.'),
                                    ('netops_probe_last_observed_timestamp_seconds','API receipt timestamp of last probe.')]:
            output+=['# HELP '+metric+' '+description,'# TYPE '+metric+' gauge']
            if database_ok:
                for row in rows[:20]:
                    target=row[1]
                    value={'netops_probe_healthy':int(bool(row[4])), 'netops_probe_latency_seconds':float(row[2])/1000,
                           'netops_probe_last_observed_timestamp_seconds':float(row[5])}[metric]
                    if math.isfinite(float(value)):
                        output.append(metric+labels(target=target)+' '+str(value))
        return '\n'.join(output)+'\n'
