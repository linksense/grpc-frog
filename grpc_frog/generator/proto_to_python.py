#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/2/19 17:22
# Copyright 2021 LinkSense Technology CO,. Ltd

import os
import re
from distutils.dir_util import copy_tree

import grpc_frog.template.model as model
from grpc_frog import proto_type_recorder

_servicer_text = """
import os
from typing import List, Dict
from .model_{proto_name} import {models}
from grpc_frog import Servicer, frog

servicer = Servicer("{proto_name}")
frog.add_servicer(servicer)


{func_code}

# client
# frog.client_init("grpc://127.0.0.1:50065", proto_dir=os.path.join(r"{package_dir}", "proto"))

# server
# frog.bind_servicer(server, proto_dir=os.path.join(r"{package_dir}", "proto"))
"""


class PyCodeHelper:
    mapping = {
        'int64': 'int',
        'string': 'str',
        'bool': 'bool',
        'float': 'float',
        "google.protobuf.Timestamp": "datetime.datetime",
    }

    def __init__(self, package_dir, pb_file_dir, use_for="client"):
        """python生成助手
        :param package_dir: 生成的代码地址
        :param pb_file_dir: 目前pb.py和pb2_grpc的存放地址
        :param use_for: 用于生成客户端或者服务端代码
        """
        if not os.path.isdir(package_dir):
            raise ValueError("{} is not dictionary".format(package_dir))
        if not os.path.isdir(pb_file_dir):
            raise ValueError("{} is not dictionary".format(pb_file_dir))
        if use_for not in ("client", "server"):
            raise ValueError("use_for should be client or server")

        self._use_for = use_for

        self._package_dir = package_dir
        self._pb_file_dir = pb_file_dir

        self._proto_files = []
        self._pb2_files = []
        self._pb2_grpc_files = []

        for file_name in os.listdir(self._pb_file_dir):
            if file_name.endswith(".proto"):
                self._proto_files.append(file_name[:- len(".proto")])
            elif file_name.endswith("pb2.py"):
                self._pb2_files.append(file_name[:- len("pb2.py") - 1])
            elif file_name.endswith("pb2_grpc.py"):
                self._pb2_grpc_files.append(file_name[:- len("pb2_grpc.py") - 1])

    def generate_code(self):
        """生成C端"""
        # 复制proto文件夹
        copy_tree(self._pb_file_dir, os.path.join(self._package_dir, "proto"))
        for proto_name in self._proto_files:
            print("start proto file:", proto_name)
            # 生成model文件
            models = self._generate_models_file(proto_name)
            # 生成servicer文件
            self._generate_service_file(proto_name, models)
        return

    def _generate_models_file(self, proto_name):
        """生成model文件"""
        modules = {}
        relationship = dict()  # 类名 : [依赖类1,依赖类2]
        with open(os.path.join(self._pb_file_dir, "{}.proto".format(proto_name)), 'r', encoding='utf8') as f:
            proto_file = f.read()
        message_text = re.findall(r"message (\w*) ({[^\}]*})", proto_file)
        for name, fields_code in message_text:
            if name[0].islower():
                continue
            field_codes, unknown_py_type = self._get_struct_from_proto(fields_code)
            modules[name] = field_codes
            relationship[name] = unknown_py_type

        ret = open(model.__file__, "r", encoding="utf8").read()
        relationship = list(relationship.items())
        while len(relationship) != 0:
            name, required = relationship.pop(0)
            if not required:
                ret += "\n\n@frog.model()\nclass {}(BaseModel):\n    {}\n".format(name, "\n    ".join(modules[name]))
                for _, _required in relationship:
                    if name in _required:
                        _required.pop()
            else:
                relationship.append((name, required))
        # 输出
        with open(os.path.join(self._package_dir, "model_{}.py".format(proto_name)), "w", encoding="utf8") as f:
            f.write(ret)
        return modules.keys()

    def _generate_service_file(self, proto_name, models=[]):
        """生成接口文件"""
        with open(os.path.join(self._pb_file_dir, "{}.proto".format(proto_name)), 'r', encoding='utf8') as f:
            proto_body = f.read()
        func_list = re.findall(r"rpc (\w*)\((\w*)\) returns \((\w*)\) \{\};", proto_body)

        func_codes = ""
        for func_name, req, resp in func_list:
            if "_" in req:
                message_text = re.findall("message {}[^}}]*}}".format(req), proto_body)[0]
                req, _ = self._get_struct_from_proto(message_text)
            func_code = self._get_func_code(func_name, req, resp)
            func_codes += func_code + "\n\n"

        out_text = _servicer_text.format(proto_name=proto_name, models=", ".join(models) or "*",
                                         func_code=func_codes, package_dir=self._package_dir)

        # 输出
        out_file = os.path.join(self._package_dir, "servicer_{}.py".format(proto_name))
        with open(out_file, "w", encoding="utf8") as f:
            f.write(out_text)
        return

    def _get_struct_from_proto(self, proto):
        """
        将proto文件的message
        field
        转换成python代码
        """
        unknown_py_type = []
        field_list = proto[proto.find("{") + 1:proto.rfind(";")].split(";")

        def _get_type(message_type):
            """获取CMessages对应的python类型，并记录自定义类型"""
            if message_type in self.mapping:
                return self.mapping[message_type]
            else:
                unknown_py_type.append(message_type)
                return message_type

        ret_params = []
        for field in field_list:
            field = field.strip()
            if field.startswith("repeated"):
                _, _type, _name, *_ = field.split()
                _type_text = _get_type(_type)
                ret_params.append("{}: List[{}] = {}()".format(_name, _type_text, "list"))
            elif field.startswith("map"):
                field = field.replace("<", " ").replace(",", " ").replace(">", " ")
                _, _type_key, _type_value, _name, *_ = field.split()
                _key = _get_type(_type_key)
                _value = _get_type(_type_value)
                ret_params.append("{}: Dict[{}, {}] = {}()".format(_name, _key, _value, "dict"))
            else:
                _type, _name, *_ = field.split()
                _type_text = _get_type(_type)
                _default_value = proto_type_recorder.get_py_default_value(_type_text)
                ret_params.append("{}: {} = {}()".format(_name, _type_text, _default_value))
        return ret_params, unknown_py_type

    def _get_func_code(self, func_name, req, resp):
        if self._use_for == "client":
            func_code = """@servicer.remote_method({})\ndef {}({}) -> {}:\n    ...\n"""
        else:
            func_code = """@servicer.grpc_method({})\ndef {}({}) -> {}:\n    raise NotImplementedError\n"""
        return func_code.format(resp, func_name, ", ".join(req), resp)


def generate_py_code(package_dir, proto_dir=None, use_for="client"):
    """生成python文件"""
    if proto_dir is None:
        proto_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "proto")
    PyCodeHelper(package_dir, proto_dir, use_for).generate_code()
