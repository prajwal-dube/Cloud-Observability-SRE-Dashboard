#!/usr/bin/env python3
"""Prepare optional Slack configuration; makes no outbound HTTP/Slack request."""
import argparse
import base64
import getpass
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def valid_webhook(url):
    parsed=urlparse(url)
    return parsed.scheme=='https' and parsed.hostname=='hooks.slack.com' and parsed.port in [None,443] and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and bool(re.fullmatch(r'/services/[A-Za-z0-9]+/[A-Za-z0-9]+/[A-Za-z0-9]+',parsed.path))

def config(channel,path):
    if not re.fullmatch(r'#[A-Za-z0-9_-]+',channel):raise ValueError('Use a Slack channel like #netops-alerts')
    return {'global':{'resolve_timeout':'5m'},'route':{'receiver':'drop','group_by':['alertname','namespace'],
       'group_wait':'15s','group_interval':'1m','repeat_interval':'30m',
       'routes':[{'matchers':['service="netops"'],'receiver':'netops-slack'}]},
       'receivers':[{'name':'drop'},{'name':'netops-slack','slack_configs':[{'api_url_file':path,'channel':channel,'send_resolved':True,
       'title':'[{{ .Status }}] {{ .CommonLabels.alertname }}',
       'text':'{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}\n{{ end }}'}]}]}

def main():
    p=argparse.ArgumentParser();p.add_argument('--local',action='store_true');p.add_argument('--channel',required=True);args=p.parse_args()
    webhook=getpass.getpass('Slack incoming-webhook URL (hidden; configuration only): ')
    if not valid_webhook(webhook):raise SystemExit('Supply a normal HTTPS hooks.slack.com/services incoming webhook')
    root=Path(__file__).resolve().parents[1]
    if args.local:
        folder=root/'.secrets';folder.mkdir(mode=0o700,exist_ok=True);folder.chmod(0o700)
        fd=os.open(folder/'slack-url',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
        with os.fdopen(fd,'w') as stream:stream.write(webhook)
        # JSON is valid YAML; no additional Python dependencies are required.
        generated=root/'alertmanager.local.json';generated.write_text(json.dumps(config(args.channel,'/run/secrets/slack-url'),indent=2)+'\n')
        overlay={'services':{'alertmanager':{'volumes':[f'{generated}:/etc/alertmanager/alertmanager.yml:ro',
                   f'{folder / "slack-url"}:/run/secrets/slack-url:ro']}}}
        (root/'slack-compose.local.json').write_text(json.dumps(overlay,indent=2)+'\n')
        print('Prepared optional local Slack files. Review and run local-up.sh -f slack-compose.local.json to activate.')
    else:
        secret={'apiVersion':'v1','kind':'Secret','type':'Opaque','metadata':{'name':'netops-slack','namespace':'monitoring'},
                'data':{'slack-url':base64.b64encode(webhook.encode()).decode()}}
        subprocess.run(['kubectl','create','-f','-'],input=json.dumps(secret),text=True,check=True)
        values={'alertmanager':{'tplConfig':False,'config':config(args.channel,'/etc/alertmanager/secrets/netops-slack/slack-url'),
                               'alertmanagerSpec':{'secrets':['netops-slack']}}}
        (root/'slack-values.local.json').write_text(json.dumps(values,indent=2)+'\n')
        print('Prepared optional Slack Secret and nonsecret override. Review then upgrade with the same base/persistence values.')
if __name__=='__main__':main()
