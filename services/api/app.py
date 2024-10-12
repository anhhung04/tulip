#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is part of Flower.
#
# Copyright ©2018 Nicolò Mazzucato
# Copyright ©2018 Antonio Groza
# Copyright ©2018 Brunello Simone
# Copyright ©2018 Alessio Marotta
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
#
# Flower is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Flower is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Flower.  If not, see <https://www.gnu.org/licenses/>.

import traceback
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Union

from configurations import services, traffic_dir, start_date, tick_length, flag_regex
from pathlib import Path
from data2req import convert_flow_to_http_requests, convert_single_http_requests
from base64 import b64decode
from db import DB
from bson import json_util
from fastapi.middleware.cors import CORSMiddleware

from flow2pwn import flow2pwn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DB()


def return_json_response(object):
    return Response(content=json_util.dumps(object), media_type="application/json")


def return_text_response(object):
    return Response(content=object, media_type="text/plain")


@app.get("/")
def hello_world():
    return "Hello, World!"


@app.get("/tick_info")
def get_tick_info():
    data = {"startDate": start_date, "tickLength": tick_length}
    return return_json_response(data)


class QueryModel(BaseModel):
    flow_data: Optional[str] = Field(None, alias="flow.data")
    service: str
    dst_ip: Optional[str] = None
    dst_port: Union[str, int, None] = None
    from_time: Union[str, int, None] = None
    to_time: Union[str, int, None] = None
    includeTags: List[str] = []
    excludeTags: List[str] = []
    tags: List[str] = []
    flags: List[str] = []
    flagids: List[str] = []


@app.post("/query")
def query(query: QueryModel):
    result = db.getFlowList(query.model_dump(exclude_none=True))
    return return_json_response(result)


@app.get("/tags")
def get_tags():
    result = db.getTagList()
    return return_json_response(result)


@app.get("/signature/{id}")
def signature(id: int):
    result = db.getSignature(id)
    return return_json_response(result)


@app.get("/star/{flow_id}/{star_to_set}")
def set_star(flow_id: str, star_to_set: str):
    db.setStar(flow_id, star_to_set != "0")
    return "ok!"


@app.get("/services")
def get_services():
    return return_json_response(services)


@app.get("/flag_regex")
def get_flag_regex():
    return return_json_response(flag_regex)


@app.get("/flow/{id}")
def get_flow_detail(id: str):
    return return_json_response(db.getFlowDetail(id))


@app.post("/to_single_python_request")
async def convert_to_single_request(request: Request):
    flow_id = request.query_params.get("id", "")
    if flow_id == "":
        return return_text_response(
            "There was an error while converting the request:\n{}: {}".format(
                "No flow id", "No flow id param"
            )
        )
    flow = db.getFlowDetail(flow_id)
    if not flow:
        return return_text_response(
            "There was an error while converting the request:\n{}: {}".format(
                "Invalid flow", "Invalid flow id"
            )
        )
    data = b64decode(await request.body())
    tokenize = request.query_params.get("tokenize", "false").lower() == "true"
    use_requests_session = (
        request.query_params.get("use_requests_session", "false").lower() == "true"
    )
    try:
        converted = convert_single_http_requests(
            data, flow, tokenize, use_requests_session
        )
    except Exception as ex:
        return return_text_response(
            "There was an error while converting the request:\n{}: {}".format(
                type(ex).__name__, traceback.format_exc()
            )
        )
    return return_text_response(converted)


@app.get("/to_python_request/{id}")
def convert_to_requests(
    id: str, tokenize: bool = True, use_requests_session: bool = True
):
    flow = db.getFlowDetail(id)
    if not flow:
        return return_text_response(
            "There was an error while converting the request:\n{}: {}".format(
                "Invalid flow", "Invalid flow id"
            )
        )
    try:
        converted = convert_flow_to_http_requests(flow, tokenize, use_requests_session)
    except Exception as ex:
        return return_text_response(
            "There was an error while converting the request:\n{}: {}".format(
                type(ex).__name__, traceback.format_exc()
            )
        )
    return return_text_response(converted)


@app.get("/to_pwn/{id}")
def convert_to_pwn(id: str):
    flow = db.getFlowDetail(id)
    converted = flow2pwn(flow)
    return return_text_response(converted)


@app.get("/download/")
def download_file(file: str):
    if file is None:
        raise HTTPException(
            status_code=400,
            detail="There was an error while downloading the requested file: No 'file' given",
        )
    filepath = Path(file)

    # Check for path traversal by resolving the file first.
    filepath = filepath.resolve()
    if traffic_dir not in filepath.parents:
        raise HTTPException(
            status_code=400,
            detail="There was an error while downloading the requested file: 'file' was not in a subdirectory of traffic_dir",
        )

    try:
        return FileResponse(filepath, filename=filepath.name)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="There was an error while downloading the requested file: 'file' not found",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
