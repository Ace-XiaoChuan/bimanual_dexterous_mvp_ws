# MVP-1 接口快照

本文件记录 MVP-1 冻结时对外可依赖的 ROS 接口、任务名、状态序列和
fake 语义。它是验收快照，不替代源码中的 `.srv`、`.action`、`.msg`
定义。

## StartTask

Service：

```text
/assembly/start_task
assembly_interfaces/srv/StartTask
```

支持的 `task_name`：

```text
mvp0_home
pick_and_place_mvp
```

MVP-1 合法请求：

```text
task_name: "pick_and_place_mvp"
```

主要响应语义：

```text
accepted = true   表示任务请求已被接受，后台任务线程开始执行
accepted = false  表示请求被拒绝，不会启动任务
error_code = 0    表示请求接受成功
3001              task_name 为空
3002              task_name 不受支持
3003              当前已有任务运行，拒绝并发任务
```

## TaskState

Topic：

```text
/assembly/task_state
assembly_interfaces/msg/TaskState
```

字段：

```text
string task_id
string current_state
string previous_state
float32 progress
int32 error_code
string message
```

MVP-1 成功状态序列：

```text
IDLE
-> RESETTING
-> ARM_HOME
-> HAND_OPEN
-> ARM_PREGRASP
-> HAND_PRESHAPE
-> ARM_GRASP
-> HAND_CLOSE
-> ATTACH_OBJECT
-> ARM_LIFT
-> ARM_PREPLACE
-> ARM_PLACE
-> TERMINAL_PLACE
-> DETACH_OBJECT
-> HAND_OPEN
-> ARM_RETREAT
-> ARM_HOME
-> SUCCESS
```

失败语义：

```text
任一底层 fake service 或 action 调用失败时，assembly_task 发布 FAILED。
FAILED 的 error_code 和 message 来自失败调用或任务编排节点的超时/不可用判断。
```

## MoveArm

Action：

```text
/assembly/move_arm
assembly_interfaces/action/MoveArm
```

MVP-1 使用的逻辑机械臂：

```text
right_arm
```

MVP-1 使用的命名目标：

```text
home
pregrasp
grasp
lift
preplace
place
retreat
```

这些目标在 MVP-1 中是 fake 命名目标，不代表真实关节角、真实轨迹或
MoveIt 规划结果。

## ControlHand

Service：

```text
/assembly/control_hand
assembly_interfaces/srv/ControlHand
```

MVP-1 使用的逻辑手部：

```text
right_hand
```

支持的高层命令：

```text
open
preshape
close
hold
release
```

MVP-1 状态机实际使用：

```text
open
preshape
close
open
```

`right_hand` 在本阶段按夹爪化或预设抓型执行器处理，不控制
RH56DFX-2R 的真实全关节。

## Scene Object

Services：

```text
/assembly/reset_scene
/assembly/attach_object
/assembly/detach_object
/assembly/get_object_pose
```

MVP-1 物体和位置：

```text
object_id: mvp_object
source_location: pickup_zone
target_location: place_zone
attached location: attached
attached link: right_hand
```

状态语义：

```text
reset_scene       将 mvp_object 放回 pickup_zone，object_attached = false
attach_object     将 mvp_object 逻辑附着到 right_hand
detach_object     将 mvp_object 释放到 place_zone
get_object_pose   返回 object_location、object_attached 和 attached_link
```

## Terminal Operation

Service：

```text
/assembly/execute_terminal_operation
assembly_interfaces/srv/ExecuteTerminalOperation
```

MVP-1 支持并使用：

```text
operation_type: PLACE
object_id: mvp_object
target_location: place_zone
```

`PLACE` 是 Pick-and-Place 的末端操作占位，不代表航空插头插接、拧紧或真实装配。

## Launch

MVP-1 一键启动文件：

```text
assembly_bringup/launch/mvp1_fake_pick_place.launch.py
```

启动节点：

```text
fake_scene_manager_node
fake_arm_control_node
fake_hand_control_node
fake_terminal_operation_node
assembly_task_node
```

## 配置文件

MVP-1 任务配置：

```text
assembly_task/config/mvp1_pick_and_place.yaml
```

该配置冻结了任务名、逻辑 arm/hand/object、fake arm targets、hand commands、
抓型名和各类超时时间。

## 错误码摘要

任务编排层：

```text
3001  task_name must not be empty
3002  unsupported task_name
3003  another task is already running
3101  reset_scene service unavailable / timeout / no response
3201  move_arm action unavailable / timeout / rejected / no result
7001  control_hand service unavailable / timeout / no response
7002  scene object service unavailable / timeout / no response
7003  terminal operation service unavailable / timeout / no response
```

场景管理层：

```text
1001  task_id must not be empty
5001  object_id must not be empty
5002  object does not exist
5003  object is already attached
5004  object is not attached
```
