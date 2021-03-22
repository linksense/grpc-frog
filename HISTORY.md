.. :changelog:

History
-------

# 1.0.0 更新

* 去掉默认的servicer 用户需要自己声明 servicer并绑定到frog里
* frog.bind_servicer 需要用户传入自己声明的servicer和grpc.server两个对象
* frog对多proto_dir由servicer管理

