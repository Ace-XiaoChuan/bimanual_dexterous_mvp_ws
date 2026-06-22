# Bimanual Dexterous Assembly MVP

双臂灵巧手协同装配 MVP 工作空间。项目当前以 Pick-and-Place 作为
Peg-in-Hole 的占位任务，先验证 ROS 2 通信、任务编排、场景重置、机械臂
Action、状态发布和错误处理等基础链路，再逐步加入真实仿真、灵巧手控制、
双臂协同和精密插入能力。

> 当前阶段：MVP-0 收尾与验收中。
> MVP-0 的目标不是证明真实装配能力，而是建立一条可编译、可启动、可重复
> 执行、可测试、可失败定位的纯软件任务链路。
> 在完成本文“**MVP-0 完成关闭项**”前，不应宣告 MVP-0 完成或进入 MVP-1。

## 项目目标

本项目的近期目标不是直接完成高精度装配，而是搭建一个可以反复运行、
可重置、可记录、可替换模块的双臂灵巧手任务骨架。

MVP 阶段优先验证：

* ROS 2 package、service、action 和 topic 的基础接口可编译、可运行。
* 任务层能够按固定顺序调用场景、机械臂、灵巧手和末端操作模块。
* 左右机械臂、灵巧手、控制器和命名空间后续可以独立扩展。
* Pick-and-Place 可以作为 Peg-in-Hole 的末端操作占位符。
* 失败时能够返回错误码、日志和任务状态，而不是静默失败。
* 从干净环境重新构建后，系统能够通过一条启动命令和一组自动化测试复现。

Pick-and-Place 只能验证系统骨架，不能替代真正的精密装配能力。接触建模、
柔顺控制、力反馈、孔轴对准、插入搜索、卡阻检测和失败恢复会在后续阶段
逐步加入。

## MVP-0 阶段进度

| 阶段   | 内容                                                  | 状态      |
| ---- | --------------------------------------------------- | ------- |
| 阶段 1 | ROS 2 工程绿色基线与 Git 初始化                               | 已完成     |
| 阶段 2 | `TaskState`、`StartTask`、`ResetScene`、`MoveArm` 接口生成 | 已完成     |
| 阶段 3 | Fake Scene Manager 与 `/assembly/reset_scene`        | 已完成     |
| 阶段 4 | Fake Arm Control 与 `/assembly/move_arm`             | 已完成     |
| 阶段 5 | `assembly_task_node` 最小任务编排                         | 待完成或待验收 |
| 阶段 6 | 一键启动、集成测试与连续运行验证                                    | 待完成或待验收 |
| 收尾阶段 | 干净环境回归、文档冻结、版本标签与验收证据                               | 待完成     |

## MVP-0 最小纵向链路

MVP-0 的目标任务链路为：

```text
StartTask service
  -> assembly_task_node
  -> ResetScene service
  -> MoveArm action
  -> TaskState topic
  -> SUCCESS / FAILED
```

最小状态机为：

```text
IDLE -> RESETTING -> ARM_HOME -> SUCCESS
                     \-> FAILED
```

当前 MVP-0 只支持固定任务：

* `task_name`: `mvp0_home`
* `arm_name`: `right_arm`
* `target_name`: `home`

## 仓库结构

```text
.
├── doc/
│   └── mvp0/
│       ├── tasks/               # MVP-0 分阶段任务说明
│       └── acceptance/          # MVP-0 验收结果、接口快照和完成清单
├── src/
│   ├── assembly_interfaces/     # 自定义 msg/srv/action 接口
│   ├── assembly_task/           # 最小任务编排节点
│   ├── fake_scene_manager/      # Fake 场景管理服务
│   ├── fake_arm_control/        # Fake 机械臂 Action Server
│   ├── fake_hand_control/       # 灵巧手控制占位包
│   ├── fake_terminal_operation/ # 末端操作占位包
│   ├── assembly_bringup/        # 启动编排包
│   └── assembly_tests/          # 集成测试包
└── README.md
```

## 软件包说明

