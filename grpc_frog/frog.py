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
from grpc_frog.zk_utils import DistributedChannel


class Frog:
    servicer_map: Dict[str, Servicer] = dict()  # servicer_name : servicer

    def __init__(self):
        # d端
        self.default_servicer = Servicer("default")
        self.servicer_map["default"] = self.default_servicer

        self.add_request_extra_field = self.default_servicer.add_request_extra_field
        self.register_handle_extra_field_callable_func = self.default_servicer.register_handle_extra_field_callable_func
        self.add_response_extra_field = self.default_servicer.add_response_extra_field
        # c端
        self._channel = None
        self.driver = self.ip = self.port = self.servicer_name = None

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

    def grpc_method(self, *args, **kwargs):
        """注册一个method"""
        return self.default_servicer.grpc_method(*args, **kwargs)

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

    def bind_servicer(self, server: grpc.server, proto_dir=None):
        """装载servicer"""
        self.set_proto_dir(proto_dir)
        for service_name, servicer in self.servicer_map.items():
            if not servicer.bind_method_map:
                continue
            pb2_grpc = servicer.get_pb2_grpc()
            # bp_grpc get servicer
            servicer_name = "{}Servicer".format(service_name)
            servicer_grpc = getattr(pb2_grpc, servicer_name)
            # add method
            for method_name, _method in servicer.bind_method_map.items():
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
        :param proto_dir:
        :return:
        """
        match_obj = re.match(r"(\w*)://([\d.]*):(\d*)/?(\w*)", uri)
        if match_obj is None:
            raise ValueError("{}错误 e.g zookeeper://127.0.0.1:5000/servicer_name".format(uri))
        self.driver, self.ip, self.port, self.servicer_name = match_obj.groups()
        if self.driver == "grpc":
            self._channel = None
        elif self.driver == "zookeeper":
            self._channel = DistributedChannel(self.ip, self.port, self.servicer_name)
        else:
            raise ValueError("driver 错误 请选择 [grpc|zookeeper]")

        self.set_proto_dir(proto_dir)

    def set_proto_dir(self, proto_dir=None):
        """设置grpc运行的位置"""
        if proto_dir is not None:
            Servicer.proto_dir = proto_dir
            for name, service in self.servicer_map.items():
                service.proto_dir = proto_dir

    def __getitem__(self, servicer_name):
        if servicer_name not in self.servicer_map.keys():
            self.servicer_map[servicer_name] = Servicer(servicer_name)
        return self.servicer_map[servicer_name]

    @property
    def channel_url(self):
        """获取 channel"""
        if self.driver == "grpc":
            return '{}:{}'.format(self.ip, self.port)
        else:  # self.driver == "zookeeper":
            server = self._channel.get_server()
            _uri = "{}:{}".format(server.get("host"), server.get("port"))
            return _uri


frog = Frog()

__all__ = ["frog"]
