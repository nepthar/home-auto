#!/usr/bin/env python3

import time
import json

import tornado.httpserver
import tornado.ioloop
from tornado import web
from tornado.options import define, options
from tornado import locks

define("port", default=13001, help="Listen port", type=int)

# Expire readings after 5 minutes
METRICS_LIFE_TIME_S = 5 * 60
METRICS = {}
MLOCK = locks.Lock()

# Service Metrics
ReportedSuccessCounter = 0
ReportedFailCounter = 0
StartupTimeS = time.time()


# Nodes should report as:
# POST /report/${node_name}
# Content-Type: application/json
# [
#   ["metric1", 234],
#   ["metric2", 456.5]
# ]
#

class MetricReceiver(web.RequestHandler):
  def post(self, node_name):
    global ReportedSuccessCounter
    global ReportedFailCounter
    try:
      incoming_metrics = json.loads(self.request.body.decode('utf-8'))

      MLOCK.acquire()

      node_metrics = METRICS.get(node_name, dict())
      for name, value in incoming_metrics:
        node_metrics[name] = (value, time.time())
      METRICS[node_name] = node_metrics
      self.write('')

    except Exception:
      ReportedFailCounter += 1
      raise

    finally:
      MLOCK.release()
      ReportedFailCounter

class MetricSender(web.RequestHandler):
  def get(self, node_name):
    self.set_header('Content-Type', 'text/plain')
    metrics = []

    try:
      MLOCK.acquire()

      for name, value_time in METRICS.get(node_name, dict()).items():
        metrics.append((name, value_time[0]))
    finally:
      MLOCK.release()

    if len(metrics) == 0:
      raise web.HTTPError(404)

    for name, value in metrics:
      self.write(f"{name} {value}\n")


class ServiceMetricSender(web.RequestHandler):
  def get(self):
    self.set_header('Content-Type', 'text/plain')
    self.write(f"uptime_s {time.time() - StartupTimeS}\n")
    self.write(f"handle_success {ReportedSuccessCounter}\n")
    self.write(f"handle_failure {ReportedFailCounter}\n")


def prune_old_metrics():
  cutoff = time.time() - METRICS_LIFE_TIME_S

  try:
    MLOCK.acquire()

    # Iterates through all keys
    for node_name in list(METRICS):
      node_metrics = METRICS[node_name]

      for metric_name in list(node_metrics):
        if node_metrics[metric_name][1] < cutoff:
          del node_metrics[metric_name]

      if len(node_metrics) == 0:
        del METRICS[node_name]

  finally:
    MLOCK.release()
    tornado.ioloop.IOLoop.current().call_later(
      delay=METRICS_LIFE_TIME_S, callback=prune_old_metrics
    )


def main():
  tornado.options.parse_command_line()

  application = tornado.web.Application([
    (r"/report/(.*)", MetricReceiver),
    (r"/metrics/(.*)", MetricSender),
    (r"/metrics", ServiceMetricSender)
  ])

  http_server = tornado.httpserver.HTTPServer(application)
  http_server.listen(options.port)
  print(f"Listening on {options.port}")
  prune_old_metrics()
  tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
  main()
