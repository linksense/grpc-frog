#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/27 11:20
# Copyright 2021 LinkSense Technology CO,. Ltd
from typing import Dict, List

from pydantic import BaseModel as _BaseModel

from grpc_frog import frog
from grpc_frog.servicer import Servicer

test_servicer = Servicer("grpc_test")
frog.add_servicer(test_servicer)


class BaseModel(_BaseModel):
    class Config:
        arbitrary_types_allowed = True
        orm_mode = True


@frog.model()
class HelloModel(BaseModel):
    int_field: int = 0
    float_field: float = 0.0
    str_field: str = ""
    list_int_field: List[int] = list()
    map_int_field: Dict[str, int] = dict()

    def increment_one(self):
        self.int_field += 1
        self.float_field += 1
        self.str_field += "1"
        self.list_int_field = [number + 1 for number in self.list_int_field]

        for k, v in self.map_int_field.items():
            self.map_int_field[k] = v + 1

    @classmethod
    def from_orm(cls, obj):
        _obj = cls()
        _obj.int_field = getattr(obj, "int_field", _obj.int_field)
        _obj.float_field = getattr(obj, "float_field", _obj.float_field)
        _obj.str_field = getattr(obj, "str_field", _obj.str_field)
        _obj.list_int_field = getattr(obj, "list_int_field", _obj.list_int_field)
        _obj.map_int_field = dict(getattr(obj, "map_int_field", _obj.map_int_field))
        return _obj


class ResponseModel(BaseModel):
    int_a: int = 0
    float_b: float = 0.0
    string_c: str = ""
    repeated_model_d: List[HelloModel] = list()
    map_model_e: Dict[str, int] = dict()


@test_servicer.grpc_method()
def echo_with_increment_one_base(request_model: ResponseModel) -> ResponseModel:
    kwargs = request_model.dict()
    res: dict = echo_with_increment_one(**kwargs)
    response_model = ResponseModel(**res)
    return response_model


@test_servicer.grpc_method(response_model=ResponseModel)
def echo_with_increment_one(int_a: int, float_b: float, string_c: str,
                            repeated_model_d: List[HelloModel],
                            map_model_e: Dict[str, int]) -> dict:
    int_a += 1
    float_b += 1
    string_c += "1"
    for _model in repeated_model_d:
        _model.increment_one()
    for k, v in map_model_e.items():
        map_model_e[k] = v + 1
    return {
        "int_a": int_a,
        "float_b": float_b,
        "string_c": string_c,
        "repeated_model_d": repeated_model_d,
        "map_model_e": map_model_e,
    }
