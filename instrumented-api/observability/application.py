import os
from app.main import application as base_application
from app.db import Database
from .metrics import Metrics
from .wsgi import ObservedApplication

application=ObservedApplication(
    base_application,
    Metrics(os.getenv('NETOPS_METRICS_DB','/tmp/netops-metrics/metrics.sqlite3')),
    probe_reader=Database().latest,
    demo=os.getenv('OBS_DEMO_MODE')=='true',
    delay_ms=int(os.getenv('OBS_DEMO_DELAY_MS','0')),
    error_every=int(os.getenv('OBS_DEMO_ERROR_EVERY','0')),
)
