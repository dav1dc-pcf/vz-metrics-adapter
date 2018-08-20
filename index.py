#!/usr/bin/python

import calendar
import time
import json
import ssl
import urllib.request
from pprint import pprint



def app(environ, start_response):
  data = main()
  start_response("200 OK", [
      ("Content-Type", "application/json"),
      ("Content-Length", str(len(data)))
  ])
  return iter([data])

def make_metrics(normal = -1, warning = -1, danger = -1):
  metrics = {}
  if (normal != -1):
    metrics["normal"] = normal
  if (warning != -1):
    metrics["warning"] = warning
  if (danger != -1):
    metrics["danger"] = danger
  return metrics

def make_notice(title, severity = 0, link = -1):
  notice = {}
  notice["title"] = title
  notice["severity"] = severity
  if (link != -1):
    notice["link"] = link
  return notice

def make_node(name, normal = -1, warning = -1, danger = -1, children = [], notices = []):
  streaming = {}
  streaming["streaming"] = 1
  node = {}
  node["name"] = name
  node["nodes"] = children
  node["notices"] = notices
  node["metadata"] = streaming
  node["renderer"] = "focusedChild"
  if (not (normal != -1 and warning != -1 and danger != -1)):
    node["metrics"] = make_metrics(normal, warning, danger)
  return node

def make_conn(src, trg, normal = -1, warning = -1, danger = -1, notices = []):
  streaming = {}
  streaming["streaming"] = 1
  conn = {}
  conn["source"] = src
  conn["target"] = trg
  conn["metadata"] = streaming
  conn["notices"] = notices
  if (not (normal != -1 and warning != -1 and danger != -1)):
    conn["metrics"] = make_metrics(normal, warning, danger)
  return conn


def check_for_notices_node(inst_data = {}):
  n = []
  # What kind of notices/alerts can we generate for the NODE??
  if (int(inst_data["cpu_usage"]) > 5):
    n.append(make_notice("CPU usage is slightly high at {0}".format(inst_data["cpu_usage"])))
  if (inst_data["state"] != "RUNNING"):
    n.append(make_notice("Instance is not in a RUNNING state!", 2))
  return n

def check_for_notices_conn(conn_data = {}):
  n = []
  # What kind of notices/alerts can we generate for the Connection??
  if (conn_data["event_count"] > 20):
    n.append(make_notice("RPS slightly high at {0}".format(conn_data["event_count"])))
  return n



