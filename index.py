#!/usr/bin/python

import calendar
import time
import json
import logging
import sys
import ssl
import urllib.request
from pprint import pprint


# Constants for warning checks
THRESHOLD_CPU_DANGER      = 75
THRESHOLD_CPU_CRIT        = 50
THRESHOLD_CPU_WARN        = 25
THRESHOLD_RPS_DANGER      = 1000
THRESHOLD_RPS_CRIT        = 500
THRESHOLD_RPS_WARN        = 100
THRESHOLD_RUNNING_STATE   = "RUNNING"

NOTICE_INFO               = 0
NOTICE_WARN               = 1
NOTICE_CRIT               = 2


def app(environ, start_response):
  data = main()
  start_response("200 OK", [
      ("Content-Type", "application/json"),
      ("Content-Length", str(len(data))),
      ("Access-Control-Allow-Origin", "*"),
      ("Access-Control-Expose-Headers", "Access-Control-Allow-Origin"),
      ("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept")
  ])
  return [bytes(data, 'utf-8')]

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
  cpu = int(inst_data["cpu_usage"])
  # What kind of notices/alerts can we generate for the NODE??
  if (cpu > THRESHOLD_CPU_DANGER):
    n.append(make_notice("CPU usage surpassed DANGER level at {0}".format(cpu), NOTICE_CRIT))
  elif (cpu > THRESHOLD_CPU_CRIT):
    n.append(make_notice("CPU usage surpassed CRITICAL level at {0}".format(cpu), NOTICE_WARN))
  elif (cpu > THRESHOLD_CPU_WARN):
    n.append(make_notice("CPU usage surpassed WARNING level at {0}".format(cpu), NOTICE_INFO))
  if (inst_data["state"] != THRESHOLD_RUNNING_STATE):
    n.append(make_notice("Instance is not in a RUNNING state!", NOTICE_CRIT))
  return n

def check_for_notices_conn(conn_data = {}, age = 1):
  n = []
  adjusted_traffic = int((conn_data["http_good_count"] +  conn_data["http_error_count"]) / age)
  # What kind of notices/alerts can we generate for the Connection??
  if ():
    n.append(make_notice("RPS surpassed DANGER level at {0}".format(adjusted_traffic), NOTICE_CRIT))
  elif (adjusted_traffic > THRESHOLD_RPS_CRIT):
    n.append(make_notice("RPS surpassed CRITICAL level at {0}".format(adjusted_traffic), NOTICE_WARN))
  elif (adjusted_traffic > THRESHOLD_RPS_WARN):
    n.append(make_notice("RPS surpassed WARNING level at {0}".format(adjusted_traffic), NOTICE_INFO))
  return n



