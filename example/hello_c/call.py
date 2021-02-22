#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/29 15:17
# Copyright 2021 LinkSense Technology CO,. Ltd

from example.hello_c.servicer_grpc_test import echo_with_increment_one

print("call")
res = echo_with_increment_one(int_a=0, float_b=0.0, string_c="", repeated_model_d=[], map_model_e=dict(a=0))
print(res)
