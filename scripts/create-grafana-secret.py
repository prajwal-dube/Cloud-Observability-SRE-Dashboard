#!/usr/bin/env python3
import argparse
import base64
import json
import os
import secrets
import subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--local',action='store_true');args=p.parse_args()
password=secrets.token_urlsafe(32)
if args.local:
    folder=Path(__file__).resolve().parents[1]/'.secrets'
    folder.mkdir(mode=0o700,exist_ok=True);folder.chmod(0o700)
    # File is container-readable; the private parent directory protects host traversal.
    fd=os.open(folder/'grafana-admin-password',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o444)
    with os.fdopen(fd,'w') as stream:stream.write(password)
    print('Generated Grafana admin credential in private .secrets directory; never overwrite an existing login.')
else:
    namespace={'apiVersion':'v1','kind':'Namespace','metadata':{'name':'monitoring'}}
    subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(namespace),text=True,check=True)
    secret={'apiVersion':'v1','kind':'Secret','type':'Opaque','metadata':{'name':'netops-grafana-admin','namespace':'monitoring'},
            'data':{'admin-user':base64.b64encode(b'admin').decode(),'admin-password':base64.b64encode(password.encode()).decode()}}
    subprocess.run(['kubectl','create','-f','-'],input=json.dumps(secret),text=True,check=True)
    print('Created Grafana login Secret via stdin; no password printed or saved to Git.')
