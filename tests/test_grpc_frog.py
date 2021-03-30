#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_grpc_frog
----------------------------------

Tests for `grpc_frog` module.
"""

import os

import grpc_frog
from grpc_frog import frog, generate_proto_file


class TestGrpc_frog:

    @classmethod
    def teardown_class(cls):
        pass

    def test_something(self):
        assert grpc_frog.__version__

    def test_generate_proto(self):
        # flake8: noqa
        # noinspection PyUnresolvedReferences
        from tests.hello_d.interface import TDemoModel, echo_with_increment_one
        generate_proto_file(save_dir=".")
        file_list = ["grpc_test.proto", "grpc_test_pb2.py", "grpc_test_pb2_grpc.py"]
        dir_list = [frog.servicer_map['grpc_test'].proto_dir]
        for dir_path in dir_list:
            for file in file_list:
                file_path = os.path.join(dir_path, file)
                print("file_path", file_path)
                assert os.path.exists(file_path)

    def test_bind_server(self):
        from concurrent import futures
        import grpc

        from tests.hello_d.interface import test_servicer
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
        frog.bind_servicer(server, test_servicer)

        server.add_insecure_port('{}:{}'.format("127.0.0.1", 50055))
        server.start()
        server.stop(None)
