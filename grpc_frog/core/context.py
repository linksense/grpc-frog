#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/19 14:45
# Copyright 2021 LinkSense Technology CO,. Ltd
"""
Context 当前上下文
"""
import logging


class Context:
    """
    保存当前(最后grpc调用的)上下文

    method: 调用函数
    request_message: 请求参数 CMessage
    request_model:  函数输入参数转换的成的 pydantic Obj
    response_model: 函数输出的pydantic Obj
    rpc_context:  GrpcStub(Client) or GrpcContext(Server)
    """

    def __init__(self):
        self.method = None
        self.request_message = None
        self.request_model = None
        self.response_model = None
        self.rpc_context = None

    def clear(self):
        """ 清理缓存 """
        self.method = None
        self.request_message = None
        self.request_model = None
        self.response_model = None
        self.rpc_context = None

    def fill(self, method, request_message, request_model, response_model, rpc_context):
        """ 装填数据 """
        # 释放全局
        self.clear()
        self.method = method
        self.request_message = request_message
        self.request_model = request_model
        self.response_model = response_model
        self.rpc_context = rpc_context


context = Context()
del Context
log = logging.getLogger("grpc_frog")