| Package                   | 说明                                      | MVP-0 状态 |
| ------------------------- | --------------------------------------- | -------- |
| `assembly_interfaces`     | 定义任务服务、状态消息和机械臂 Action                  | 已实现      |
| `assembly_task`           | 维护最小任务流程，调用场景和机械臂接口                     | 阶段 5 待验收 |
| `fake_scene_manager`      | 提供 `/assembly/reset_scene` 服务           | 已实现      |
| `fake_arm_control`        | 提供 `/assembly/move_arm` Action          | 已实现      |
| `fake_hand_control`       | 后续封装 `open/preshape/close/hold/release` | 占位       |
| `fake_terminal_operation` | 后续封装 `PLACE/INSERT` 末端任务                | 占位       |
| `assembly_bringup`        | 集中管理 MVP-0 一键启动 launch 文件               | 阶段 6 待验收 |
| `assembly_tests`          | 放置 MVP-0 集成验收测试                         | 阶段 6 待验收 |

## 环境要求

* Ubuntu 22.04
* ROS 2 Humble
* Python 3.10
* `colcon`

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

在阶段 6 完成后，可通过一条命令启动 Fake 最小链路：

```bash
cd /home/ace/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch assembly_bringup mvp0_fake_system.launch.py
```

该 launch 文件应同时启动：

```text
fake_scene_manager_node
fake_arm_control_node
assembly_task_node
```

另开一个终端发送任务请求：

```bash
cd /home/ace/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 service call \
  /assembly/start_task \
  assembly_interfaces/srv/StartTask \
  "{task_name: 'mvp0_home'}"
```

可选：检查接口。

```bash
ros2 service list | grep -E '/assembly/(start_task|reset_scene)'
ros2 action list | grep /assembly/move_arm
ros2 topic list | grep /assembly/task_state
```

可选：监听任务状态。

```bash
ros2 topic echo /assembly/task_state
```

一次合法任务应至少发布以下状态：

```text
RESETTING
ARM_HOME
SUCCESS
```

当 ResetScene 服务或 MoveArm Action 不可用、执行失败或超时时，应发布：

```text
FAILED
```

## ROS 接口

### Service

| 名称                      | 类型                                   | 说明         |
| ----------------------- | ------------------------------------ | ---------- |
| `/assembly/start_task`  | `assembly_interfaces/srv/StartTask`  | 请求启动一个任务   |
| `/assembly/reset_scene` | `assembly_interfaces/srv/ResetScene` | 重置 Fake 场景 |

### Action

| 名称                   | 类型                                   | 说明           |
| -------------------- | ------------------------------------ | ------------ |
| `/assembly/move_arm` | `assembly_interfaces/action/MoveArm` | 请求机械臂移动到命名目标 |

### Topic

| 名称                     | 类型                                  | 说明            |
| ---------------------- | ----------------------------------- | ------------- |
| `/assembly/task_state` | `assembly_interfaces/msg/TaskState` | 发布任务状态、进度和错误码 |

## StartTask 响应与任务结果约定

MVP-0 中，`StartTask` 的 `accepted` 字段只表示请求是否通过任务入口校验：

```text
accepted = false
```

表示：

```text
task_name 为空
或 task_name 不受支持
```

对于合法任务：

```text
accepted = true
task_id 非空
error_code = 0
message = "Task accepted"
```

任务最终是否成功，必须以 `/assembly/task_state` 的终态为准：

```text
SUCCESS：最小链路执行成功
FAILED：任务在 ResetScene 或 MoveArm 阶段失败
```

MVP-0 可以采用同步实现，但不得把 `accepted` 误解为“任务已成功完成”。

MVP-1 及后续阶段可将任务执行改为后台异步模型；此时 `accepted = true`
仍表示“任务已被受理”，最终结果继续由任务状态 Topic 或后续查询接口返回。

## MVP-0 完成关闭项

MVP-0 不再新增功能模块。以下项目全部完成并留存验收证据后，才能宣告
MVP-0 完成。

### 1. 完成并验收最小任务编排节点

`assembly_task_node` 必须实现：

```text
Service Server：/assembly/start_task
Service Client：/assembly/reset_scene
Action Client：/assembly/move_arm
Topic Publisher：/assembly/task_state
```

合法任务应执行：

