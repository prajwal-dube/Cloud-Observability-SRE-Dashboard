"""Reset this container's dedicated metric store BEFORE spawning Gunicorn workers."""
import os
from pathlib import Path
from .metrics import Metrics

if __name__=='__main__':
    folder=Path('/tmp/netops-metrics')
    folder.mkdir(mode=0o700,exist_ok=True)
    path=folder/'metrics.sqlite3'
    for name in ['metrics.sqlite3','metrics.sqlite3-wal','metrics.sqlite3-shm']:
        (folder/name).unlink(missing_ok=True)
    os.environ['NETOPS_METRICS_DB']=str(path)
    Metrics(path)
    os.execvp('gunicorn',['gunicorn','--bind=0.0.0.0:8000','--workers=2','--threads=4','--timeout=30',
                          '--access-logfile=-','observability.application:application'])
