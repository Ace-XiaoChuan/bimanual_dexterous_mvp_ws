# MVP-2 第一阶段：FR3 MoveIt 接口与配置冻结

## 1. 工作目标

冻结 MVP-2 的配置字段、逻辑命名、MoveIt 接入边界和错误处理范围，避免
MoveIt 相关参数散落在任务节点代码中。

## 2. 推荐配置文件

```text
src/assembly_task/config/mvp2_moveit_pick_and_place.yaml
```

推荐字段：

```text
task_name: pick_and_place_mvp
arm_name: right_arm
planning_group: fr3_arm
object_id: mvp_object
source_location: pickup_zone
target_location: place_zone
terminal_operation: PLACE
planning_timeout_sec
execution_timeout_sec
scene_operation_sec
```

MoveIt 命名目标：

```text
home
pregrasp
grasp
lift
preplace
place
retreat
```

## 3. 接口边界

上层继续使用：

```text
MoveArm.action
ControlHand.srv
AttachObject.srv
DetachObject.srv
ExecuteTerminalOperation.srv
TaskState.msg
```

`assembly_task` 不应直接调用 `move_group`、`libfranka` 或厂商 API。

## 4. 验收标准

```text
配置文件存在并能被后续节点读取
MoveIt 参数不写死在 assembly_task_node 中
right_arm 仍映射到 FR3 逻辑机械臂
pick_and_place_mvp 任务名保持兼容
MVP-1 配置和接口不被破坏
```

## 5. 非目标

```text
不实现 MoveIt 规划
不启动 RViz
不接真实 FR3
不实现完整 Pick-and-Place
```
