import json
import logging
import os
import threading
import time
LOG=logging.getLogger('netops.observability')

class ObservedApplication:
    def __init__(self,app,metrics,probe_reader=None,demo=False,delay_ms=0,error_every=0):
        if not 0<=delay_ms<=2000 or not 0<=error_every<=1000:raise ValueError('Invalid bounded demo settings')
        self.app=app;self.metrics=metrics;self.probe_reader=probe_reader
        self.demo=demo;self.delay_ms=delay_ms;self.error_every=error_every
        self._reads=0;self._lock=threading.Lock()

    def __call__(self,env,start_response):
        path=env.get('PATH_INFO','/')
        if path=='/metrics':
            if env.get('REQUEST_METHOD')!='GET':
                start_response('405 Method Not Allowed',[('Content-Type','text/plain')]);return [b'GET required']
            rows=[];database_ok=True
            try:
                if self.probe_reader:rows=self.probe_reader()
            except Exception:
                database_ok=False
                LOG.warning('probe_metrics_collection_failed')
            try:
                body=self.metrics.render(rows,database_ok).encode()
                start_response('200 OK',[('Content-Type','text/plain; version=0.0.4; charset=utf-8'),('Content-Length',str(len(body)))])
                return [body]
            except Exception:
                LOG.warning('metrics_store_unavailable')
                start_response('503 Service Unavailable',[('Content-Type','text/plain')]);return [b'Metrics unavailable']
        started=time.monotonic();status=[500]
        def capture(value,headers,exc_info=None):
            status[0]=int(value.split()[0]);return start_response(value,headers,exc_info)
        injected=False
        if self.demo and env.get('REQUEST_METHOD')=='GET' and path in ['/api/targets','/api/history']:
            if self.delay_ms:time.sleep(self.delay_ms/1000)
            with self._lock:
                self._reads+=1
                injected=self.error_every>0 and self._reads%self.error_every==0
        def stream():
            iterable=None
            try:
                if injected:
                    body=json.dumps({'error':'Controlled observability demo failure'}).encode()
                    capture('500 Internal Server Error',[('Content-Type','application/json'),('Content-Length',str(len(body))),('X-NetOps-Demo','true')])
                    yield body
                else:
                    iterable=self.app(env,capture)
                    yield from iterable
            finally:
                if iterable is not None and hasattr(iterable,'close'):iterable.close()
                try:self.metrics.observe(env.get('REQUEST_METHOD','GET'),path,status[0],time.monotonic()-started)
                except Exception:LOG.warning('request_telemetry_dropped')
        return stream()
