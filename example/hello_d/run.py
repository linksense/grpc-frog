#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/1/29 15:12
# Copyright 2021 LinkSense Technology CO,. Ltd
from concurrent import futures

import grpc
from example.hello_d import interface

from grpc_frog import frog


def run():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2), )
    print("bind interface {}".format(interface))
    frog.bind_servicer(server)
    server.add_insecure_port('{}:{}'.format("127.0.0.1", 50065))

    print("127.0.0.1", 50065, "server.start()")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    run()
