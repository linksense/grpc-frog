# -*- coding: utf-8 -*-
import os
import shutil

hello_c_path = os.path.join(os.path.dirname(__file__), "hello_c")


def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    os.makedirs(hello_c_path, exist_ok=True)


def teardown_module(module):
    """ setup any state specific to the execution of the given module."""
    # 还原hello_c文件夹
    from grpc_frog import frog
    shutil.rmtree(hello_c_path)
    file_list = ["grpc_test.proto", "grpc_test_pb2.py", "grpc_test_pb2_grpc.py"]
    dir_list = [frog.servicer_map['grpc_test'].proto_dir, "."]
    for dir_path in dir_list:
        for file in file_list:
            file_path = os.path.join(dir_path, file)
            print(file_path)
            if os.path.exists(file_path):
                print(os.remove(file_path))

