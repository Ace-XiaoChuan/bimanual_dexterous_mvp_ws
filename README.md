# Bimanual Dexterous Assembly MVP

双臂灵巧手协同装配 MVP 工作空间。项目当前以 Pick-and-Place 作为
Peg-in-Hole 的占位任务，先验证 ROS 2 通信、任务编排、场景重置、机械臂
Action、状态发布和错误处理等基础链路，再逐步加入真实仿真、灵巧手控制、
双臂协同和精密插入能力。

> 当前阶段：MVP-0，纯软件接口联调。所有真实机器人、MoveIt、MuJoCo 和
> 灵巧手控制逻辑尚未接入，现阶段通过 fake 节点跑通最小任务流程。

## 项目目标

本项目的近期目标不是直接完成高精度装配，而是搭建一个可以反复运行、
可重置、可记录、可替换模块的双臂灵巧手任务骨架。

MVP 阶段希望优先验证：

- ROS 2 package、service、action 和 topic 的基础接口可编译、可运行。
- 任务层能够按固定顺序调用场景、机械臂、灵巧手和末端操作模块。
- 左右机械臂、灵巧手、控制器和命名空间后续可以独立扩展。
- Pick-and-Place 可以作为 Peg-in-Hole 的末端操作占位符。
- 失败时能够返回错误码、日志和任务状态，而不是静默失败。

Pick-and-Place 只能验证系统骨架，不能替代真正的精密装配能力。接触建模、
柔顺控制、力反馈、孔轴对准、插入搜索、卡阻检测和失败恢复会在后续阶段
逐步加入。

## 当前能力

MVP-0 当前实现了一条最小任务链路：

```text
StartTask service
  -> assembly_task_node
  -> ResetScene service
  -> MoveArm action
  -> TaskState topic
```

任务状态机当前为：

```text
IDLE -> RESETTING -> ARM_HOME -> SUCCESS
                     \-> FAILED
```

当前支持的任务名和目标：

- `task_name`: `mvp0_home`
- `arm_name`: `right_arm`
- `target_name`: `home`

## 仓库结构

```text
.
├── doc/mvp0/tasks/              # MVP-0 任务说明和阶段文档
├── src/
│   ├── assembly_interfaces/     # 自定义 msg/srv/action 接口
│   ├── assembly_task/           # 最小任务编排节点
│   ├── fake_scene_manager/      # Fake 场景管理服务
│   ├── fake_arm_control/        # Fake 机械臂 Action Server
│   ├── fake_hand_control/       # 灵巧手控制占位包
│   ├── fake_terminal_operation/ # 末端操作占位包
│   ├── assembly_bringup/        # 启动编排占位包
│   └── assembly_tests/          # 集成测试占位包
└── README.md
```

## 软件包说明

| Package | 说明 | 当前状态 |
| --- | --- | --- |
| `assembly_interfaces` | 定义任务服务、状态消息和机械臂 Action | 已实现 |
| `assembly_task` | 维护最小任务流程，调用场景和机械臂接口 | 已实现 MVP-0 |
| `fake_scene_manager` | 提供 `/assembly/reset_scene` 服务 | 已实现 MVP-0 |
| `fake_arm_control` | 提供 `/assembly/move_arm` Action | 已实现 MVP-0 |
| `fake_hand_control` | 后续封装 `open/preshape/close/hold/release` | 占位 |
| `fake_terminal_operation` | 后续封装 `PLACE/INSERT` 末端任务 | 占位 |
| `assembly_bringup` | 后续集中管理 launch 文件 | 占位 |
| `assembly_tests` | 后续放置集成测试 | 占位 |

## 环境要求

- Ubuntu 22.04
- ROS 2 Humble
- Python 3.10
- `colcon`

进入工作空间后，先加载 ROS 环境：

```bash
source /opt/ros/humble/setup.bash
```

## 构建

```bash
cd /home/ace/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 运行 MVP-0

分别打开三个终端，并在每个终端中加载环境：

```bash
cd /home/ace/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
```

终端 1：启动 Fake 场景管理器。

```bash
ros2 run fake_scene_manager fake_scene_manager_node
```

终端 2：启动 Fake 机械臂控制器。

```bash
ros2 run fake_arm_control fake_arm_control_node
```

终端 3：启动任务编排节点。

```bash
ros2 run assembly_task assembly_task_node
```

另开一个终端发送任务请求：

```bash
ros2 service call /assembly/start_task assembly_interfaces/srv/StartTask "{task_name: 'mvp0_home'}"
```

可选：监听任务状态。

```bash
ros2 topic echo /assembly/task_state
```

成功时可以看到任务状态从 `RESETTING` 进入 `ARM_HOME`，最终进入 `SUCCESS`。

## ROS 接口

### Service

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/assembly/start_task` | `assembly_interfaces/srv/StartTask` | 请求启动一个任务 |
| `/assembly/reset_scene` | `assembly_interfaces/srv/ResetScene` | 重置 fake 场景 |

### Action

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/assembly/move_arm` | `assembly_interfaces/action/MoveArm` | 请求机械臂移动到命名目标 |

### Topic

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| `/assembly/task_state` | `assembly_interfaces/msg/TaskState` | 发布任务状态、进度和错误码 |

## 设计原则

- 上层任务接口保持通用，不把系统核心写死为单一 `place` 流程。
- 抓取、运输和末端操作分阶段设计，便于后续把 `PLACE` 替换为 `INSERT`。
- 灵巧手在早期被降维为预设抓型执行器，任务层只发送高层命令。
- 场景中的物体抓取可先使用逻辑附着，后续再替换为真实物理接触。
- 关键动作必须有超时、错误码和结构化日志。

建议的长期任务分层：

```text
acquire object -> transport object -> terminal operation
```

其中 `terminal operation` 当前为 Pick-and-Place，后续升级为 Peg-in-Hole。

## MVP 路线图

| 阶段 | 目标 |
| --- | --- |
| MVP-0 | 纯软件接口联调，使用 fake 节点跑通完整任务链路 |
| MVP-1 | RViz 单臂 Pick-and-Place，接入固定目标点和逻辑附着 |
| MVP-2 | MuJoCo 单臂 Pick-and-Place，验证关节控制和场景重置 |
| MVP-3 | 双臂双手 Pick-and-Place，验证左右命名空间和简单同步 |
| MVP-4 | 预插入占位任务，验证装配坐标系和接近方向 |
| MVP-5 | 简单 Peg-in-Hole，加入大间隙、低速直线插入和基础验证 |

## 非目标

MVP-0 不包含以下内容：

- 任意物体抓取或自动抓取姿态生成。
- 视觉定位、触觉闭环、滑移检测和掌内操作。
- 真实 MoveIt/MTC 规划、MuJoCo 接触仿真或 ros2_control 控制器。
- 力控制、阻抗控制、插入搜索、卡阻检测和自动失败恢复。
- 强化学习或端到端策略。

## 参考文档

- `doc/mvp0/tasks/`：MVP-0 的分阶段任务说明。
- `双臂灵巧手_MVP_Pick_and_Place占位方案.txt`：Pick-and-Place 作为
  Peg-in-Hole 占位任务的原始方案说明。
