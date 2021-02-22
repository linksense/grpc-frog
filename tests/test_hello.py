#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/27 11:43
# Copyright 2021 LinkSense Technology CO,. Ltd
import multiprocessing
import os
import socket
import time
from typing import Dict, Union

from grpc_frog import Servicer, frog, generate_proto_file, generate_py_code
from tests.hello_d.interface import ResponseModel, echo_with_increment_one


def _is_port_used(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, port))
    except OSError:
        return False
    finally:
        s.close()
    return True

def run_grpc_server_daemon():
    from concurrent import futures
    import grpc
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2), )
    frog.bind_servicer(server)
    server.add_insecure_port('{}:{}'.format("127.0.0.1", 50055))
    server.start()
    server.wait_for_termination()


class TestHello:
    server_daemon = None
    server_name = "test_hello"
    default_proto_path = Servicer.proto_dir

    @classmethod
    def setup_class(cls):
        # flake8: noqa
        # noinspection PyUnresolvedReferences
        from tests.hello_d.interface import TDemoModel, echo_with_increment_one
        generate_proto_file()

        if _is_port_used("127.0.0.1", 50055):
            raise ValueError("当前端(127.0.0.1, 50055)口被占用，不能启动测试服务")
        cls.server_daemon = multiprocessing.Process(target=run_grpc_server_daemon, args=())
        cls.server_daemon.start()
        time.sleep(2)

        # 生成Client
        path = os.path.join(os.path.dirname(__file__), "hello_c")
        generate_py_code(path)

    @classmethod
    def teardown_class(cls):
        cls.server_daemon.terminate()
        os.remove(os.path.join(frog.servicer_map['grpc_test'].proto_dir, "grpc_test.proto"))
        os.remove(os.path.join(frog.servicer_map['grpc_test'].proto_dir, "grpc_test_pb2.py"))
        os.remove(os.path.join(frog.servicer_map['grpc_test'].proto_dir, "grpc_test_pb2_grpc.py"))
        frog.set_proto_dir(cls.default_proto_path)

    def setup_method(self):
        print("setup_method")

    def teardown_method(self):
        print("teardown_method")

    @staticmethod
    def _get_default_args():
        from tests.hello_d.interface import TDemoModel
        _model = TDemoModel(list_int_field=[0], map_int_field={"a": 0})
        kwargs = dict(int_a=0, float_b=0.0, string_c="", repeated_model_d=[_model], map_model_e=dict(a=0))
        return kwargs

    @staticmethod
    def _asset_response(response: Union[ResponseModel, Dict]):
        response_dict = response.dict() if isinstance(response, ResponseModel) else response
        assert response_dict['int_a'] == 1
        assert response_dict['float_b'] == 1.0
        assert response_dict['string_c'] == "1"
        assert response_dict['map_model_e']["a"] == 1
        _model = response_dict["repeated_model_d"][0]
        assert _model.int_field == 1
        assert _model.float_field == 1.0
        assert _model.str_field == "1"
        assert _model.list_int_field[0] == 1
        assert _model.map_int_field['a'] == 1

    def test_server_daemon(self):
        """测试生成proto"""
        pb2 = frog.servicer_map['grpc_test'].get_pb2()
        pb2_grpc = frog.servicer_map['grpc_test'].get_pb2_grpc()
        assert hasattr(pb2_grpc, "grpc_test")
        assert hasattr(pb2_grpc, "grpc_testStub")
        assert hasattr(pb2_grpc, "grpc_testServicer")
        assert hasattr(pb2, "TDemoModel")
        assert hasattr(pb2, "ResponseModel")
        assert hasattr(pb2, "echo_with_increment_one_request")
        args = self._get_default_args()
        # 测试直接调用函数echo_with_increment_one
        res = echo_with_increment_one(**args)
        self._asset_response(res)

    def test_generate_client_code(self):
        # 验证语法正确
        exec("from tests.hello_c.model_default import *")
        exec("from tests.hello_c.servicer_grpc_test import *")
        # Client init 后发送请求
        frog.client_init("grpc://127.0.0.1:50055/hello")
        from tests.hello_c.servicer_grpc_test import echo_with_increment_one
        args = self._get_default_args()
        # 测试直接调用函数echo_with_increment_one
        res = echo_with_increment_one(**args)
        # BaseModel.dict 会导致
        tmp = res.dict()
        tmp["repeated_model_d"][0] = res.repeated_model_d[0]
        self._asset_response(tmp)

    def test_zookeeper(self):
        from grpc_frog.zk_utils import register_zk
        register_zk("127.0.0.1", 50055, "hello", "192.168.0.68", 2181)

        frog.client_init("zookeeper://192.168.0.68:2181/hello")
        from tests.hello_c.servicer_grpc_test import echo_with_increment_one
        res = echo_with_increment_one()
        # BaseModel.dict 会导致
        tmp = res.dict()
        assert tmp is not None