```text
StartTask(mvp0_home)
-> RESETTING
-> ResetScene(task_id)
-> ARM_HOME
-> MoveArm(right_arm, home, 5.0)
-> SUCCESS
```

非法任务应返回明确错误：

```text
task_name = ""
-> accepted = false
-> error_code = 3001

task_name != "mvp0_home"
-> accepted = false
-> error_code = 3002
```

### 2. 保证任务执行模型不会死锁或永久阻塞

`assembly_task_node` 不得在单线程 ROS 回调中阻塞等待自身依赖的 Future，
导致服务、Action 或反馈无法推进。

MVP-0 至少采用以下其中一种实现方式：

```text
方案 A：
MultiThreadedExecutor
+ ReentrantCallbackGroup
+ 合理等待 ResetScene 与 MoveArm Future

方案 B：
StartTask 回调创建独立工作线程，
由工作线程执行 ResetScene 与 MoveArm，
主 ROS executor 保持可调度状态
```

验收要求：

```text
合法任务不会卡死
失败场景不会永久等待
Action Result 能正常返回
连续任务不会因回调阻塞导致节点失去响应
```

### 3. 完成一键启动文件

`assembly_bringup` 中必须提供：

```text
launch/mvp0_fake_system.launch.py
```

启动命令：

```bash
ros2 launch assembly_bringup mvp0_fake_system.launch.py
```

启动后必须可发现：

```text
/assembly/reset_scene
/assembly/start_task
/assembly/move_arm
/assembly/task_state
```

### 4. 完成自动化集成测试

`assembly_tests` 必须能够自动启动 MVP-0 Fake 系统，并至少覆盖：

```text
1. 合法 mvp0_home 请求
2. 空 task_name 请求
3. 不支持的 task_name 请求
4. RESETTING -> ARM_HOME -> SUCCESS 状态序列
5. 连续执行 10 次合法任务
6. task_id 递增且不重复
7. 未启动 ResetScene 时进入 FAILED
8. 未启动 MoveArm 时进入 FAILED
```

推荐测试命令：

```bash
cd /home/ace/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

colcon test \
  --packages-select assembly_tests \
  --event-handlers console_direct+

colcon test-result --verbose
```

### 5. 完成干净环境回归验证

不得依赖旧的 `build/`、`install/` 或 `log/` 目录残留。

每次准备冻结 MVP-0 前，都必须从干净环境完成一次回归：

```bash
cd /home/ace/bimanual_dexterous_mvp_ws

rm -rf build install log

source /opt/ros/humble/setup.bash

colcon build --symlink-install
source install/setup.bash

colcon test --event-handlers console_direct+
colcon test-result --verbose
```

验收要求：

```text
全部 8 个 package 可构建
接口生成无错误
launch 文件可正常启动
集成测试全部通过
不存在 Python import 错误
不存在依赖历史构建产物的情况
```

### 6. 冻结文档、错误码和验收证据

完成 MVP-0 前，应在仓库中保留以下资料：

```text
doc/mvp0/acceptance/
├── mvp0_completion_checklist.md
├── build_and_test_result.md
├── interface_snapshot.md
└── known_limitations.md
```

建议至少记录：

```text
Git commit hash
ROS 2 Humble 版本
Python 版本
构建命令
测试命令
测试结果
失败场景结果
当前已知限制
```

完成验收后，创建版本标签：

```bash
git status
git add README.md doc/mvp0/acceptance src
git commit -m "chore: freeze MVP-0 acceptance baseline"
git push

git tag -a mvp0.0.0 -m "MVP-0 fake system integration complete"
git push origin mvp0.0.0
```

## 错误码表

| 错误码    | 来源            | 含义                                     |
| ------ | ------------- | -------------------------------------- |
| `0`    | 通用            | 无错误                                    |
| `1001` | ResetScene    | `task_id` 不能为空                         |
| `2001` | MoveArm       | 不支持的 `arm_name`                        |
| `2002` | MoveArm       | 不支持的 `target_name`                     |
| `2003` | MoveArm       | `timeout_sec` 必须大于 0                   |
| `3001` | StartTask     | `task_name` 不能为空                       |
| `3002` | StartTask     | 不支持的 `task_name`                       |
| `3101` | Assembly Task | `/assembly/reset_scene` 服务不可用          |
| `3201` | Assembly Task | `/assembly/move_arm` Action Server 不可用 |

