#!/usr/bin/env python3
"""Controlled lab traffic; not an application-capacity benchmark."""
import argparse
import concurrent.futures
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlopen
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8080/api/targets')
p.add_argument('--seconds',type=int,default=300);p.add_argument('--concurrency',type=int,default=2)
args=p.parse_args()
parsed=urlparse(args.url)
if parsed.scheme not in ['http','https'] or not parsed.hostname or parsed.username or parsed.password:p.error('Use a credential-free HTTP(S) URL')
if not 1<=args.concurrency<=10 or not 1<=args.seconds<=1800:p.error('Use concurrency 1-10 and duration 1-1800 seconds')
deadline=time.monotonic()+args.seconds
def client(_):
    total=errors=0
    while time.monotonic()<deadline:
        try:
            with urlopen(args.url,timeout=5) as response:response.read();errors+=int(response.status>=500)
        except HTTPError as exc:errors+=int(exc.code>=500);exc.close()
        except Exception:errors+=1
        total+=1;time.sleep(0.1)
    return total,errors
with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:results=list(pool.map(client,range(args.concurrency)))
print({'requests':sum(x[0] for x in results),'errors':sum(x[1] for x in results),'note':'Lab traffic, not a throughput capacity claim'})
