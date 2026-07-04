# MVP-1 第四阶段：Fake 末端操作节点

## 1. 工作目标

实现 `fake_terminal_operation_node`，为 MVP-1 提供 PLACE 末端操作占位能力。

这里的 terminal operation 表示“任务语义上的放置动作已经执行”，不等同于
真实接触、对孔或插入。

## 2. 本阶段范围

涉及软件包：

```text
fake_terminal_operation
assembly_interfaces
assembly_tests
```

推荐提供：

```text
/assembly/execute_terminal_operation
```

MVP-1 只支持：

```text
operation_type = "PLACE"
```

## 3. 推荐请求字段

```text
task_id
operation_type
object_id
target_location
timeout_sec
```

响应字段：

```text
success
error_code
message
```

## 4. 职责边界

`fake_terminal_operation` 负责表达高层末端操作语义：

```text
PLACE operation accepted
PLACE operation completed
```

`fake_scene_manager` 负责维护 object 状态：

```text
detach object
object_location = place_zone
```

两者不要混成一个模块。这样后续从 PLACE 过渡到 INSERT 时，只需要替换或扩展
terminal operation，而不必重写场景状态管理。

## 5. 错误处理

```text
不支持的 operation_type -> 6001
target_location 为空 -> 6002
timeout_sec <= 0 -> 6003
object_id 为空 -> 6004
```

## 6. 日志要求

请求日志：

```text
event=terminal_operation_request
task_id
operation_type
object_id
target_location
timeout_sec
```

响应日志：

```text
event=terminal_operation_response
success
error_code
message
```

## 7. 验收标准

```text
colcon build 通过
fake_terminal_operation_node 可启动
/assembly/execute_terminal_operation 可发现
PLACE 返回 success
不支持的 operation_type 返回错误码
object_id / target_location / timeout_sec 非法时返回明确错误码
日志可定位 task_id 和 operation_type
```

## 8. 非目标

本阶段不实现：

```text
INSERT
孔轴对准
接触检测
力反馈
柔顺控制
插入搜索
自动失败恢复
```
