import concurrent.futures
import math
import multiprocessing
import re
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'instrumented-api'))
from observability.metrics import Metrics,BUCKETS,labels

def process_writer(path,count):
    metrics=Metrics(path)
    for _ in range(count):metrics.observe('GET','/api/targets',200,0.012)

def samples(text,name):
    return [(line.split(' ',1)[0],float(line.rsplit(' ',1)[1])) for line in text.splitlines() if line.startswith(name+'{') or line.startswith(name+' ')]

class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'metrics.db';self.metrics=Metrics(self.path)
    def tearDown(self):self.temp.cleanup()
    def test_counter_statuses_and_histogram(self):
        for duration,status in [(0.001,200),(0.010,200),(0.2,500),(15,503)]:self.metrics.observe('GET','/api/targets',status,duration)
        text=self.metrics.render()
        self.assertEqual(sum(v for _,v in samples(text,'netops_http_requests_total')),4)
        self.assertEqual(samples(text,'netops_http_request_duration_seconds_count')[0][1],4)
        self.assertAlmostEqual(samples(text,'netops_http_request_duration_seconds_sum')[0][1],15.211)
        buckets=[v for _,v in samples(text,'netops_http_request_duration_seconds_bucket')]
        self.assertEqual(buckets,sorted(buckets));self.assertEqual(buckets[-1],4)
        self.assertIn('le="0.01"} 2',text);self.assertIn('# TYPE netops_http_request_duration_seconds histogram',text)
    def test_health_and_metrics_requests_are_excluded(self):
        for path in ['/healthz','/readyz','/metrics']:self.metrics.observe('GET',path,200,0.1)
        self.assertEqual(samples(self.metrics.render(),'netops_http_requests_total'),[])
    def test_routes_and_methods_have_bounded_cardinality(self):
        for i in range(100):self.metrics.observe('UNTRUSTED'+str(i),'/dynamic/'+str(i),404,0.01)
        counts=samples(self.metrics.render(),'netops_http_requests_total')
        self.assertEqual(len(counts),1);self.assertIn('method="OTHER",route="__other__"',counts[0][0]);self.assertEqual(counts[0][1],100)
    def test_invalid_durations_never_create_samples(self):
        for value in [-1,float('nan'),float('inf')]:
            with self.subTest(value=value),self.assertRaises(ValueError):self.metrics.observe('GET','/api/targets',200,value)
        self.assertEqual(samples(self.metrics.render(),'netops_http_requests_total'),[])
    def test_labels_escape_quotes_backslashes_and_newlines(self):
        self.assertEqual(labels(target='a"b\\c\n'),'{target="a\\"b\\\\c\\n"}')
    def test_probe_gauges_and_target_cap(self):
        rows=[('id','api',250,200,True,1234)]
        text=self.metrics.render(rows)
        self.assertIn('netops_probe_healthy{target="api"} 1',text)
        self.assertIn('netops_probe_latency_seconds{target="api"} 0.25',text)
        self.assertIn('netops_probe_last_observed_timestamp_seconds{target="api"} 1234.0',text)
        rows=[('id','target'+str(i),1,200,True,1234) for i in range(25)]
        text=self.metrics.render(rows)
        self.assertEqual(len(samples(text,'netops_probe_healthy')),20)
        self.assertIn('netops_probe_targets_truncated 1',text)
    def test_database_failure_does_not_falsely_export_health(self):
        text=self.metrics.render([],database_ok=False)
        self.assertIn('netops_database_collect_success 0',text)
        self.assertEqual(samples(text,'netops_probe_healthy'),[])
    def test_shared_threaded_transactions(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:self.metrics.observe('GET','/api/targets',200,0.001),range(100)))
        self.assertEqual(sum(v for _,v in samples(self.metrics.render(),'netops_http_requests_total')),100)
    def test_shared_process_transactions(self):
        context=multiprocessing.get_context('spawn')
        workers=[context.Process(target=process_writer,args=(str(self.path),40)) for _ in range(3)]
        for worker in workers:worker.start()
        for worker in workers:worker.join(timeout=15);self.assertEqual(worker.exitcode,0)
        self.assertEqual(samples(self.metrics.render(),'netops_http_request_duration_seconds_count')[0][1],120)