def parse_metrics_json(data, exclude_orgs = [], only_orgs = []):
  # Make some GO Routers (statically set to 3 for the time being)
  n_rtr1 = make_node("rtr1")
  n_rtr2 = make_node("rtr2")
  n_rtr3 = make_node("rtr3")
  routers = [n_rtr1, n_rtr2, n_rtr3]

  # A Place for some Diego Cells
  cells = {}
  cell_traffic = {}

  # A Place for some App Instances
  app_instances = []

  # Sort out the Nodes & Connections
  connections = []
  nodes = []
  routes = {}
  volume = 0

  for key in data:
    # Check to see if we want to exclude applications within this ORG
    if (data[key]["organization"]["name"] in exclude_orgs):
      continue
    # Check to see if only_orgs is non-empty, in which case we only want a specific collection or ORGs
    if (len(only_orgs) > 0 and data[key]["organization"]["name"] not in only_orgs):
      continue
    # The total volume is inflated slightly by adding 10 for every application processed (for testing purposes)
    volume = volume + data[key]["event_count"] + 10
    for inst in data[key]["instances"]:
      # Create a Node for the AI
      inst_name = "{0}/{1}".format(key, inst["index"])
      app_inst = make_node(inst_name, data[key]["event_count"])
      app_inst["notices"] = check_for_notices_node(inst)
      app_instances.append(app_inst)
      # Create a Connection between the Reported Cell IP and the AI Name
      c = make_conn(inst["cell_ip"], inst_name, int(10 + data[key]["event_count"]))
      c["notices"] = check_for_notices_conn(data[key])
      connections.append(c)
      # Also Keep track of the Cell Nodes, we will append these to the master list later
      cells[inst["cell_ip"]] = make_node(inst["cell_ip"])
      cell_traffic[inst["cell_ip"]] = cell_traffic.get(inst["cell_ip"], 0) + int(10 + data[key]["event_count"])
      # Also extract an routes, and create a connection between the route and the AI
      if (data[key]["routes"] != None):
        for r in data[key]["routes"]:
          routes[r] = r
          connections.append(make_conn(r, inst_name, int(10 + data[key]["event_count"])))

  # Copy the whole list of AI's as a starting point for the master node list
  nodes = app_instances
  # Append the list of Routers to the master node list
  for rtr in routers:
    nodes.append(rtr)

  # Append the list of application routes to the master node list, also creating connections to the INTERNET
  for rou in routes:
    nodes.append(make_node(rou))
    connections.append(make_conn("INTERNET", rou, 10))

  # Append remaining nodes to the master list, and create connections between the routers <-> cells & INTERNET <-> routers
  for cell in cells:
    nodes.append(cells[cell])
    for rtr in routers:
      connections.append(make_conn(rtr["name"], cell, int(cell_traffic.get(cell, 100)/3)))
      connections.append(make_conn("INTERNET", rtr["name"], 1000))

  # The resulting Region can now take shape
  n_pcf = {}
  n_pcf["renderer"] = "region"
  n_pcf["nodes"] = nodes
  n_pcf["connections"] = connections
  n_pcf["class"] = "normal"
  n_pcf["metadata"] = {}
  n_pcf["updated"] = int(round(time.time() * 1000))
  n_pcf["props"] = {}
  n_pcf["maxVolume"] = volume

  # return the completed object representation
  return n_pcf

# END parse_metrics_json




def main():

  # INTERNET Region, aka ROOT node
  n_internet = {}
  n_internet["renderer"] = "region"
  n_internet["name"] = "INTERNET"
  n_internet["displayName"] = "INTERNET"
  n_internet["nodes"] = []
  n_internet["connections"] = []
  n_internet["class"] = "normal"
  n_internet["metadata"] = {}




  # Read the response from app-metrics-nozzle from a file (for now)
  #with open('apps.json') as f:
  #  json_data = json.load(f)
  # Old read from local file test


  myssl = ssl.create_default_context()
  myssl.check_hostname=False
  myssl.verify_mode=ssl.CERT_NONE

  pcf1_link = "https://app-metrics-nozzle.apps.az.dav3.io/api/apps"
  response = urllib.request.urlopen(pcf1_link, context=myssl)
  json_data = json.load(response)


  n_pcf1 = parse_metrics_json(json_data)
  n_pcf2 = parse_metrics_json(json_data, exclude_orgs=["system"])

  # Label the Foundtion data
  n_pcf1["name"] = "pcf-az-central"
  n_pcf1["displayName"] = "Azure CentralUS"

  n_pcf2["name"] = "pcf-az-useast"
  n_pcf2["displayName"] = "Azure USEast"



  # Create the Global connections from the INTERNET to each PCF Foundation
  conn1 = {}
  conn1["source"] = "INTERNET"
  conn1["target"] = "pcf-az-central"
  conn1["class"] = "normal"
  conn1["notices"] = []
  conn1["metrics"] = make_metrics(n_pcf1["maxVolume"], 0.017, 5)

  conn2 = {}
  conn2["source"] = "INTERNET"
  conn2["target"] = "pcf-az-useast"
  conn2["class"] = "normal"
  conn2["notices"] = []
  conn2["metrics"] = make_metrics(n_pcf2["maxVolume"], 0.014, 3)


  d = {}
  d["renderer"] = "global"
  d["name"] = "edge"
  d["nodes"] = [n_internet, n_pcf1, n_pcf2]
  d["connections"] = [conn1, conn2]
  d["serverUpdateTime"] = int(round(time.time() * 1000))

  return json.dumps(d, sort_keys=True, indent=2)

