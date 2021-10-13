#!/usr/bin/env python
# encoding: utf-8
# Created by zza on 2021/2/4 10:41
# Copyright 2021 LinkSense Technology CO,. Ltd

import json
import random
import time

from kazoo.client import KazooClient


def register_zk(server_host, server_port, server_name, zk_host, zk_port):
    """
    服务端注册到zookeeper
    """
    zk = KazooClient(hosts="{host}:{port}".format(host=zk_host, port=zk_port))
    zk.start()
    zk.ensure_path("/{}".format(server_name))  # 创建根节点
    value = json.dumps({"host": server_host, "port": server_port})
    # 创建服务子节点
    zk.create(
        "/{}/{}_".format(server_name, int(time.time())),
        value.encode(),
        ephemeral=True,
        sequence=True,
    )


class DistributedChannel(object):
    """分布式服务 - 获取服务连接方式的类"""

    def __init__(self, host, port, servicer_name):
        self.servicer_name = servicer_name
        self._zk = KazooClient(hosts="{host}:{port}".format(host=host, port=port))
        self._zk.start()
        self._get_servers()

    def _get_servers(self, event=None):
        """
        从zookeeper获取服务器地址信息列表
        """
        servers = self._zk.get_children(
            "/{}".format(self.servicer_name), watch=self._get_servers
        )
        self._servers = []
        for server in servers:
            data = self._zk.get("/{}/{}".format(self.servicer_name, server))[0]
            if data:
                addr = json.loads(data.decode())
                self._servers.append(addr)

    def get_server(self):
        """
        随机选出一个可用的服务器
        """
        return random.choice(self._servers)