def parse_metrics_json(data, exclude_orgs = [], only_orgs = []):
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
  http_good = 0
  http_bad = 0
  stats_since = sys.maxsize
  stats_temp = 0
  stats_age = 1
  now = round(time.time())

  for key in data:
    # Check to see if we want to exclude applications within this ORG
    if (data[key]["organization"]["name"] in exclude_orgs):
      continue
    # Check to see if only_orgs is non-empty, in which case we only want a specific collection or ORGs
    if (len(only_orgs) > 0 and data[key]["organization"]["name"] not in only_orgs):
      continue
    # How old is the data that we're processing here?
    stats_temp = data[key].get("stats_since", (round(time.time()) - 1) )
    if (stats_temp < stats_since):
      stats_since = stats_temp
    stats_age = (now - stats_since)
    # Trim the age of the data if it is very fresh (smooths rough edges with such a small sample size)
    if stats_age < 5:
      stats_age -= 1
    # Guard against DIV BY ZERO
    if stats_age < 1:
      stats_age = 1
    # The total volume of traffic for this foundation
    traffic = (data[key]["http_good_count"] + data[key]["http_error_count"])
    volume = volume + traffic
    http_good = http_good + data[key]["http_good_count"]
    http_bad = http_bad + data[key]["http_error_count"]
    if (isinstance(data[key]["instances"], list)):
      for inst in data[key]["instances"]:
        # Create a Node for the AI
        inst_name = "{0}/{1}".format(key, inst["index"])
        app_inst = make_node(inst_name, traffic)
        app_inst["notices"] = check_for_notices_node(inst)
        app_instances.append(app_inst)
        # Create a Connection between the Reported Cell IP and the AI Name
        c = make_conn(inst_name, inst["cell_ip"], traffic)
        c["notices"] = check_for_notices_conn(data[key], stats_age)
        connections.append(c)
        # Also Keep track of the Cell Nodes, we will append these to the master list later
        cells[inst["cell_ip"]] = make_node(inst["cell_ip"])
        cell_traffic[inst["cell_ip"]] = cell_traffic.get(inst["cell_ip"], 0) + traffic
        # Also extract an routes, and create a connection between the route and the AI
        if (data[key]["routes"] != None):
          for r in data[key]["routes"]:
            routes[r] = r
            connections.append(make_conn(r, inst_name, traffic))

  # Copy the whole list of AI's as a starting point for the master node list
  nodes = app_instances

  # Append the list of application routes to the master node list, also creating connections to the INTERNET
  for rou in routes:
    nodes.append(make_node(rou))
    connections.append(make_conn("INTERNET", rou, 100))

  # Append remaining nodes to the master list
  for cell in cells:
    nodes.append(cells[cell])

  # DEBUG INFO
  logging.warning("Stats AGE is " + str(stats_age))

  # The resulting Region can now take shape
  n_pcf = {}
  n_pcf["renderer"] = "region"
  n_pcf["nodes"] = nodes
  n_pcf["connections"] = connections
  n_pcf["class"] = "normal"
  n_pcf["metadata"] = {}
  n_pcf["updated"] = int(round(time.time() * 1000))
  n_pcf["props"] = {}
  n_pcf["maxVolume"] = int(volume / stats_age)
  n_pcf["http_good"] = int(http_good / stats_age)
  n_pcf["http_bad"] = int(http_bad / stats_age)
  if (n_pcf["maxVolume"] == 0):
    n_pcf["error_rate"] = 0.0
  else:
    n_pcf["error_rate"] = (n_pcf["http_bad"] / n_pcf["maxVolume"])

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

  # Define the foundations to process in an array
  foundations = {}

  # First Foundation
  pcf_one = {}
  pcf_one["name"] = "pcf-az-central-system"
  pcf_one["displayName"] = "AZR CUS [system]"
  pcf_one["json_url"] = "https://app-metrics-nozzle.apps.az.dav3.io/api/apps"
  pcf_one["exclude_orgs"] = []
  pcf_one["only_orgs"] = ["system"]

  # Second Foundation (which is really just the first, repeated with different filters)
  pcf_two = {}
  pcf_two["name"] = "pcf-az-central-non-system"
  pcf_two["displayName"] = "AZR CUS [!system]"
  pcf_two["json_url"] = "https://app-metrics-nozzle.apps.az.dav3.io/api/apps"
  pcf_two["exclude_orgs"] = ["system"] 
  pcf_two["only_orgs"] = []

  foundations[pcf_one["name"]] = pcf_one
  foundations[pcf_two["name"]] = pcf_two

  # Ensure that we can read from sites using self-signed SSL
  myssl = ssl.create_default_context()
  myssl.check_hostname=False
  myssl.verify_mode=ssl.CERT_NONE

  # A place for all the data we process
  d_conns = []
  d_nodes = []

  # The INTERNET node should be the first in the list
  d_nodes.append(n_internet)

  for site_name in foundations:
    response = urllib.request.urlopen(foundations[site_name]["json_url"], context=myssl)
    json_data = json.load(response)
    site_data = parse_metrics_json(json_data, only_orgs=foundations[site_name]["only_orgs"], exclude_orgs=foundations[site_name]["exclude_orgs"])
    site_data["name"] = site_name
    site_data["displayName"] = foundations[site_name]["displayName"]
    # Create the Global connections from the INTERNET to the PCF Foundation
    conn1 = {}
    conn1["source"] = "INTERNET"
    conn1["target"] = site_name
    conn1["class"] = "normal"
    conn1["notices"] = []
    conn1["metrics"] = make_metrics(site_data["maxVolume"], site_data["error_rate"], int(site_data["maxVolume"] * site_data["error_rate"]) )

    d_conns.append(conn1)
    d_nodes.append(site_data)
  # END for

  d = {}
  d["renderer"] = "global"
  d["name"] = "edge"
  d["nodes"] = d_nodes
  d["connections"] = d_conns
  d["serverUpdateTime"] = int(round(time.time() * 1000))

  return json.dumps(d, sort_keys=True, indent=2)

