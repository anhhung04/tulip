#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
from typing import Dict, Any

def escape(char: int) -> str:
    if 0x20 <= char < 0x7f:
        char_str = chr(char)
        return f'\\{char_str}' if char_str in '\\"' else char_str
    return f'\\x{char:02x}'

def convert(message: bytes) -> str:
    return ''.join(map(escape, message))

def flow2pwn(flow: Dict[str, Any]) -> str:
    port = flow["dst_port"]
    
    script = f"""from pwn import *
import os, sys

host = os.getenv("TARGET_IP", sys.argv[1])
proc = remote(host, {port})
"""

    for message in flow['flow']:
        data = base64.b64decode(message["b64"])
        if message['from'] == 'c':
            script += f'proc.write(b"{convert(data)}")\n'
        else:
            last_10_bytes = data[-10:]
            last_10_bytes = convert(last_10_bytes).replace("\\n", "\\\\n")
            script += f'proc.recvuntil(b"{last_10_bytes}")\n'

    return script