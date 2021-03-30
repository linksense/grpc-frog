#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/2/19 17:22
# Copyright 2021 LinkSense Technology CO,. Ltd
import os
import shutil

from grpc_frog import frog, proto_type_recorder
from grpc_tools import protoc

proto_text = """syntax = "proto3";\n\npackage {};\n\nimport "google/protobuf/timestamp.proto";\n\n{}\n\n{}"""
service_text = "service {name} {{\n  {method_str}\n}}"


class ProtoHelper:
    def __init__(self, servicer_name=None, save_dir=None):
        self._servicer_list = (frog.servicer_map[servicer_name],) if servicer_name else frog.servicer_map.values()
        self._save_dir = save_dir

    def generate_code(self):
        for servicer in self._servicer_list:
            if not servicer.bind_method_map:
                continue
            proto_file = os.path.join(servicer.proto_dir, servicer.name + ".proto")
            pb2_file = os.path.join(servicer.proto_dir, servicer.name + "_pb2.py")  # pb2 决定对路径
            pb2_grpc_file = os.path.join(servicer.proto_dir, servicer.name + "_pb2_grpc.py")  # pb2 grpc 绝对路径
            self.generate_proto_file(servicer, proto_file, pb2_file, pb2_grpc_file)

    def generate_proto_file(self, servicer, proto_file, pb2_file, pb2_grpc_file):
        """生成proto文件"""
        required_proto_type = {msg for _method in servicer.bind_method_map.values() for msg in _method.py_type_set}
        required_message_type = required_proto_type - set(proto_type_recorder.proto_base_type.keys())

        if len(required_message_type) == 0:
            # no message means no modules and method
            return
        # proto
        method_str = self.get_message_body(servicer)
        _proto_str = "service {name} {{\n  {method_str}\n}}".format(name=servicer.name, method_str=method_str)
        messages = "\n\n".join([proto_type_recorder.translate_2_proto_message(i) for i in required_message_type])
        text = proto_text.format(servicer.name, messages, _proto_str)
        # save
        with open(proto_file, "w", encoding="utf8") as f:
            f.write(text)
        # 生成pb2文件
        self._generate_pb2_file(servicer, proto_file, pb2_file, pb2_grpc_file)

    def _generate_pb2_file(self, servicer, proto_file, pb2_file, pb2_grpc_file):
        """生成pb文件"""
        # copy google dir
        google_dir = os.path.join(servicer.proto_dir, "google")
        if not os.path.exists(google_dir):
            import grpc_frog
            frog_google_dir = os.path.join(os.path.dirname(grpc_frog.__file__), "proto", "google")
            shutil.copytree(frog_google_dir, google_dir)

        protoc_result = protoc.main(
            (
                '',
                '-I' + servicer.proto_dir,
                '--python_out=' + servicer.proto_dir,
                '--grpc_python_out=' + servicer.proto_dir,
                proto_file,
            )
        )
        if protoc_result == 1:
            raise SyntaxError("编译{}下的文件时产生了一个错误".format(servicer.proto_dir))
        file_data = open(pb2_grpc_file, "r", encoding="utf8").read()
        file_data = file_data.replace("import {}".format(servicer.name),
                                      "# todo need changed to your proto\nfrom grpc_frog.proto import {}".format(
                                          servicer.name))
        with open(pb2_grpc_file, "w", encoding="utf8") as f:
            f.write(file_data)

    @staticmethod
    def get_message_body(servicer):
        """获取method的proto形式"""
        define_text = "rpc {}({}) returns ({}) {{}};"
        ret = [define_text.format(method.name, method.request_name, method.response_name)
               for method in servicer.bind_method_map.values()]
        return "\n  ".join(ret)


def generate_proto_file(servicer_name=None, save_dir=None):
    """生成proto文件"""
    ProtoHelper(servicer_name=servicer_name, save_dir=save_dir).generate_code()
