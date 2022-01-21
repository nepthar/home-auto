#!/usr/bin/env python3

import requests
import time
import random

node_names = ['node1', 'node2']

metrics = ['temp', 'humidity']

for i in range(100):
  for nn in node_names:

    req_body = []
    for mn in metrics:
      req_body.append([f'{mn}_{i}', random.random() * 100])

    r = requests.post(f'http://127.0.0.1:13001/report/{nn}/ins', body='\n'.join(req_body))
    print(f"{nn} metrics post {r.status_code}")

  time.sleep(1)

print(requests.get(f'http://127.0.0.1:13001/metrics').content.decode('utf-8'))