对于下层接口返回的业务错误，`assembly_task_node` 应尽量透传：

```text
error_code = 下层接口返回的 error_code
message = 下层接口返回的 message
```

## 集成验收测试

MVP-0 的自动化验收至少覆盖：

```text
合法任务请求
空 task_name
不支持的 task_name
任务状态发布
ResetScene 不可用
MoveArm 不可用
连续 10 次执行
task_id 连续递增
```

合法任务的期望状态序列：

```text
RESETTING -> ARM_HOME -> SUCCESS
```

失败任务的期望终态：

```text
FAILED
```

连续执行 10 次后，应满足：

```text
每次请求均可返回
每个 task_id 均不重复
每次任务均有终态
节点不崩溃
节点不死锁
日志可定位任务开始、状态变化和失败原因
```

## MVP-0 完成定义

MVP-0 完成不等于“Fake 节点代码已经写完”，而是满足以下所有条件：

```text
任何人从干净环境拉取仓库后：

1. 可以完成 colcon build；
2. 可以通过一条 launch 命令启动系统；
3. 可以通过 StartTask 发起 mvp0_home；
4. 可以观察到 RESETTING -> ARM_HOME -> SUCCESS；
5. 可以对非法请求获得明确错误码；
6. 可以在依赖缺失时进入明确 FAILED；
7. 可以通过自动化测试重复验证；
8. 可以连续执行 10 次而不崩溃、不死锁；
9. 可以从日志和 TaskState 定位失败位置；
10. 可以通过 Git tag 定位冻结版本。
```

在以上条件全部满足前，项目状态应标记为：

```text
MVP-0 收尾与验收中
```

全部满足后，项目状态可更新为：

```text
MVP-0 已完成：Fake 系统最小纵向链路已冻结
```

## 设计原则

* 上层任务接口保持通用，不把系统核心写死为单一 `place` 流程。
* 抓取、运输和末端操作分阶段设计，便于后续把 `PLACE` 替换为 `INSERT`。
* 灵巧手在早期被降维为预设抓型执行器，任务层只发送高层命令。
* 场景中的物体抓取可先使用逻辑附着，后续再替换为真实物理接触。
* 关键动作必须有超时、错误码和结构化日志。
* 任务成功与失败必须具有可观测终态，不能静默结束。
* 上层接口在 MVP-1 替换底层控制实现时应尽量保持稳定。

建议的长期任务分层：

```text
acquire object -> transport object -> terminal operation
```

其中 `terminal operation` 当前为 Pick-and-Place，后续升级为 Peg-in-Hole。

## MVP 路线图

后续 MVP 的推进原则是先补完整任务闭环，再逐步替换底层能力。每一阶段都应
保留一键启动、可重复测试、状态发布、错误码和日志，不因为引入新能力而破坏
上层任务接口。

| 阶段    | 版本目标                              | 核心验收结果                         |
| ----- | --------------------------------- | ------------------------------ |
| MVP-0 | Fake 最小纵向链路                       | `mvp0_home` 可启动、可观测、可测试、可冻结 |
| MVP-1 | Fake 单臂单手 Pick-and-Place 完整任务闭环   | 完整抓取、搬运、放置状态机跑通             |
| MVP-2 | RViz / MoveIt 单臂 Pick-and-Place    | 机械臂由真实规划执行固定目标点             |
| MVP-3 | MuJoCo 单臂 Pick-and-Place          | 验证仿真关节控制、物体状态和场景重置          |
| MVP-4 | 双臂双手 Pick-and-Place               | 验证左右命名空间、控制器隔离和简单同步         |
| MVP-5 | 预插入与末端操作抽象                       | 将 `PLACE` 平滑替换为 `INSERT` 占位    |
| MVP-6 | 简单 Peg-in-Hole                    | 大间隙、低速直线插入、基础插入结果验证         |
| MVP-7 | 柔顺控制与真实硬件准备                      | 接入力/触觉反馈、安全约束和真机接口           |

