#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/20 10:28
# Copyright 2021 LinkSense Technology CO,. Ltd
import functools
import importlib
import inspect
import os

import grpc

import grpc_frog.proto as proto
from grpc_frog.context import context
from grpc_frog.method import Method


class Servicer:
    proto_dir = os.path.dirname(proto.__file__)  # 存放proto文件的包

    def __init__(self, name):
        self.name = name
        self.bind_method_map = {}  # str:function
        self.request_extra_field_map = {}  # str:py_type
        self.response_extra_field_map = {}  # str:py_type
        self.handle_extra_field_callable_func = {}  # str:callable_func

    @functools.lru_cache()
    def get_pb2(self):
        """获取当前servicer的pb2对象"""
        file_path = os.path.join(self.proto_dir, "{}_pb2.py".format(self.name))
        spec = importlib.util.spec_from_file_location(self.name, file_path)
        pb2 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pb2)
        return pb2

    def get_pb2_grpc(self):
        """获取当前servicer的pb2_grpc对象"""
        file_path = os.path.join(self.proto_dir, "{}_pb2_grpc.py".format(self.name))
        spec = importlib.util.spec_from_file_location(self.name, file_path)
        pb2_grpc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pb2_grpc)
        return pb2_grpc

    def register_method(self, func, response_model=None, request_model=None):
        """给当前服务注册一个方法"""
        _m = Method(func, self, response_model, request_model)
        self.bind_method_map[_m.name] = _m
        return _m

    def add_request_extra_field(self, field_name: str, field_py_type: type):
        """增加method请求体体默认参数"""
        self.request_extra_field_map[field_name] = field_py_type

    def add_response_extra_field(self, field_name: str, field_py_type: type):
        """增加method响应体的默认参数"""
        self.response_extra_field_map[field_name] = field_py_type

    def grpc_method(self, *args, **kwargs):
        """注册一个method"""

        # 第一层 获取参数
        def _record_method(func):
            # 第二层 修改func
            @functools.wraps(func)
            def wrapper(request, _context):
                # 第三层 处理Input Output
                _m = self.bind_method_map[func.__name__]
                # 将当前请求相关参数放入全局context
                context.fill(_m, request, _m.request_model, _m.response_ret_2_message, _context)
                # 将CMessage转成dict
                kw_args = _m.request_message_2_dict(request)
                # 去除外加的参数
                self._handle_extra_fields(kw_args)
                # 调用函数逻辑
                func_ret = func(**kw_args)
                # 将函数返回值(model)转换成CMessage
                ret = _m.response_ret_2_message(func_ret)
                # 释放全局
                context.clear()
                return ret

            self.register_method(wrapper, *args, **kwargs)
            return func

        return _record_method

    def _handle_extra_fields(self, kw_args: dict):
        """过滤掉额外的字段 触发hook函数"""
        for field_name in self.request_extra_field_map.keys():
            value = kw_args.pop(field_name)
            self.handle_extra_field_callable_func[field_name](value)

    def register_handle_extra_field_callable_func(self, field_name, callable_func):
        self.handle_extra_field_callable_func[field_name] = callable_func

    def remote_method(self, *args, **kwargs):
        """记录可以远程调用的method"""

        # 第一层 获取参数
        def _record_method(func):
            # 第二层 修改func
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # 第三层 处理Input Output
                from grpc_frog import frog
                _m = self.bind_method_map[func.__name__]
                # 将函数参数转换成CMessage
                sig = inspect.signature(func)
                bound_values = sig.bind(*args, **kwargs)
                message = _m.request_ret_2_message(dict(**bound_values.arguments))
                # 远程调用函数
                with grpc.insecure_channel(frog.channel_url) as channel:
                    self._stub = getattr(self.get_pb2_grpc(), "{}Stub".format(self.name))(channel)
                    context.fill(_m, message, _m.request_model, _m.response_ret_2_message, self._stub)
                    remote_result = getattr(self._stub, func.__name__)(message)
                # 将CMessage转换成dict 并装填到response_model中
                res_obj = _m.response_model(**_m.response_message_2_dict(remote_result))
                context.clear()
                return res_obj

            self.register_method(wrapper, *args, **kwargs)
            return wrapper

        return _record_method

    def get_pb2_message(self, message_name):
        """获取CMessages对象"""
        return getattr(self.get_pb2(), message_name)
