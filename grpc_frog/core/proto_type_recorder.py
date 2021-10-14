#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/19 18:02
# Copyright 2021 LinkSense Technology CO,. Ltd
"""
记录proto类型与python类型对应关系
"""
import datetime
from collections import defaultdict
from typing import Type, Union

import flask_sqlalchemy
from google.protobuf.message import Message
from pydantic import BaseModel

# CMessage的基本类型

proto_base_type = {
    int: "int64",
    str: "string",
    bool: "bool",
    float: "float",
    datetime.datetime: "google.protobuf.Timestamp",
}

# python类型对应proto文件中名字
_py_name_2_proto_name_map = proto_base_type.copy()  # py_type : str
# 将一个python类型的属性转换成一个字典
message_collections = defaultdict(
    dict
)  # {a:int,b:str,c:list[str],d:{str,int},f:class_a}}

# 将自CMessage的数据转换成python对象
_converter = {
    int: int,
    str: str,
    bool: bool,
    float: float,
    datetime.datetime: lambda x: datetime.datetime.fromtimestamp(x.seconds),
}

_py_default_value = {
    "datetime.datetime": "datetime.datetime.now",
}


def default_converter_reverse(message, name, value):
    """默认 CMessage属性设置方式"""
    setattr(message, name, value)


# 将python数据转换成CMessage
converter_reverse = {
    int: default_converter_reverse,
    str: default_converter_reverse,
    bool: default_converter_reverse,
    float: default_converter_reverse,
    datetime.datetime: lambda message, name, value: getattr(message, name).FromDatetime(
        value
    ),
}


def _converter_py_type(py_type, value):
    """ 将自CMessage的数据转换成python对象  """
    if issubclass(py_type, (BaseModel, flask_sqlalchemy.model.Model)):
        obj = py_type()
        # obj 的属性结构
        struct = message_collections[py_type]
        for attr_name, attr_type in struct.items():
            # CMessage 对象 attr 的值
            message_value = getattr(value, attr_name)

            if isinstance(attr_type, list):
                # eg. attr_type == [float]
                if getattr(obj, attr_name) is None:
                    setattr(obj, attr_name, list())
                for _v in message_value:
                    getattr(obj, attr_name).append(_converter_py_type(attr_type[0], _v))
            elif isinstance(attr_type, dict):
                # eg. attr_type = {str, str} _k_type = str, _v_type =str
                if getattr(obj, attr_name) is None:
                    setattr(obj, attr_name, dict())
                (_k_type, _v_type), *_ = list(attr_type.items())
                for _k, _v in message_value.items():
                    key_obj = _converter_py_type(_k_type, _k)
                    value_obj = _converter_py_type(_v_type, _v)
                    getattr(obj, attr_name)[key_obj] = value_obj
            else:
                # eg. attr_type = str
                setattr(obj, attr_name, _converter_py_type(attr_type, message_value))
        return obj

    return _converter[py_type](value)


def converter_proto(py_type, message, name, value):
    """将CMessage对象转换成python对象

    :param py_type: python type
    :param message: CMessage
    :param name: field name
    :param value: field python value
    :return: grpc CMessage
    """
    converter_reverse[py_type](message, name, value)
    return message


def translate_2_proto_field(type_field: Type):
    """将py_type参数转换成proto字符串"""
    if isinstance(type_field, list):
        return "repeated {}".format(translate_2_proto_field(type_field[0]))
    elif isinstance(type_field, dict):
        (k, v), *_ = list(type_field.items())
        return "map<{}, {}>".format(
            translate_2_proto_field(k), translate_2_proto_field(v)
        )
    else:
        return _py_name_2_proto_name_map[type_field]


def translate_2_proto_message(py_type: str):
    """通过message_name获取这个message proto的形式"""
    body = ""
    for index, (name, _type_field) in enumerate(message_collections[py_type].items()):
        _proto_str = translate_2_proto_field(_type_field)
        body += "\n  {} {} = {};".format(_proto_str, name, index + 1)

    ret_str = """message {name} {{ {body}\n}}"""
    ret = ret_str.format(name=_py_name_2_proto_name_map[py_type], body=body)
    return ret


def register_py_type(
    model, message_name=None, to_dict_method="dict", from_orm_method="from_orm"
):
    """将一个model注册到frog中
    将sqlalchemy model转换成proto文件并
    需要实现 model与dict 之间的抓换 dict/from_obj
    proto_name: 在proto里的名字默认为类名
    """
    if not hasattr(model, to_dict_method):
        raise NotImplementedError("请实现{}方法，将model返回为dict".format(to_dict_method))
    if not hasattr(model, from_orm_method):
        raise NotImplementedError("请实现{}方法，将dict转换为model".format(from_orm_method))
    # lk特制
    old_model = None
    if (
        hasattr(model, "__abstract__")
        and model.__abstract__
        and hasattr(model, "switch_table")
    ):
        old_model = model
        model = model.switch_table(None)

    message_name = message_name or model.__name__
    _py_name_2_proto_name_map[model] = message_name

    message_collections[model] = annotations_to_dict(model.__annotations__)
    _converter[model] = getattr(model, from_orm_method)

    if old_model:
        _converter[old_model] = getattr(model, from_orm_method)
        _py_name_2_proto_name_map[old_model] = message_name
        message_collections[old_model] = annotations_to_dict(model.__annotations__)