### MVP-1：Fake Pick-and-Place 闭环

MVP-1 的目标是从 MVP-0 的 `RESETTING -> ARM_HOME -> SUCCESS` 扩展为一条
完整但仍然是 Fake 的 Pick-and-Place 任务链路。

推荐状态机：

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
-> DETACH_OBJECT
-> HAND_OPEN
-> ARM_RETREAT
-> ARM_HOME
-> SUCCESS
```

本阶段应实现：

```text
fake_hand_control:
  open / preshape / close / hold / release

fake_scene_manager:
  reset_scene / attach_object / detach_object / get_object_pose

fake_terminal_operation:
  execute_terminal_operation(operation_type = PLACE)

fake_arm_control:
  home / pregrasp / grasp / lift / preplace / place / retreat

assembly_task:
  支持 task_name = "pick_and_place_mvp"
```

验收重点：

```text
1. 一条 launch 命令启动完整 Fake Pick-and-Place 系统；
2. 一条 StartTask 请求触发完整任务；
3. 物体可被逻辑附着和解除附着；
4. 每个关键动作都有 TaskState；
5. 任一 Fake 服务或 Action 失败时进入 FAILED；
6. 连续执行 10 次不崩溃、不死锁；
7. 集成测试覆盖成功链路和主要失败链路。
```

技术栈：

```text
ROS 2 Humble
rclpy
ROS 2 Service / Action / Topic
自定义 msg / srv / action
launch_ros
Python dataclass
YAML 配置
pytest / unittest
colcon
```

MVP-1 暂不引入：

```text
MoveIt 真实规划
MuJoCo 物理接触
双臂协同
灵巧手全关节真实控制
视觉定位
力控制
Peg-in-Hole 插入
```

### MVP-2：RViz / MoveIt 单臂 Pick-and-Place

MVP-2 的目标是把 MVP-1 中 Fake 机械臂的底层能力替换为 MoveIt 规划执行，
但尽量保持 `assembly_task` 的上层状态机和任务接口稳定。

推荐演进路径：

```text
Fake MoveArm
-> MoveIt named target
-> MoveIt pose target
-> PlanningScene object
-> AttachedCollisionObject
-> 简单 Pick-and-Place 轨迹
```

验收重点：

```text
1. RViz 中可以看到机器人模型、TF 和规划场景；
2. 机械臂能规划并执行 home / pregrasp / grasp / place 等固定目标；
3. 物体能加入 PlanningScene；
4. 抓取后物体能作为 attached object 跟随末端；
5. 释放后物体从 attached object 回到场景；
6. 上层 StartTask 和 TaskState 语义不变。
```

技术栈：

```text
MoveIt 2
RViz2
URDF / Xacro
SRDF
TF2
robot_state_publisher
joint_state_publisher 或 joint_state_broadcaster
ros2_control
joint_trajectory_controller
MoveIt PlanningScene
MoveIt collision object / attached collision object
```

### MVP-3：MuJoCo 单臂物理仿真

MVP-3 的目标是把单臂 Pick-and-Place 放进物理仿真环境，验证关节控制、
场景重置、物体状态同步和基础接触参数。

验收重点：

```text
1. MuJoCo 中机器人、手、桌面和物体模型可加载；
2. ROS 2 控制命令能驱动仿真关节；
3. 场景可以重置到确定初始状态；
4. 物体位置和附着状态可观测；
5. 任务结束后可以重复运行；
6. 物理仿真失败时能回传明确 FAILED 状态。
```

技术栈：

```text
MuJoCo
MJCF 或 URDF 到 MuJoCo 模型转换
ROS 2 与 MuJoCo bridge
ros2_control 仿真硬件接口
trajectory controller
/clock 仿真时间
接触参数、摩擦、质量和惯量配置
rosbag2 可选
```

### MVP-4：双臂双手 Pick-and-Place

MVP-4 的目标是从单臂扩展到双臂双手，但第一版不要求复杂同步和闭链操作。
重点是验证左右系统可以共存、独立控制、状态可区分。

推荐最小任务：

```text
left_arm  -> move_to_ready 或 hold_position
right_arm -> 完成 Pick-and-Place
left_arm  -> return_home
right_arm -> return_home
```

也可以做稍复杂版本：

```text
left_arm  抓取物体 A 并保持
right_arm 抓取物体 B 并放到 A 附近
两臂释放并返回 Home
```

验收重点：

```text
1. 左右臂、左右手有清晰 namespace；
2. 左右控制器不会互相抢资源；
3. TF 树没有重复 frame 或断裂；
4. 双臂碰撞模型可用；
5. 任务状态能区分 left/right 子任务；
6. 简单事件同步可运行。
```

技术栈：

```text
ROS 2 namespace
多机器人 URDF / Xacro 参数化
双 MoveIt planning group
多 controller_manager
TF2 frame 命名规范
MoveIt collision checking
launch 参数化
简单事件同步或任务子状态机
```

### MVP-5：预插入与末端操作抽象

MVP-5 的目标是让系统开始面向 Peg-in-Hole，但仍不要求真实插入成功。重点是
把 Pick-and-Place 的末端 `PLACE` 阶段替换为统一的 terminal operation
接口，并增加 `INSERT` 占位流程。

推荐接口语义：

```text
execute_terminal_operation(operation_type, parameters)

