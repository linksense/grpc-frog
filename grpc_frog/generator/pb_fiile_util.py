#!/usr/bin/python3
# encoding: utf-8
# @Time    : 2021/10/13 18:34
# @author  : zza
# @Email   : 740713651@qq.com
# @File    : pb_fiile_util.py
import os
from distutils.dir_util import copy_tree, remove_tree

from grpc_tools import protoc

from grpc_frog.proto import google_dir


def generate_pb2_file(proto_file: str) -> None:
    """生成pb2文件"""
    # copy google dir
    proto_dir = os.path.dirname(proto_file)
    args = (
        "grpc_tools.protoc",
        "-I" + proto_dir,
        "--python_out=" + proto_dir,
        "--grpc_python_out=" + proto_dir,
        proto_file,
    )
    copy_tree(os.path.join(google_dir, "google"), os.path.join(proto_dir, "google"))
    protoc_result = protoc.main(args)
    remove_tree(os.path.join(proto_dir, "google"))
    if protoc_result == 1:
        message = "编译{}下的文件时产生了一个错误args:\n" "python -m grpc.tools.protoc " + " ".join(
            args
        )
        raise SyntaxError(message)

    init_file = os.path.join(os.path.dirname(proto_dir), "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as fp:
            pass
