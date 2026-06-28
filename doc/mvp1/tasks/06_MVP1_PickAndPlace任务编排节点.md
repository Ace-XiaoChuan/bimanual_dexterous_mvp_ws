# MVP-1 第六阶段：Pick-and-Place 任务编排节点

## 1. 工作目标

扩展 `assembly_task_node`，让它在保留 `mvp0_home` 的同时支持
`pick_and_place_mvp`，并按固定顺序调用 MVP-1 fake 模块。

本阶段是 MVP-1 的核心：把场景、机械臂、手部和末端操作串成完整任务链路。

## 2. 本阶段范围

涉及软件包：

```text
assembly_task
assembly_interfaces
fake_scene_manager
fake_arm_control
fake_hand_control
fake_terminal_operation
assembly_tests
```

`assembly_task_node` 需要新增 client：

```text
/assembly/control_hand
/assembly/attach_object
/assembly/detach_object
/assembly/get_object_pose
/assembly/execute_terminal_operation
```

继续使用：

```text
/assembly/start_task
/assembly/reset_scene
/assembly/move_arm
/assembly/task_state
```

## 3. 状态机

成功路径：

```text
RESETTING
ARM_HOME
HAND_OPEN
ARM_PREGRASP
HAND_PRESHAPE
ARM_GRASP
HAND_CLOSE
ATTACH_OBJECT
ARM_LIFT
ARM_PREPLACE
ARM_PLACE
TERMINAL_PLACE
DETACH_OBJECT
HAND_OPEN
ARM_RETREAT
ARM_HOME
SUCCESS
```

说明：

```text
TERMINAL_PLACE 表示调用 fake_terminal_operation 的 PLACE。
DETACH_OBJECT 表示更新 fake_scene_manager 中的 object 状态。
```

## 4. StartTask 行为

必须支持：

```text
task_name = "mvp0_home"
task_name = "pick_and_place_mvp"
```

非法任务仍然返回：

```text
accepted = false
task_id = ""
error_code = 3002
message = "unsupported task_name"
```

## 5. TaskState 要求

每个关键状态都发布：

```text
task_id
previous_state
current_state
progress
error_code
message
```

progress 建议单调递增。可以先按固定状态数量平均分配，不需要真实进度。

## 6. 失败处理

任一依赖失败时：

```text
current_state = "FAILED"
previous_state = 失败前状态
error_code = 下层错误码或 assembly_task 自身错误码
message = 可定位失败原因
```

assembly_task 自身错误码建议：

```text
7001  hand control 不可用或无响应
7002  scene object 操作不可用或无响应
7003  terminal operation 不可用或无响应
```

## 7. 并发模型

建议继续沿用 MVP-0 的后台线程模型：

```text
StartTask callback 只负责校验和受理
后台线程执行完整任务
ROS executor 保持可调度
```

MVP-1 暂不支持多任务并发。可以选择：

```text
方案 A：允许排队但一次只执行一个
方案 B：任务执行中拒绝新任务，返回明确错误码
```

如果要新增 busy 错误码，应在接口快照中记录。

## 8. 验收标准

```text
StartTask(pick_and_place_mvp) 被接受
最终进入 SUCCESS
完整状态序列按顺序出现
物体 attach / detach 被调用且状态正确
mvp0_home 仍然通过
非法 task_name 行为不回退
任一关键 fake 调用失败时进入 FAILED
```

## 9. 非目标

本阶段不实现任务取消、暂停、恢复、多任务并发和自动失败恢复。所有目标位置
和动作结果都仍然是 fake。
