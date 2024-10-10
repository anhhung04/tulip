#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
from pathlib import Path
from typing import List, Dict, Any

# Environment variables with default values
traffic_dir = Path(os.getenv("TULIP_TRAFFIC_DIR", "/traffic"))
tick_length = os.getenv("TICK_LENGTH", 2*60*1000)
start_date = os.getenv("TICK_START", "2018-06-27T13:00+02:00")
mongo_host = os.getenv("TULIP_MONGO", "localhost:27017")
flag_regex = os.getenv("FLAG_REGEX", "[A-Z0-9]{31}=")
mongo_server = f'mongodb://{mongo_host}/'
vm_ip = os.getenv("VM_IP", "10.10.3.1")
SERVICES_FILE = os.getenv("SERVICES_FILE", "/tmp/dummy")

def load_services() -> List[Dict[str, Any]]:
  """Load services from file or use default if file doesn't exist."""
  if Path(SERVICES_FILE).exists():
      with open("/tmp/services.json", "r") as f:
          services = json.load(f)
      for service in services:
          service.setdefault("ip", vm_ip)
      return services
  
  return [
      {"ip": vm_ip, "port": 9876, "name": "cc_market"},
      {"ip": vm_ip, "port": 80, "name": "maze"},
      {"ip": vm_ip, "port": 8080, "name": "scadent"},
      {"ip": vm_ip, "port": 5000, "name": "starchaser"},
      {"ip": vm_ip, "port": 1883, "name": "scadnet_bin"},
      {"ip": vm_ip, "port": -1, "name": "other"}
  ]

services = load_services()