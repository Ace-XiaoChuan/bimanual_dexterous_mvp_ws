# MVP-1 第三阶段：Fake 手部控制器

## 1. 工作目标

实现 `fake_hand_control_node`，把真实因时 RH56DFX-2R 在 MVP-1 中降维为
夹爪化或预设抓型执行器。

本阶段只验证高层手部命令链路，不控制真实手指关节。

## 2. 本阶段范围

涉及软件包：

```text
fake_hand_control
assembly_interfaces
assembly_tests
```

推荐提供：

```text
/assembly/control_hand
```

接口建议见：

```text
doc/mvp1/tasks/01_MVP1_接口与配置冻结.md
```

## 3. 支持命令

MVP-1 支持：

```text
open
preshape
close
hold
release
```

推荐内部状态：

```text
current_hand = "right_hand"
current_command
current_grasp = "default"
is_closed: bool
is_holding: bool
last_error_code
last_message
```

## 4. 命令语义

```text
open:
  打开夹爪化手部，is_closed = false, is_holding = false

preshape:
  切换到预抓取形态，grasp_name 可先固定为 default

close:
  闭合夹爪化手部，is_closed = true

hold:
  进入保持状态，is_holding = true

release:
  释放保持状态，可等价于 open 或置 is_holding = false
```

## 5. 错误处理

```text
不支持的 hand_name -> 4001
不支持的 command -> 4002
timeout_sec <= 0 -> 4003
```

MVP-1 只支持：

```text
hand_name = "right_hand"
grasp_name = "default"
```

## 6. 日志要求

每次请求至少记录：

```text
event=control_hand_request
hand_name
command
grasp_name
timeout_sec
```

每次响应至少记录：

```text
event=control_hand_response
success
error_code
message
current_command
is_closed
is_holding
```

## 7. 验收标准

```text
colcon build 通过
fake_hand_control_node 可启动
/assembly/control_hand 可发现
open / preshape / close / hold / release 均返回 success
非法 hand_name / command / timeout 返回明确错误码
```

## 8. 与后续阶段关系

`assembly_task_node` 在任务编排阶段只调用高层 command，不关心真实手指关节。
未来 MVP-3 或 Post-MVP 可把该 fake 实现替换为真实 RH56DFX-2R 驱动适配层。