operation_type = PLACE
operation_type = INSERT
```

`INSERT` 占位流程：

```text
ARM_PREINSERT
ALIGN_APPROACH_AXIS
ARM_INSERT_APPROACH
CHECK_PREINSERT_POSE
RETREAT
```

验收重点：

```text
1. 不重写 acquire 和 transport 阶段；
2. 通过配置切换 PLACE / INSERT；
3. 装配坐标系、孔轴方向和接近方向定义清楚；
4. 插入前位姿误差可记录；
5. terminal operation 失败时能明确返回 FAILED。
```

技术栈：

```text
geometry_msgs / PoseStamped
TF2 坐标变换
MoveIt pose constraint
MoveIt Cartesian path
YAML 任务配置
装配 frame 和 target frame 管理
```

### MVP-6：简单 Peg-in-Hole

MVP-6 的目标是在简化条件下实现第一版插入：大间隙、低速、固定初始位姿、
固定插入方向，不处理复杂卡阻和自动恢复。

验收重点：

```text
1. 插入对象和孔位在已知坐标系下定义；
2. 机械臂能低速沿插入轴直线运动；
3. 能判断插入成功、超时或失败；
4. 能记录插入深度、最终位姿和错误码；
5. 失败后能停止并撤离到安全位置。
```

技术栈：

```text
MoveIt Cartesian path
低速轨迹执行
末端位姿误差计算
简单插入成功判定
基础接触信号或仿真状态读取
rosbag2 数据记录
```

### MVP-7：柔顺控制与真实硬件准备

MVP-7 才进入更接近真实装配的能力建设，包括力反馈、柔顺控制、安全约束和
真机接口。此阶段不应在 MVP-1 到 MVP-3 之前提前展开。

验收重点：

```text
1. 具备力/力矩或触觉反馈入口；
2. 能做简单 admittance / impedance 控制；
3. 能检测卡阻、过力和异常接触；
4. 有急停、速度限制和工作空间限制；
5. 真机接口与仿真接口尽量保持同一上层语义；
6. 实验数据可记录、可回放、可复盘。
```

技术栈：

```text
ros2_control hardware interface
force/torque sensor
tactile sensor 可选
admittance control
impedance control
安全限位和急停
手眼标定 / TCP 标定 / 力传感器零偏
rosbag2
实验日志和数据分析脚本
```

## 实施策略补充

### 主线与真机支线

MVP 主线不应过早把完整任务成功绑定到真机上。早期主线按以下顺序推进：

```text
MVP-1：Fake 完整任务闭环
MVP-2：MoveIt / RViz 单臂规划验证
MVP-3：MuJoCo 单臂物理仿真
MVP-4：双臂系统扩展
```

这样做的目的不是回避真机，而是避免在任务状态机、MoveIt 规划、控制器、
坐标系、手部动作、抓取稳定性和硬件安全策略都不稳定时，把所有问题混在
一起调试。

可以并行保留一条真机冒烟测试支线，但它不作为 MVP-1 的完成标准：

```text
真机上电
读取 joint_states
确认 TF 和 joint name
控制器 enable / disable
单关节或单臂低速回 Home
急停、限位和速度限制验证
```

真机支线的目标是提前暴露硬件接入风险；MVP 主线的目标是保证任务架构
可解释、可重复、可测试。

### 双臂能力的引入节奏

项目最终目标包含双臂双手协同，但早期 MVP 不应直接要求复杂双臂装配成功。
推荐分三步引入：

```text
第一步：双臂系统存在
第二步：双臂顺序执行
第三步：双臂协同装配
```

因此：

```text
MVP-1：不做双臂，全 Fake 单臂单手任务闭环；
MVP-2：不做双臂，复现单臂 MoveIt / MTC Pick-and-Place；
MVP-3：仍以单臂物理仿真为主；
MVP-4：开始双臂 bringup 和简单顺序任务；
MVP-5 之后：再逐步进入左臂保持、右臂预插入等装配占位任务。
```

MVP-4 的重点不是高难度协同，而是验证：

```text
左右 namespace
双臂 URDF / Xacro
TF frame 命名
MoveIt planning group
controller 配置
joint_states 是否冲突
launch 参数化
任务层是否能区分 left / right
```

真正的双臂协同装配应建立在以上工程基础稳定之后。

### 学习模型的使用边界

模仿学习、强化学习或抓取生成模型可以作为后续能力，但不应成为早期 MVP
成功的前置条件。早期应先建立不用模型也能跑通的可解释基线：

```text
object pose from config
pregrasp pose from config
grasp pose from config
hand preshape from grasp_library.yaml
close hand
logical attach / simulated attach
```

学习模型更适合作为模块替换，而不是直接控制完整任务。推荐系统分层为：

```text
assembly_task 状态机
  -> arm_motion 规划模块
  -> hand_control 抓型模块
  -> scene_manager 场景模块
  -> terminal_operation 末端操作模块
       -> optional learning_policy
