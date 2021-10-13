# -*- coding: utf-8 -*-
import os
import shutil

from grpc_frog import proto

hello_c_path = os.path.join(os.path.dirname(__file__), "hello_c")


def setup_module(module):
    """ setup any state specific to the execution of the given module."""
    os.makedirs(hello_c_path, exist_ok=True)
    from grpc_frog import generate_proto_file
    from tests.hello_d import interface
    from tests.hello_d.interface import TDemoModel, echo_with_increment_one, service_d

    generate_proto_file(
        servicer_name=service_d.name, save_dir=os.path.dirname(interface.__file__)
    )


def teardown_module(module):
    """ setup any state specific to the execution of the given module."""
    # 还原hello_c文件夹
    from grpc_frog import frog
    from tests.hello_d.interface import service_d

    shutil.rmtree(hello_c_path)
    file_list = [
        i.format(service_d.name) for i in ["{}.proto", "{}_pb2.py", "{}_pb2_grpc.py"]
    ]
    dir_list = [
        frog.servicer_map[service_d.name].proto_dir,
        ".",
        os.path.dirname(proto.__file__),
    ]
    for dir_path in dir_list:
        for file in file_list:
            file_path = os.path.join(dir_path, file)
            print(file_path)
            if os.path.exists(file_path):
                print(os.remove(file_path))
