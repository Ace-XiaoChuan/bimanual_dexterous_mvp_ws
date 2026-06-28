# MVP-1 第五阶段：Fake 机械臂多目标扩展

## 1. 工作目标

扩展 `fake_arm_control_node`，让 MVP-0 中只支持 `home` 的 MoveArm action
扩展为 Pick-and-Place 所需的多个命名目标。

本阶段仍然不做真实规划，只验证目标名、反馈、结果和错误码。

## 2. 本阶段范围

涉及软件包：

```text
fake_arm_control
assembly_interfaces
assembly_tests
```

沿用接口：

```text
/assembly/move_arm
assembly_interfaces/action/MoveArm
```

## 3. 支持目标

MVP-1 支持：

```text
home
pregrasp
grasp
lift
preplace
place
retreat
```

继续只支持：

```text
arm_name = "right_arm"
```

## 4. Fake 执行语义

每个合法目标都可以采用相同的 fake 执行模型：

```text
goal accepted
feedback: accepted, progress 0.0
feedback: moving, progress 0.5
feedback: succeeded, progress 1.0
result: success = true
```

内部状态建议：

```text
current_arm
current_target
is_moving
last_goal_success
last_error_code
last_message
```

## 5. 错误处理

沿用 MVP-0 错误码：

```text
2001  不支持的 arm_name
2002  不支持的 target_name
2003  timeout_sec 必须为正数
```

## 6. 日志要求

每个 goal 至少记录：

```text
event=move_arm_goal_received
arm_name
target_name
timeout_sec
```

每个 result 至少记录：

```text
event=move_arm_result
arm_name
target_name
success
error_code
message
```

## 7. 验收标准

```text
colcon build 通过
home 目标仍然成功
pregrasp / grasp / lift / preplace / place / retreat 均成功
不支持的 target_name 返回 2002
timeout_sec 非法返回 2003
feedback 进度可观测
```

## 8. 与后续阶段关系

MVP-2 可以把这些命名目标映射到 MoveIt named target、pose target 或 MTC
stage。MVP-1 只要求上层任务状态机和目标名稳定。