def get_base_type(type_list):
    """去除typing的List Dict"""
    ret_type_list = set()
    for py_type in type_list:
        if py_type in list(proto_base_type.keys()):
            ret_type_list.add(py_type)
            continue
        elif isinstance(py_type, list):
            ret_type_list.update(get_base_type(py_type))
            continue
        elif isinstance(py_type, dict):
            ret_type_list.update(get_base_type(py_type.values()))
            continue
        elif str(py_type).startswith("typing.List[") or str(py_type).startswith(
            "typing.Dict["
        ):
            ret_type_list.update(get_base_type(py_type.__args__))
            continue

        ret_type_list.update(get_base_type(py_type.__annotations__.values()))
        # for sqlalchemy model
        _struct = message_collections[py_type]
        ret_type_list.update(get_base_type(_struct.values()))
        ret_type_list.add(py_type)
    return ret_type_list


def register_by_dict(struct, proto_name):
    """将一个dict数据加入frog"""

    class base_model:
        def __init__(self, data: dict):
            self.__dict__.update(data)

        def dict(self):
            return self.__dict__

        @classmethod
        def from_orm(cls, data):
            return cls(data)

    new_model = type(proto_name, (base_model,), {"__annotations__": struct})
    register_py_type(new_model)
    return new_model


def annotations_to_dict(annotations):
    """将typing里的Dict和List转换成python类型"""
    # 因为不好描述这个类型 所以简单直接拿list or dict装了
    # typing 转换后 实际上是对 类型是否可迭代(list[int])
    # 键值类型(Dict[str,str])的一种描述
    # 也可以用 (List,int) (Dict,(str,str)) 这种方式表达 不过判断也很麻烦
    annotations = annotations.copy()
    for k, v in annotations.items():
        if not isinstance(k, str):
            raise TypeError("annotations 的 key 必须为str")
        if str(v).startswith("typing.List["):
            annotations[k] = list(v.__args__)
        elif str(v).startswith("typing.Dict["):
            annotations[k] = dict((v.__args__,))
    return annotations


def message_to_dict(message_obj, struct_dict: dict):
    """ 将CMessages对象换成dict """
    return_dict = dict()
    for name, py_type in struct_dict.items():
        value = getattr(message_obj, name)
        if isinstance(py_type, dict):
            (key_type, value_type), *_ = py_type.items()
            return_dict[name] = {}
            for key, value in value.items():
                _key = _converter_py_type(key_type, key)
                _value = _converter_py_type(value_type, value)
                return_dict[name][_key] = value

        elif isinstance(py_type, list):
            return_dict[name] = []
            for _value in value:
                # todo: pydantic.model .from_orm 不支持直接转换 to_list 考虑框架做这件事情？
                model_obj = _converter_py_type(py_type[0], _value)
                return_dict[name].append(model_obj)

        else:
            return_dict[name] = _converter_py_type(py_type, value)

    return return_dict


def dict_to_message(
    return_dict: Union[dict, BaseModel], message: Message, model, servicer
):
    """ py_type转换成CMessage """
    if not isinstance(return_dict, dict) and not hasattr(return_dict, "dict"):
        raise TypeError("{}对象实现错误 没有dict方法，请检查输入".format(type(return_dict)))
    if not isinstance(return_dict, dict):
        return_dict = return_dict.dict()
    struct_dict = message_collections[model]
    for name, py_type in struct_dict.items():
        value = return_dict.get(name)
        struct = struct_dict[name]
        if value is None or name not in struct_dict:
            continue
        if isinstance(struct, dict):
            # 可能没考虑到太复杂的情况
            # struct e.g: {str:str}
            _set_message_value__dict(message, name, servicer, struct, value)
        elif isinstance(struct, list):
            # struct e.g: [str]
            _set_message_value__list(message, name, servicer, struct, value)
        else:
            _set_message_value___obj(message, name, servicer, struct, value)

    return message


def _set_message_value___obj(message, name, servicer, struct, value):
    if struct in message_collections.keys():
        if getattr(value, "dict", None):
            value = value.dict()
        dict_to_message(value, getattr(message, name), struct, servicer)
    else:
        converter_proto(struct, message, name, value)


def _set_message_value__list(message, name, servicer, struct, value):
    if struct[0] in message_collections:
        # 生成CMessage填入
        _message_model = servicer.get_pb2_message(_py_name_2_proto_name_map[struct[0]])
        for _value in value:
            _message = dict_to_message(_value, _message_model(), struct[0], servicer)
            getattr(message, name).append(_message)
    else:
        # 基础类型 直接填入
        for _value in value:
            getattr(message, name).append(_value)


def _set_message_value__dict(message, name, servicer, struct, value):
    (key_type, value_type), *_ = struct.items()
    for key, value in value.items():
        # 如果是proto的基础类型 直接填值
        # 如果是frog中有的model 生成CMessage填入
        if key_type in message_collections.keys():
            _key_model = servicer.get_pb2_message(_py_name_2_proto_name_map[key])
            key = dict_to_message(key, _key_model(), key_type, servicer)
        if value_type in message_collections.keys():
            _value_model = servicer.get_pb2_message(_py_name_2_proto_name_map[value])
            value = dict_to_message(value, _value_model, value_type, servicer)
        getattr(message, name)[key] = value


def get_py_default_value(py_text: str):
    """获取py_obj的默认值"""
    if py_text not in _py_default_value:
        return py_text
    else:
        return _py_default_value[py_text]
