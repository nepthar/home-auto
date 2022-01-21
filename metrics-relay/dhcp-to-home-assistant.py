#!/usr/bin/env python3

# This is designed to read the output line by line from dhcpdump(1)
# I'm sure there's a better way but man is this easy.
# A state machine looks for these 4 lines in dhcpdump's output in order:
#
# OPTION:  53 (  1) DHCP message type         3 (DHCPREQUEST)
# OPTION:  61 (  7) Client-identifier         01:98:60:ca:58:86:a2
# OPTION:  50 (  4) Request IP address        192.168.1.22
# ----------------------------------------------------------------------
#
# There are other lines between, but who cares.

REPORT_DEST = 'http://127.0.0.1:13001/dhcp'

mac_triggers = {
  'e8:48:b8:14:3b:33': 'kitchen_cooking_on',
  '00:5f:67:ac:b9:be': 'master_hallway_on',
  'e8:48:b8:5d:65:6d': 'livingroom_reading_on',
}

import requests
import sys

class Machine:
  def __init__(self):
    self.state = 'waiting'
    self.mac_addr = None
    self.ip_addr = None

  def begin(self):
    self.state = 'reading'

  def set_ip(self, ip):
    if self.state != 'reading':
      self.reset()
      return

    self.ip_addr = ip
    self.state = 'sendable' if self.mac_addr

  def set_mac(self, mac):
    if self.state != 'reading':
      self.reset()
      return

    self.mac_addr = mac
    self.state = 'sendable' if self.ip_addr

  def finish(self):
    if self.state != 'sendable':
      self.reset()
      return

    self.state = 'sending'
    requests.post(REPORT_DEST,  data = {'ip': self.ip_addr, 'mac': self.mac_addr})
    self.reset()

MACHINE = Machine()
MACHINE.reset()


def handle_line(line):
  if "DHCPREQUEST" in line:
    MACHINE.begin()
  elif "Client-identifier" in line:
    MACHINE.set_mac(line.split()[-1])
  elif "Request IP address" in line:
    MACHINE.set_ip(line.split()[-1])
  elif "-----------------" in line:
    MACHINE.finish()

for line in sys.stdin:
  handle_line(line)
