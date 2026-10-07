import importlib.util
import json
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
sink=load('sink',ROOT/'notification-sink/server.py')
slack=load('slack',ROOT/'scripts/configure-slack.py')

class NotificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sink.EVENTS.clear();cls.server=sink.ThreadingHTTPServer(('127.0.0.1',0),sink.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.thread.join(timeout=3);cls.server.server_close()
    def test_local_receiver_records_firing_and_resolved(self):
        for status in ['firing','resolved']:
            body=json.dumps({'status':status,'alerts':[{'status':status,'labels':{'alertname':'TestOnly'}}]}).encode()
            request=Request(self.base+'/alerts',data=body,headers={'Content-Type':'application/json'})
            with urlopen(request,timeout=3) as response:self.assertEqual(response.status,200)
        with urlopen(self.base+'/notifications',timeout=3) as response:events=json.load(response)['notifications']
        self.assertEqual(events[-2]['status'],'firing');self.assertEqual(events[-1]['status'],'resolved')
    def test_receiver_rejects_malformed_payload(self):
        with self.assertRaises(HTTPError) as caught:urlopen(Request(self.base+'/alerts',data=b'{}'),timeout=3)
        self.assertEqual(caught.exception.code,400)
    def test_slack_urls_reject_other_hosts_credentials_and_queries(self):
        self.assertTrue(slack.valid_webhook('https://hooks.slack.com/services/T123/B123/abcXYZ123'))
        for url in ['http://hooks.slack.com/services/T/B/x','https://example.com/services/T/B/x',
                    'https://user@hooks.slack.com/services/T/B/x','https://hooks.slack.com/services/T/B/x?token=x']:
            self.assertFalse(slack.valid_webhook(url))
    def test_slack_config_references_file_and_filters_netops(self):
        data=slack.config('#netops-alerts','/secret/webhook')
        receiver=data['receivers'][1]['slack_configs'][0]
        self.assertEqual(receiver['api_url_file'],'/secret/webhook');self.assertNotIn('api_url',receiver)
        self.assertTrue(receiver['send_resolved']);self.assertEqual(data['route']['routes'][0]['matchers'],['service="netops"'])
        with self.assertRaises(ValueError):slack.config('@everyone','/secret/webhook')
