# MVP-0 Interface Snapshot

生成时间：2026-06-24 13:32:37 CST

最后更新：2026-06-24 14:59:29 HKT

基准 commit：`fcd7a22`

## Launch

一键启动入口：

```bash
ros2 launch assembly_bringup mvp0_fake_system.launch.py
```

启动节点：

| 节点 | Package | Executable |
| --- | --- | --- |
| `fake_scene_manager_node` | `fake_scene_manager` | `fake_scene_manager_node` |
| `fake_arm_control_node` | `fake_arm_control` | `fake_arm_control_node` |
| `assembly_task_node` | `assembly_task` | `assembly_task_node` |

## Public ROS Interfaces

| 接口 | 类型 | 提供方 | 使用方 |
| --- | --- | --- | --- |
| `/assembly/start_task` | Service `StartTask` | `assembly_task_node` | 外部调用者、集成测试 |
| `/assembly/reset_scene` | Service `ResetScene` | `fake_scene_manager_node` | `assembly_task_node` |
| `/assembly/move_arm` | Action `MoveArm` | `fake_arm_control_node` | `assembly_task_node` |
| `/assembly/task_state` | Topic `TaskState` | `assembly_task_node` | 外部观察者、集成测试 |

## Supported MVP-0 Task

| 字段 | 值 |
| --- | --- |
| `task_name` | `mvp0_home` |
| `arm_name` | `right_arm` |
| `target_name` | `home` |
| `timeout_sec` | `5.0` |
| 机械臂硬件映射 | Franka Research 3 |
| 灵巧手硬件映射 | 因时 RH56DFX-2R，仅做命名预留 |

## StartTask Service

文件：`src/assembly_interfaces/srv/StartTask.srv`

```text
string task_name
---
bool accepted
string task_id
int32 error_code
string message
```

响应约定：

| 请求 | accepted | task_id | error_code | message |
| --- | --- | --- | --- | --- |
| `mvp0_home` | `true` | 非空，如 `mvp0_task_0001` | `0` | `Task accepted` |
| 空字符串 | `false` | 空字符串 | `3001` | `task_name must not be empty` |
| 其他任务名 | `false` | 空字符串 | `3002` | `unsupported task_name` |

## ResetScene Service

文件：`src/assembly_interfaces/srv/ResetScene.srv`

```text
string task_id
---
bool success
int32 error_code
string message
```

响应约定：

| 请求 | success | error_code | message |
| --- | --- | --- | --- |
| 非空 `task_id` | `true` | `0` | `Scene reset successfully` |
| 空 `task_id` | `false` | `1001` | `task_id must not be empty` |

## MoveArm Action

文件：`src/assembly_interfaces/action/MoveArm.action`

```text
string arm_name
string target_name
float32 timeout_sec
---
bool success
int32 error_code
string message
---
string current_state
float32 progress
```

Goal 约定：

| 字段 | 合法值 |
| --- | --- |
| `arm_name` | `right_arm` |
| `target_name` | `home` |
| `timeout_sec` | 大于 `0.0` |

错误码：

| error_code | 含义 |
| --- | --- |
| `0` | 成功 |
| `2001` | 不支持的 `arm_name` |
| `2002` | 不支持的 `target_name` |
| `2003` | `timeout_sec` 非正数 |

## TaskState Topic

文件：`src/assembly_interfaces/msg/TaskState.msg`

```text
string task_id
string current_state
string previous_state
float32 progress
int32 error_code
string message
```

成功路径状态序列：

```text
IDLE -> RESETTING -> ARM_HOME -> SUCCESS
```

失败路径状态：

```text
RESETTING -> FAILED
ARM_HOME -> FAILED
```

MVP-0 集成测试验收的成功路径状态：

```text
RESETTING -> ARM_HOME -> SUCCESS
```

## Error Codes

| error_code | 来源 | 含义 |
| --- | --- | --- |
| `0` | 通用 | 无错误 |
| `1001` | ResetScene | `task_id` 不能为空 |
| `2001` | MoveArm | 不支持的 `arm_name` |
| `2002` | MoveArm | 不支持的 `target_name` |
| `2003` | MoveArm | `timeout_sec` 必须为正数 |
| `3001` | StartTask | `task_name` 不能为空 |
| `3002` | StartTask | 不支持的 `task_name` |
| `3101` | AssemblyTask | ResetScene 不可用或无响应 |
| `3201` | AssemblyTask | MoveArm 不可用、拒绝或无响应 |

## Test Coverage Snapshot

`assembly_tests` 当前覆盖：

- 合法 `mvp0_home` 请求。
- 空 `task_name` 请求。
- 不支持的 `task_name` 请求。
- `RESETTING -> ARM_HOME -> SUCCESS` 状态序列。
- 连续 10 次合法任务。
- `task_id` 唯一且递增。

未启动 ResetScene 或 MoveArm 时进入 `FAILED` 的专项失败注入测试已降级为后续
增强验收项，不作为阶段 6 完成阻塞条件。
