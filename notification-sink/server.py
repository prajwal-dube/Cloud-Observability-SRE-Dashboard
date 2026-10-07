"""Local-only alert receiver for verifying delivery without notifying people."""
import collections
import json
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
EVENTS=collections.deque(maxlen=100)
LOCK=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def send(self,code,payload):
        body=json.dumps(payload).encode();self.send_response(code)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        if self.path=='/healthz':self.send(200,{'status':'alive'})
        elif self.path=='/notifications':
            with LOCK:self.send(200,{'notifications':list(EVENTS)})
        else:self.send(404,{'error':'not found'})
    def do_POST(self):
        if self.path!='/alerts':self.send(404,{'error':'not found'});return
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=524288:self.send(413,{'error':'size limit'});return
            payload=json.loads(self.rfile.read(size))
            alerts=payload['alerts']
            if not isinstance(alerts,list):raise ValueError('alerts array required')
            event={'received_at':time.time(),'status':payload.get('status','unknown'),
                   'alerts':[{'name':a.get('labels',{}).get('alertname','unknown'),'status':a.get('status','unknown')} for a in alerts]}
        except (ValueError,KeyError,TypeError,AttributeError):self.send(400,{'error':'invalid alert payload'});return
        with LOCK:EVENTS.append(event)
        print(json.dumps(event),flush=True);self.send(200,{'received':len(alerts)})
    def log_message(self,*_):pass
if __name__=='__main__':ThreadingHTTPServer(('0.0.0.0',8085),Handler).serve_forever()
