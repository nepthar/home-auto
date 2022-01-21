#!/usr/bin/env python3
# metrics-relay.py: Metric push => pull service for prometheus
# Post as:
# POST /report/job/instance
# Content-Type: text/plain
# metric1_name metric_value
# metric2_name metric_value

import time
import json
import math
import datetime

from tornado import web, ioloop, httpserver
from tornado.options import define, options

define("port", default=13001, help="Listen port", type=int)
define("metric_lifetime_s", default=600, help="How long metrics are kept before expiring", type=int)
define("dhcp_eth_device", default="en0.2", help="Device to listen to dhcp messagers on")
define("dhcpdump_bin", default="/usr/local/bin/dhcpdump", help="path to dhcpdump")

# We're running this in single threaded mode, so we don't need to lock
METRICS = {}

# Service Metrics
ReportedSuccessCounter = 0
ReportedFailCounter = 0
PrunedCounter = 0
StartupTimeS = time.time()


class MetricReceiver(web.RequestHandler):
  def post(self, job, instance):
    global ReportedSuccessCounter
    global ReportedFailCounter

    print(self.request.body.decode('utf-8'))
    print(self.request.headers)

    try:
      report_time_s = math.floor(time.time())

      for line in self.request.body.decode('utf-8').splitlines():
        metric, _, value = line.rpartition(' ')
        key = f"{metric}{{job=\"{job}\",instance=\"{instance}\"}}"
        METRICS[key] = (value, report_time_s)

      ReportedSuccessCounter += 1

    except Exception:
      ReportedFailCounter += 1
      raise


class MetricSender(web.RequestHandler):

  def get(self):
    self.set_header('Content-Type', 'text/plain')

    for metric, val_time in METRICS.items():
      self.write(f"{metric} {val_time[0]} {val_time[1]}\n")

    self.wm('uptime_s{job="metrics_relay",instance="0"}', math.floor(time.time() - StartupTimeS))
    self.wm('report_success_count{job="metrics_relay",instance="0"}', ReportedSuccessCounter)
    self.wm('report_fail_count{job="metrics_relay",instance="0"}', ReportedFailCounter)
    self.wm('pruned_count{job="metrics_relay",instance="0"}', PrunedCounter)

  def wm(self, name, value):
    self.write(f"{name} {value}\n")


class DHCPReportHandler(web.RequestHandler):
  def post(self):
    print(self.get_argument('ip'))
    print(self.get_argument('mac'))
    self.write('ok')


def prune_old_metrics(metric_lifetime_s):
  global PrunedCounter

  cutoff = time.time() - metric_lifetime_s

  for metric_name in list(METRICS):
    if METRICS[metric_name][1] < cutoff:
      PrunedCounter += 1
      del METRICS[metric_name]


def main():
  options.parse_command_line()

  application = web.Application([
    (r"/report/(.*)/(.*)", MetricReceiver),
    (r"/metrics", MetricSender),
  ])

  dhcp_listen_cmd = (
    '/usr/bin/sudo', option.dhcpdump_bin, '-i', options.dhcp_eth_device
  )

  http_server = httpserver.HTTPServer(application)
  http_server.listen(options.port)

  metric_ttl_s = options.metric_lifetime_s
  ioloop.PeriodicCallback(
    lambda: prune_old_metrics(metric_ttl_s),
    metric_ttl_s * 1000
  ).start()

  opts = '\n'.join(f"{k}={v}" for k, v in options.items())
  print(f"{datetime.datetime.now()} Started with options:\n{opts}")

  ioloop.IOLoop.current().start()

if __name__ == "__main__":
  main()
