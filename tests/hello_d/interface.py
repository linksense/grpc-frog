#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/27 11:20
# Copyright 2021 LinkSense Technology CO,. Ltd
"""测试类"""
import datetime
import os
from typing import Dict, List

import grpc
from pydantic import BaseModel

from grpc_frog import frog
from grpc_frog.core.servicer import Servicer

proto_dir = os.path.join(os.path.dirname(__file__), "proto")
service_d = Servicer("hello_d", proto_dir=proto_dir)
frog.add_servicer(service_d)


@frog.model()
class TDemoModel(BaseModel):
    int_field: int = 0
    float_field: float = 0.0
    str_field: str = ""
    list_int_field: List[int] = list()
    map_int_field: Dict[str, int] = dict()
    create_time: datetime.datetime = datetime.datetime.now()

    def increment_one(self):
        self.int_field += 1
        self.float_field += 1
        self.str_field += "1"
        self.list_int_field = [number + 1 for number in self.list_int_field]

        for key, value in self.map_int_field.items():
            self.map_int_field[key] = value + 1


class ResponseModel(BaseModel):
    int_a: int = 0
    float_b: float = 0.0
    string_c: str = ""
    repeated_model_d: List[TDemoModel] = list()
    map_model_e: Dict[str, int] = dict()


@service_d.grpc_method()
def echo_with_increment_one_base(request_model: ResponseModel) -> ResponseModel:
    kwargs = request_model.dict()
    res: dict = echo_with_increment_one(**kwargs)
    response_model = ResponseModel(**res)
    return response_model


@service_d.grpc_method(response_model=ResponseModel)
def echo_with_increment_one(
    int_a: int,
    float_b: float,
    string_c: str,
    repeated_model_d: List[TDemoModel],
    map_model_e: Dict[str, int],
) -> dict:
    int_a += 1
    float_b += 1
    string_c += "1"
    for _model in repeated_model_d:
        _model.increment_one()
    for key, value in map_model_e.items():
        map_model_e[key] = value + 1
    res = {
        "int_a": int_a,
        "float_b": float_b,
        "string_c": string_c,
        "repeated_model_d": repeated_model_d,
        "map_model_e": map_model_e,
    }
    return res


def generate_proto() -> str:
    """生成proto文件"""
    from grpc_frog import generate_proto_file

    os.makedirs(proto_dir, exist_ok=True)
    generate_proto_file(servicer_name=service_d.name, save_dir=proto_dir)
    print("proto dir ok")
    return proto_dir


def run_grpc_server_daemon():
    """启动server"""
    from concurrent import futures

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=2),
    )
    frog.bind_servicer(server, service_d)
    server.add_insecure_port("127.0.0.1:50055")
    server.start()
    print("server start", frog.servicer_map[service_d.name].bind_method_map)
    server.wait_for_termination()


def make_client():
    from grpc_frog import generate_py_code

    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hello_c")
    os.makedirs(path, exist_ok=True)
    generate_py_code(path, proto_dir=proto_dir)


if __name__ == "__main__":
    generate_proto()
    make_client()
    run_grpc_server_daemon()
