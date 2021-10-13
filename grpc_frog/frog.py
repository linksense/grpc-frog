#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/15 11:00
# Copyright 2021 LinkSense Technology CO,. Ltd
import os
import re
from typing import Dict

import grpc

from grpc_frog import proto_type_recorder
from grpc_frog.servicer import Servicer


class Frog:
    """
    包抽象对象

    管理
    """

    servicer_map: Dict[str, Servicer] = dict()  # servicer_name : servicer
    _uri_map = {}  # servicer_name : uri
    channel_options = []  # grpc channel_options

    def add_servicer(self, servicer: Servicer):
        """绑定servicer"""
        self.servicer_map[servicer.name] = servicer

    def generate_proto_file(self, servicer_name=None, save_dir=None):
        """生成proto文件"""
        if servicer_name:
            return self.servicer_map[servicer_name].generate_proto_file(save_dir)
        else:
            for servicer in self.servicer_map.values():
                servicer.generate_proto_file(save_dir)

    def remote_method(self, servicer_name="default", *args, **kwargs):
        """声明这是一个远程调用函数"""
        return self.servicer_map["servicer_name"].remote_method(*args, **kwargs)

    def model(self, *args, **kwargs):
        """
        将sqlalchemy model转换成proto文件
        需要实现 model与dict 之间的抓换 dict/from_obj
        proto_name: 在proto里的名字默认为类名
        """

        def wrapper(model):
            proto_type_recorder.register_py_type(model, *args, **kwargs)
            return model

        return wrapper

    def bind_servicer(self, server: grpc.server, frog_servicer):
        """
        装载servicer

        :param server: grpc.server对象
        :param frog_servicer: grpc_frog.servicer对象
        :return: grpc.server对象
        """
        pb2_grpc = frog_servicer.get_pb2_grpc()
        # bp_grpc get servicer
        servicer_name = "{}Servicer".format(frog_servicer.name)
        servicer_grpc = getattr(pb2_grpc, servicer_name)
        # add method
        for method_name, _method in frog_servicer.bind_method_map.items():
            setattr(servicer_grpc, method_name, staticmethod(_method.func))
        # add server
        add_func_name = "add_{}_to_server".format(servicer_name)
        add_func = getattr(pb2_grpc, add_func_name)
        add_func(servicer_grpc, server)
        return server

    def clear_proto_cache(self):
        """清空 .proto 和 pb2 文件缓存"""
        dir_path = os.path.join(os.path.dirname(__file__), "proto")
        file_list = os.listdir(dir_path)
        for i in file_list:
            if (i.endswith(".py") or i.endswith(".proto")) and (i != "__init__.py"):
                os.remove(os.path.join(dir_path, i))

    def client_init(self, uri, proto_dir=None):
        """
        client端初始化用
        :param uri: eg. grpc://127.0.0.1:5000 zookeeper://127.0.0.1:5000/servicer_name
        :param proto_dir: servicer所使用的proto文件
        """
        match_obj = re.match(r"(\w*)://([\w.]*):(\d*)/?(\w*)", uri)
        if match_obj is None:
            raise ValueError(
                "{}错误 e.g zookeeper://127.0.0.1:5000/servicer_name".format(uri)
            )
        *_, servicer_name = match_obj.groups()
        if servicer_name not in self.servicer_map.keys():
            raise ValueError(
                "{}未在frog中注册,当前已组测服务为{}".format(
                    servicer_name or "None", self.servicer_map.keys()
                )
            )
        self._uri_map[servicer_name] = uri
        self.servicer_map[servicer_name].client_init(uri, proto_dir)

    def __getitem__(self, servicer_name):
        if servicer_name not in self.servicer_map.keys():
            self.servicer_map[servicer_name] = Servicer(servicer_name)
        return self.servicer_map[servicer_name]

    def get_servicer_uri(self, servicer_name):
        """ 通过服务名称获取连接的uri """
        if servicer_name not in self._uri_map:
            raise KeyError("未初始化 {} client".format(servicer_name))
        return self._uri_map[servicer_name]

    def set_channel_options(self, options: list):
        self.channel_options += options

    def get_channel_options(self):
        grpc_max_length = (
            os.environ.get("grpc_frog__grpc_max_length") or 512 * 1024 * 1024
        )
        options = [
            ("grpc.max_send_message_length", grpc_max_length),
            ("grpc.max_receive_message_length", grpc_max_length),
        ]
        return options + self.channel_options


frog = Frog()

__all__ = ["frog"]
