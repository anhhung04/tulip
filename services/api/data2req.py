#!/usr/bin/env python
# -*- coding: utf-8 -*-

from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
from jinja2 import Environment, BaseLoader
from io import BytesIO
import json
from typing import Dict, Any, Tuple, Optional

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, raw_http_request: bytes):
        self.rfile = BytesIO(raw_http_request)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

        self.headers = dict(self.headers)
        self.body = raw_http_request.split(b"\r\n\r\n", 1)[1].rstrip() if b"\r\n\r\n" in raw_http_request else None

    def send_error(self, code: int, message: str):
        self.error_code = code
        self.error_message = message

def decode_http_request(raw_request: bytes, tokenize: bool) -> Tuple[HTTPRequest, Dict[str, Any], str, Dict[str, str]]:
    request = HTTPRequest(raw_request)
    data: Dict[str, Any] = {}
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["content-length", "accept-encoding", "connection", "accept", "host"]}
    content_type = request.headers.get("content-type", "")
    data_param_name = "data"
    body = request.body

    if tokenize and body:
        if content_type.startswith("application/x-www-form-urlencoded"):
            data = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(body.decode()).items()}
        elif content_type.startswith("application/json"):
            data_param_name = "json"
            data = json.loads(body)
        elif content_type.startswith("text/plain"):
            data = body
        elif content_type.startswith("multipart/form-data"):
            data_param_name = "files"
            return request, "Forms with files are not yet implemented", None, None

    return request, data, data_param_name, headers

def convert_single_http_requests(raw_request: bytes, flow: Dict[str, Any], tokenize: bool = True, use_requests_session: bool = False) -> str:
    request, data, data_param_name, headers = decode_http_request(raw_request, tokenize)
    if not request.path.startswith('/'):
        raise ValueError('Request path must start with / to be a valid HTTP request')
    request_method = validate_request_method(request.command)

    template = Environment(loader=BaseLoader()).from_string("""
import os
import requests

host = os.getenv("TARGET_IP")
{% if use_requests_session %}
s = requests.Session()
s.headers = {{headers}}
{% else %}
headers = {{headers}}
{% endif %}
data = {{data}}

{% if use_requests_session %}s{% else %}requests{% endif %}.{{request_method}}(f"http://{{ '{' }}host{{ '}' }}:{{port}}" + {{request_path_repr}}, {{data_param_name}}=data{% if not use_requests_session %}, headers=headers{% endif %})
""")

    return template.render(
        headers=str(dict(headers)),
        data=data,
        request_method=request_method,
        request_path_repr=repr(request.path),
        data_param_name=data_param_name,
        use_requests_session=use_requests_session,
        port=flow["dst_port"]
    )

def convert_flow_to_http_requests(flow: Dict[str, Any], tokenize: bool = True, use_requests_session: bool = True) -> str:
    template = Environment(loader=BaseLoader()).from_string("""
import os
import requests
import sys

host = os.getenv("TARGET_IP", sys.argv[1])
{% if use_requests_session %}
s = requests.Session()
{% endif %}

{% for message in messages %}
{% if message.from == 'c' %}
{% if use_requests_session %}
s.headers = {{message.headers}}
{% else %}
headers = {{message.headers}}
{% endif %}
data = {{message.data}}
{% if use_requests_session %}s{% else %}requests{% endif %}.{{message.request_method}}(f"http://{{ '{' }}host{{ '}' }}:{{port}}" + {{message.request_path_repr}}, {{message.data_param_name}}=data{% if not use_requests_session %}, headers=headers{% endif %})
{% endif %}
{% endfor %}
""")

    messages = []
    for message in flow['flow']:
        if message['from'] == 'c':
            request, data, data_param_name, headers = decode_http_request(message['data'].encode(), tokenize)
            request_method = validate_request_method(request.command)
            if not request.path.startswith('/'):
                raise ValueError('Request path must start with / to be a valid HTTP request')
            messages.append({
                'headers': str(dict(headers)),
                'data': data,
                'request_method': request_method,
                'request_path_repr': repr(request.path),
                'data_param_name': data_param_name,
                'from': 'c'
            })

    return template.render(
        messages=messages,
        use_requests_session=use_requests_session,
        port=flow["dst_port"]
    )

def validate_request_method(request_method: str) -> str:
    request_method = request_method.lower()
    if request_method not in {'delete', 'get', 'head', 'options', 'patch', 'post', 'put'}:
        raise ValueError(f'Invalid request method: {request_method}')
    return request_method