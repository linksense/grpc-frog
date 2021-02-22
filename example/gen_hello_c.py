#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/2/4 15:35
# Copyright 2021 LinkSense Technology CO,. Ltd
import example.hello_d.interface
from grpc_frog import generate_proto_file,generate_py_code
# 需要先加载一遍 hello_d 的代码 使得 hello_d 被注册
frog = example.hello_d.interface.frog
generate_proto_file()
generate_py_code("hello_c")
