#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/19 18:25
# Copyright 2021 LinkSense Technology CO,. Ltd

from grpc_frog import proto_type_recorder


class Method:
    def __init__(self, func, servicer, response_model=None, request_model=None):
        self.func = func
        self.name = func.__name__
        self.servicer = servicer

        self._parse_request(request_model)
        self._parse_response(response_model)

        _type_list = [self.request_model, self.response_model]
        self.py_type_set = proto_type_recorder.get_base_type(_type_list)

    def _parse_response(self, response_model):
        """解析返回体参数模型
        用户可以直接在函数末尾注明参数
        """
        if response_model is None:
            # 来自函数的注解
            response_model = self.func.__annotations__["return"]
            # 可能给dict 和 pydantic model
            if response_model in proto_type_recorder.proto_base_type:
                # base type
                raise NotImplementedError("不支持基本类型作为返回值，(没有name)")
            response_model = self.func.__annotations__["return"]

        self.response_name = response_model.__name__
        self.response_model = response_model
        proto_type_recorder.register_py_type(response_model, message_name=self.response_name)

    def _parse_request(self, request_model):
        """解析函数的请求参数
        如果有request_model,则用model的注解
        """
        _fields = {k: v for k, v in self.func.__annotations__.items() if k != "return"}
        _fields.update(self.servicer.request_extra_field_map)
        if request_model is None:
            request_model = proto_type_recorder.register_by_dict(_fields, "{}_request".format(self.name))
        else:
            if set(request_model.__annotations__.keys()) != set(_fields.keys()):
                raise NotImplementedError("[{}]该方法注入的{}与函数参数不同，记录失败".format(self.name, request_model))

        self.request_name = request_model.__name__
        self.request_model = request_model
        proto_type_recorder.register_py_type(request_model, message_name=self.request_name)

    def request_message_2_dict(self, request):
        """将grpc的CMessages对象换成成函数参数"""
        struct_dict = proto_type_recorder.message_collections[self.request_model]
        return proto_type_recorder.message_to_dict(request, struct_dict)

    def response_message_2_dict(self, response):
        """将grpc的CMessages对象换成成函数参数"""
        struct_dict = proto_type_recorder.message_collections[self.response_model]
        return proto_type_recorder.message_to_dict(response, struct_dict)

    def response_ret_2_message(self, return_data):
        """将函数返回体转换为CMessage"""
        if not isinstance(return_data, dict):
            return_data = return_data.dict()
        message = getattr(self.servicer.get_pb2(), self.response_name)()
        return proto_type_recorder.dict_to_message(return_data, message, self.response_model, self.servicer)

    def request_ret_2_message(self, return_data):
        """将函数返回体转换为CMessage"""
        if not isinstance(return_data, dict):
            return_data = return_data.dict()
        message = getattr(self.servicer.get_pb2(), self.request_name)()
        return proto_type_recorder.dict_to_message(return_data, message, self.request_model, self.servicer)
