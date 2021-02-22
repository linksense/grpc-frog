#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/19 14:45
# Copyright 2021 LinkSense Technology CO,. Ltd


class Context:
    def __init__(self):
        self.method = None
        self.request_message = None
        self.request_model = None
        self.response_model = None
        self.rpc_context = None

    def clear(self):
        self.method = None
        self.request_message = None
        self.request_model = None
        self.response_model = None
        self.rpc_context = None

    def fill(self, method, request_message, request_model, response_model, rpc_context, ):
        self.method = method
        self.request_message = request_message
        self.request_model = request_model
        self.response_model = response_model
        self.rpc_context = rpc_context


context = Context()
del Context
