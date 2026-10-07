import io
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request,urlopen
from wsgiref.simple_server import make_server,WSGIRequestHandler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'instrumented-api'))
from app.db import Database
from app.main import Application
from observability.metrics import Metrics
from observability.wsgi import ObservedApplication

class Quiet(WSGIRequestHandler):
    def log_message(self,*_):pass

class ObservedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'SQLITE_PATH':str(self.folder/'app.db'),'INGEST_TOKEN':'unit-test-token'});self.env.start()
        self.db=Database();self.db.migrate();self.metrics=Metrics(self.folder/'metrics.db')
        self.app=ObservedApplication(Application(self.db),self.metrics,self.db.latest)
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def call(self,path='/api/targets',method='GET',payload=None,app=None):
        raw=json.dumps(payload).encode() if payload is not None else b''
        captured=[]
        env={'PATH_INFO':path,'REQUEST_METHOD':method,'wsgi.input':io.BytesIO(raw),'CONTENT_LENGTH':str(len(raw)),
             'CONTENT_TYPE':'application/json','HTTP_AUTHORIZATION':'Bearer unit-test-token'}
        body=b''.join((app or self.app)(env,lambda status,headers,exc_info=None:captured.append((status,headers))))
        return int(captured[0][0].split()[0]),body,captured[0][1]
    def test_actual_project1_api_is_instrumented(self):
        self.assertEqual(self.call()[0],200)
        text=self.call('/metrics')[1].decode()
        self.assertIn('netops_http_requests_total{method="GET",route="/api/targets",status_class="2xx"} 1',text)
        self.assertEqual(self.call('/metrics')[0],200)
        self.assertIn(' 1',self.metrics.render())
    def test_ingestion_remains_authenticated_and_exposes_shared_probe(self):
        status,_,_=self.call('/api/observations','POST',{'target':'api','latency_ms':20,'status_code':200})
        self.assertEqual(status,201)
        self.assertIn('netops_probe_healthy{target="api"} 1',self.call('/metrics')[1].decode())
    def test_metrics_content_type_and_method(self):
        _,_,headers=self.call('/metrics')
        self.assertTrue(dict(headers)['Content-Type'].startswith('text/plain; version=0.0.4'))
        self.assertEqual(self.call('/metrics','POST')[0],405)
    def test_db_outage_still_exposes_request_metrics(self):
        with patch.object(self.app,'probe_reader',side_effect=RuntimeError('offline')):
            text=self.call('/metrics')[1].decode();self.assertIn('netops_database_collect_success 0',text)
    def test_telemetry_failure_does_not_break_application(self):
        with patch.object(self.metrics,'observe',side_effect=RuntimeError('locked')):self.assertEqual(self.call()[0],200)
    def test_demo_flags_are_disabled_by_default(self):
        app=ObservedApplication(Application(self.db),self.metrics,self.db.latest,delay_ms=20,error_every=1)
        self.assertEqual(self.call(app=app)[0],200)
    def test_controlled_errors_and_delay_leave_probes_healthy(self):
        app=ObservedApplication(Application(self.db),self.metrics,self.db.latest,demo=True,delay_ms=20,error_every=2)
        self.assertEqual(self.call(app=app)[0],200);self.assertEqual(self.call(app=app)[0],500)
        self.assertEqual(self.call('/readyz',app=app)[0],200)
        self.assertIn('status_class="5xx"} 1',self.metrics.render())
    def test_unhandled_application_error_records_5xx(self):
        def broken(env,start):raise RuntimeError('broken')
        with self.assertRaises(RuntimeError):self.call(app=ObservedApplication(broken,self.metrics))
        self.assertIn('status_class="5xx"} 1',self.metrics.render())
    def test_real_http_metrics_roundtrip(self):
        with make_server('127.0.0.1',0,self.app,handler_class=Quiet) as server:
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base=f'http://127.0.0.1:{server.server_port}'
                with urlopen(base+'/api/targets',timeout=3) as response:self.assertEqual(response.status,200)
                with urlopen(base+'/metrics',timeout=3) as response:
                    self.assertIn('netops_http_requests_total',response.read().decode())
            finally:server.shutdown();thread.join(timeout=3)
