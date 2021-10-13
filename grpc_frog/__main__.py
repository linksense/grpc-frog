#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/13 15:31
# Copyright 2021 LinkSense Technology CO,. Ltd
import os

import fire


def generate_proto_file(servicer_name=None):
    """生成proto文件
    建议不要用命令行生成，import 容易出现error
    """
    modules = []
    for root, _, filenames in os.walk(os.getcwd()):
        for filename in filenames:
            if filename.startswith(".") or not filename.endswith(".py"):
                continue
            path = os.path.join(root, filename)
            modules.append(path)
    for py_file in sorted(modules):
        try:
            exec(open(py_file, "r", encoding="utf8").read())
        except Exception as err:
            print("import err on {}\nerr:{}".format(py_file, err))

    from grpc_frog import generate_proto_file as _generate_proto_file

    _generate_proto_file(servicer_name)


def clear_proto_cache():
    """ 生成proto文件 """
    from grpc_frog import frog

    frog.clear_proto_cache()


def generate_client_code(package_dir, pb_file_dir=None):
    """生成client包文件
    :param package_dir: client文件生成地址
    :param pb_file_dir: pb file文件所在目录
    """
    from grpc_frog import generate_py_code

    generate_py_code(package_dir, pb_file_dir)


def cli_run():
    """
    默认函数 触发fire包
    https://github.com/google/python-fire
    """
    fire.Fire()


if __name__ == "__main__":
    cli_run()
