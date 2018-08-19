#!/usr/bin/python

import calendar
import time
import json


def make_node(name, children = []):
  streaming = {}
  streaming["streaming"] = 1
  node = {}
  node["name"] = name
  node["nodes"] = children
  node["metadata"] = streaming
  node["renderer"] = "focusedChild"
  return node

def make_n(name, normal = -1, warning = -1, danger = -1):
  metrics = {}
  if (normal != -1):
    metrics["normal"] = normal
  if (warning != -1):
    metrics["warning"] = warning
  if (danger != -1):
    metrics["danger"] = danger
  node = {}
  node["name"] = name
  if (normal != -1 and warning != 1 and danger != -1):
    node["metrics"] = metrics
  return node

def make_conn(src, trg, normal = -1, warning = -1, danger = -1):
  streaming = {}
  streaming["streaming"] = 1
  metrics = {}
  if (normal != -1):
    metrics["normal"] = normal
  if (warning != -1):
    metrics["warning"] = warning
  if (danger != -1):
    metrics["danger"] = danger
  conn = {}
  conn["source"] = src
  conn["target"] = trg
  conn["metadata"] = streaming
  if (normal != -1 and warning != 1 and danger != -1):
    conn["metrics"] = metrics
  return conn


# INTERNET Region, aka ROOT node
n_internet = {}
n_internet["renderer"] = "region"
n_internet["name"] = "INTERNET"
n_internet["displayName"] = "INTERNET"
n_internet["nodes"] = []
n_internet["connections"] = []
n_internet["class"] = "normal"
n_internet["metadata"] = {}

# Make some GO Routers
n_rtr1 = make_node("rtr1")
n_rtr2 = make_node("rtr2")
n_rtr3 = make_node("rtr3")
routers = [n_rtr1, n_rtr2, n_rtr3]

# Make some Diego Cells
n_dc1 = make_node("cell_1")
n_dc2 = make_node("cell_2")
n_dc3 = make_node("cell_3")
n_dc4 = make_node("cell_4")
cells = [n_dc1, n_dc2, n_dc3, n_dc4]

# Make some App Instances
a_1 = make_node("AI1")
a_2 = make_node("AI2")
a_3 = make_node("AI3")
a_4 = make_node("AI4")
instances = [a_1, a_2, a_3, a_4]

# The first PCF Foundation Region
n_pcf1 = {}
n_pcf1["renderer"] = "region"
n_pcf1["name"] = "pcf-one"
n_pcf1["displayName"] = "PCF SRT Azure CentralUS"
n_pcf1["nodes"] = [n_rtr1, n_rtr2, n_rtr3, n_dc1, n_dc2, n_dc3, n_dc4, a_1, a_2, a_3, a_4]
n_pcf1["connections"] = [make_conn("INTERNET", "rtr1"), make_conn("INTERNET", "rtr2"), make_conn("INTERNET", "rtr3"), make_conn("rtr1", "cell_1"), make_conn("rtr1", "cell_2"), make_conn("rtr1", "cell_3"), make_conn("rtr1", "cell_4"), make_conn("cell_1", "AI1"), make_conn("cell_2", "AI2"), make_conn("cell_3", "AI3"), make_conn("rtr2", "cell_1"), make_conn("rtr2", "cell_2"), make_conn("rtr2", "cell_3"), make_conn("rtr2", "cell_4"), make_conn("rtr3", "cell_1"), make_conn("rtr3", "cell_2"), make_conn("rtr3", "cell_3"), make_conn("rtr3", "cell_4")]
n_pcf1["class"] = "normal"
n_pcf1["metadata"] = {}
n_pcf1["updated"] = int(round(time.time() * 1000))
n_pcf1["props"] = {}
n_pcf1["maxVolume"] = 10000

metrics1 = {}
metrics1["normal"] = 99950
metrics1["warning"] = 0.017
metrics1["danger"] = 50

conn1 = {}
conn1["source"] = "INTERNET"
conn1["target"] = "pcf-one"
conn1["class"] = "normal"
conn1["notices"] = []
conn1["metrics"] = metrics1


d = {}
d["renderer"] = "global"
d["name"] = "edge"
d["nodes"] = [n_internet, n_pcf1]
d["connections"] = [conn1]
d["serverUpdateTime"] = int(round(time.time() * 1000))

print json.dumps(d, sort_keys=True, indent=2)