```

后续适合引入模型的位置：

```text
抓取位姿生成：
  输入物体点云、RGB-D、mesh 或 object pose；
  输出 grasp pose、grasp type、approach direction 和 score。

灵巧手抓型或闭合策略：
  输入物体形状、手指状态、触觉或接触信息；
  输出 preshape、finger joint targets、closure amount 或 grip force。

插入和装配修正策略：
  输入末端位姿误差、力/力矩、触觉和接触状态；
  输出小幅修正动作、搜索方向、插入速度或撤退判断。
```

不建议早期让模型直接从 reset 到任务结束输出整段 Pick-and-Place 或
Peg-in-Hole 动作。这样会把规划、抓取、控制、接触和失败恢复混在一起，
难以定位问题。

推荐引入节奏：

```text
MVP-1：不用模型，全 Fake；
MVP-2：不用模型，MoveIt / MTC 固定抓取；
MVP-3：不用模型，物理仿真和控制接口验证；
MVP-4：可选接入简单 grasp pose generator；
MVP-5：装配占位仍以规则为主；
MVP-6：可选接入插入修正策略；
MVP-7 之后：模仿学习或强化学习作为策略模块正式比较。
```

## 非目标

MVP-0 不包含以下内容：

* 任意物体抓取或自动抓取姿态生成。
* 视觉定位、触觉闭环、滑移检测和掌内操作。
* 真实 MoveIt/MTC 规划、MuJoCo 接触仿真或 ros2_control 控制器。
* 力控制、阻抗控制、插入搜索、卡阻检测和自动失败恢复。
* 真机控制、真机双臂协同或真实装配执行。
* 强化学习或端到端策略。
* 任务队列、任务取消、暂停恢复和多任务并发。

## 参考文档

* `doc/mvp0/tasks/`：MVP-0 的分阶段任务说明。
* `doc/mvp0/acceptance/`：MVP-0 构建、测试和冻结验收记录。
* `双臂灵巧手_MVP_Pick_and_Place占位方案.txt`：Pick-and-Place 作为
  Peg-in-Hole 占位任务的原始方案说明。
