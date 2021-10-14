#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/2/19 17:22
# Copyright 2021 LinkSense Technology CO,. Ltd
"""将proto转换成python model"""
import os
import re
from shutil import copyfile
from typing import Dict, Iterator, List, Tuple

import grpc_frog.template.model as model
from grpc_frog.core import log, proto_type_recorder
from grpc_frog.core.proto_type_recorder import proto_base_type
from grpc_frog.generator.pb_fiile_util import generate_pb2_file

_servicer_text = """
import os
from typing import List, Dict
from .model_{proto_name} import {models}
from grpc_frog import Servicer, frog


proto_dir = os.path.join(os.path.dirname(__file__), "proto")
servicer = Servicer("{proto_name}", proto_dir=proto_dir)
frog.add_servicer(servicer)


{func_code}
def init_client() -> None:  # pragma: no cover
    proto_dir = os.path.join(r"{package_dir}", "proto")
    frog.client_init("grpc://127.0.0.1:50065", proto_dir=proto_dir)


def init_server() -> None:  # pragma: no cover
    import grpc
    from concurrent import futures
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    proto_dir = os.path.join(r"{package_dir}", "proto")
    frog.bind_servicer(server, proto_dir=proto_dir)
"""


class PyCodeHelper:
    mapping = {v: k for k, v in proto_base_type.items()}

    def __init__(
        self,
        target_dir: str,
        proto_dir: str,
        use_for: str = "client",
    ):
        """python生成助手
        :param target_dir: 生成的代码地址
        :param proto_dir: 目前pb.py和pb2_grpc的存放地址
        :param use_for: 用于生成客户端或者服务端代码
        """
        if not os.path.isdir(target_dir):
            raise ValueError("{} is not dictionary".format(target_dir))

        if use_for not in ("client", "server"):
            raise ValueError("use_for should be client or server")

        self._use_for = use_for

        self._target_dir = target_dir
        self._pb_file_dir = proto_dir

        self._proto_files = []
        self._pb2_files = []
        self._pb2_grpc_files = []

        for file_name in os.listdir(self._pb_file_dir):
            if file_name.endswith(".proto"):
                self._proto_files.append(file_name[: -len(".proto")])

    def generate_code(self) -> None:
        """生成C端"""
        # 复制proto文件夹
        dst_dir = os.path.join(self._target_dir, "proto")
        os.makedirs(dst_dir, exist_ok=True)
        for proto_name in self._proto_files:
            log.info("开始处理{}.proto".format(proto_name))
            dst_proto_file = self._make_pb2_file(dst_dir, proto_name)
            # 生成model文件
            models = self._generate_models_file(proto_name)
            # 生成servicer文件
            self._generate_service_file(proto_name, dst_proto_file, models)
        log.info("在{}生成代码完成".format(self._target_dir))

    def _make_pb2_file(self, dst_dir, proto_name):
        src = os.path.join(self._pb_file_dir, proto_name + ".proto")
        dst_proto_file = os.path.join(dst_dir, proto_name + ".proto")
        copyfile(src, dst_proto_file)
        log.info("start proto file:", proto_name)
        generate_pb2_file(dst_proto_file)
        return dst_proto_file

    def _generate_models_file(self, proto_name: str) -> Iterator[str]:
        """生成model文件"""
        modules = {}
        relationship = dict()  # 类名 : [依赖类1,依赖类2]
        # 获取proto内容
        proto_file = os.path.join(self._pb_file_dir, "{}.proto".format(proto_name))
        with open(proto_file, "r", encoding="utf8") as f:
            proto_file = f.read()
        # 解析model
        message_text = re.findall(r"message (\w*) ({[^\}]*})", proto_file)
        for _name, _fields_code in message_text:
            if _name[0].islower():
                continue
            field_codes, unknown_py_type = self._get_struct_from_proto(_fields_code)
            modules[_name] = field_codes
            relationship[_name] = unknown_py_type
        # 判断依赖关系
        model_code = open(model.__file__, "r", encoding="utf8").read()
        relationship = list(relationship.items())
        while len(relationship) != 0:
            _name, required = relationship.pop(0)
            if not required:
                model_code += _get_no_required_model_code(_name, modules, relationship)
            else:
                relationship.append((_name, required))
        # 输出
        model_file = os.path.join(self._target_dir, "model_{}.py".format(proto_name))
        format_code = _format_code(model_code)
        with open(model_file, "w", encoding="utf8") as f:
            f.write(format_code)
        return list(modules.keys())

    def _generate_service_file(
        self, proto_name: str, dst_proto_file: str, models: Iterator[str]
    ):
        """生成接口文件"""
        with open(dst_proto_file, "r", encoding="utf8") as f:
            proto_body = f.read()
        _rpc_re = r"rpc (\w*)\((\w*)\) returns \((\w*)\) \{\};"
        func_list = re.findall(_rpc_re, proto_body)
        # 获得函数代码
        func_codes = ""
        for _func_name, _req, _resp in func_list:
            # 转换成函数代码
            _func_code = self._get_func_code(_func_name, _req, _resp, proto_body)
            func_codes += _func_code + "\n\n"
        # 整合成文件
        out_text = _servicer_text.format(
            proto_name=proto_name,
            models=", ".join(models) or "*",
            func_code=func_codes,
            package_dir=self._target_dir,
        )
        # 输出
        out_file = os.path.join(self._target_dir, "servicer_{}.py".format(proto_name))
        format_code = _format_code(out_text)
        with open(out_file, "w", encoding="utf8") as f:
            f.write(format_code)
        return

    def _get_struct_from_proto(self, proto: str) -> Tuple[List[str], List[str]]:
        """
        将proto文件的message
        field
        转换成python代码
        """
        unknown_py_type = []
        field_list = proto[proto.find("{") + 1: proto.rfind(";")].split(";")

        def _get_type(message_type):
            """获取CMessages对应的python类型，并记录自定义类型"""
            if message_type in self.mapping:
                class_obj = self.mapping[message_type]
                ret: str = class_obj.__module__ + "." + class_obj.__qualname__
                if ret.startswith("builtins."):
                    ret = ret.replace("builtins.", "")
                return ret
            else:
                unknown_py_type.append(message_type)
                return message_type

        ret_params = []
        for field in field_list:
            field = field.strip()
            if field.startswith("repeated"):
                _, _type, _name, *_ = field.split()
                _type_text = _get_type(_type)
                ret_params.append(
                    "{}: List[{}] = {}()".format(_name, _type_text, "list")
                )
            elif field.startswith("map"):
                field = field.replace("<", " ").replace(",", " ").replace(">", " ")
                _, _type_key, _type_value, _name, *_ = field.split()
                _key = _get_type(_type_key)
                _value = _get_type(_type_value)
                ret_params.append(
                    "{}: Dict[{}, {}] = {}()".format(_name, _key, _value, "dict")
                )
            elif field:
                _type, _name, *_ = field.split()
                _type_text = _get_type(_type)
                _default_value = proto_type_recorder.get_py_default_value(_type_text)
                ret_params.append(
                    "{}: {} = {}()".format(_name, _type_text, _default_value)
                )
            else:  # field = ""
                print("[warming] 空 message: {} ".format(proto.replace("\n", "")))
        return ret_params, unknown_py_type

    def _get_func_code(
        self, func_name: str, req: str, resp: str, proto_body: str
    ) -> str:
        if "_" in req:
            _re_result = re.findall("message {}[^}}]*}}".format(req), proto_body)
            message_text = _re_result[0]
            # 获取函数输入输出
            req, _ = self._get_struct_from_proto(message_text)
        if self._use_for == "client":
            func_code = """@servicer.remote_method({})\ndef {}({}) -> {}:\n    ...  # pragma: no cover\n"""
        else:
            func_code = """@servicer.grpc_method({})\ndef {}({}) -> {}:\n    raise NotImplementedError\n"""
        return func_code.format(resp, func_name, ", ".join(req), resp)


def _get_no_required_model_code(
    _name: str, modules: Dict[str, List[str]], relationship: List[Tuple[str, List[str]]]
):
    model_template = "\n\n@frog.model()\nclass {}(BaseModel):\n    {}\n"
    ret = model_template.format(_name, "\n    ".join(modules[_name]))
    # 依赖关系图中去除已写入的model
    for _, _required in relationship:
        if _name in _required:
            _required.pop()
    return ret


def _format_code(code: str) -> str:
    """使用black插件格式化python代码"""
    import black

    mode = black.Mode(
        target_versions={black.TargetVersion.PY36},
        line_length=120,
        string_normalization=False,
        is_pyi=False,
    )
    format_ret = black.format_str(code, mode=mode)
    return format_ret


def generate_py_code(
    package_dir: str, proto_dir: str = None, use_for: str = "client"
) -> None:
    """生成python文件"""
    if proto_dir is None:
        proto_dir = os.path.join(package_dir, "proto")
    PyCodeHelper(package_dir, proto_dir, use_for).generate_code()
