#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/2/19 17:22
# Copyright 2021 LinkSense Technology CO,. Ltd
import os

from grpc_frog import Servicer, frog
from grpc_frog.core import log, proto_type_recorder
from grpc_frog.generator.pb_fiile_util import generate_pb2_file

proto_text = """syntax = "proto3";\n\npackage {};\n\nimport "google/protobuf/timestamp.proto";\n\n{}\n\n{}"""


class ProtoHelper:
    def __init__(
        self,
        servicer_name: str = None,
        save_dir: str = None,
        proto_location: str = None,
    ):
        """
        Args:
            servicer_name: 转换的服务名称
            save_dir: proto文件保存位置
            proto_location: proto文件package相对位置
        """
        if servicer_name:
            self._servicer_list = [frog.servicer_map[servicer_name]]
        else:
            self._servicer_list = frog.servicer_map.values()
        self._save_dir = save_dir
        self._proto_location = proto_location or "grpc_frog.proto"

    def generate_code(self):
        for servicer in self._servicer_list:
            if not servicer.bind_method_map:
                log.info("{} has no bind method".format(servicer.name))
                continue
            out_dir = self._save_dir or servicer.proto_dir
            proto_file = os.path.join(out_dir, "{}.proto".format(servicer.name))
            self._generate_proto_file(servicer, proto_file)

    def _generate_proto_file(self, servicer: Servicer, proto_file: str):
        """生成proto文件"""
        required_proto_type = set()
        for _method in servicer.bind_method_map.values():
            for msg in _method.py_type_set:
                required_proto_type.add(msg)

        required_message_type = required_proto_type - set(
            proto_type_recorder.proto_base_type.keys()
        )

        if len(required_message_type) == 0:
            # no message means no modules and method
            return
        # proto
        proto_str = self._get_service_body(servicer)
        # 准备rpc需要的message body
        proto_message_types = [
            proto_type_recorder.translate_2_proto_message(i)
            for i in required_message_type
        ]
        messages = "\n\n".join(proto_message_types)
        # 拼装成proto文件
        proto_body = proto_text.format(servicer.name, messages, proto_str)
        # save
        with open(proto_file, "w", encoding="utf8") as f:
            f.write(proto_body)
        # 生成pb2文件
        generate_pb2_file(proto_file)

    def _get_service_body(self, servicer: Servicer) -> str:
        """获取method的proto形式"""
        ret = []
        for method in servicer.bind_method_map.values():
            rpc_body = "rpc {method_name}({request_name}) returns ({response_name}) {{}};".format(
                method_name=method.name,
                request_name=method.request_name,
                response_name=method.response_name,
            )
            ret.append(rpc_body)
        proto_str = "service {name} {{\n  {method_str}\n}}".format(
            name=servicer.name, method_str="\n  ".join(ret)
        )

        return proto_str


def generate_proto_file(
    servicer_name: str = None, save_dir: str = None, proto_location: str = None
):
    """
    生成proto文件

    Args:
        servicer_name: 服务名称
        save_dir: proto文件保存位置
        proto_location: proto文件package相对位置
    """
    ProtoHelper(
        servicer_name=servicer_name, save_dir=save_dir, proto_location=proto_location
    ).generate_code()
