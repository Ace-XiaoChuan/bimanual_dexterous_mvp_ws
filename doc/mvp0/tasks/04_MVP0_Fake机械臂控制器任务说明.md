# MVP-0 第四阶段工作说明：Fake Arm Control

## 1. 工作目标

在 `fake_arm_control` 软件包中实现第二个可运行的 Fake Server：

```text
MoveArm Action Server
```

该节点接收机械臂移动请求，模拟执行一个命名目标动作，并返回执行结果。

本阶段完成后，项目将同时具备：

```text
ResetScene Service Server
MoveArm Action Server
```

这为下一阶段连接最小纵向链路打基础。

## 2. 本阶段范围

实现：

```text
节点：fake_arm_control_node
Action：/assembly/move_arm
接口：assembly_interfaces/action/MoveArm
```

本阶段只支持：

```text
arm_name = "right_arm"
target_name = "home"
```

硬件映射说明：

```text
right_arm = 首个或右侧 Franka Research 3 的逻辑名
right_hand = 因时 RH56DFX-2R 的逻辑名，本阶段不控制灵巧手
```

本阶段仍然是 fake 节点，不加载 Franka Research 3 或因时 RH56DFX-2R
真实驱动，也不发送真实关节命令。

暂不实现：

```text
left_arm
pregrasp
grasp
place
真实轨迹规划
关节空间控制
笛卡尔空间控制
MoveIt
MuJoCo
Franka Research 3 真实机械臂驱动
碰撞检测
失败注入
```

## 3. 内部机械臂状态

节点维护以下最小状态：

```text
current_arm
current_target
is_moving
last_goal_success
last_error_code
last_message
```

初始状态建议为：

```text
current_arm = ""
current_target = "unknown"
is_moving = false
last_goal_success = false
last_error_code = 0
last_message = ""
```

合法动作执行成功后，状态更新为：

```text
current_arm = "right_arm"
current_target = "home"
is_moving = false
last_goal_success = true
last_error_code = 0
last_message = "Arm moved to home successfully"
```

## 4. Action 处理规则

Goal 请求包含：

```text
arm_name
target_name
timeout_sec
```

处理流程：

```text
接收 goal
→ 检查 timeout_sec
→ 检查 arm_name
→ 检查 target_name
→ 发布执行反馈
→ 更新内部机械臂状态
→ 返回执行结果
```

本阶段建议所有 goal 先接受，然后在执行阶段返回成功或失败结果。

这样非法请求也能通过 `MoveArm.Result` 明确返回：

```text
success
error_code
message
```

### 成功结果

当请求为：

```text
arm_name = "right_arm"
target_name = "home"
timeout_sec > 0.0
```

返回：

```text
success = true
error_code = 0
message = "Arm moved to home successfully"
```

执行期间发布 feedback：

```text
current_state = "accepted"
progress = 0.0

current_state = "moving"
progress = 0.5

current_state = "succeeded"
progress = 1.0
```

### 非法 timeout

当 `timeout_sec <= 0.0` 时，返回：

```text
success = false
error_code = 2003
message = "timeout_sec must be positive"
```

### 不支持的机械臂

当 `arm_name` 不是 `right_arm` 时，返回：

```text
success = false
error_code = 2001
message = "unsupported arm_name"
```

### 不支持的目标点

当 `target_name` 不是 `home` 时，返回：

```text
success = false
error_code = 2002
message = "unsupported target_name"
```

本阶段只设置上述错误码，不建立完整错误码系统。

## 5. 文件修改范围

主要修改：

```text
fake_arm_control/
├── fake_arm_control/
│   ├── __init__.py
│   └── fake_arm_control_node.py
├── resource/
│   └── fake_arm_control
├── package.xml
├── setup.cfg
└── setup.py
```

在 `setup.py` 中注册可执行入口：

```text
fake_arm_control_node
```

节点应通过以下命令启动：

```bash
ros2 run fake_arm_control fake_arm_control_node
```

## 6. 实现建议

节点建议使用：

```text
rclpy.action.ActionServer
assembly_interfaces.action.MoveArm
```

建议类名：

```text
FakeArmControlNode
```

建议常量：

```text
ACTION_NAME = "/assembly/move_arm"
SUPPORTED_ARM = "right_arm"
SUPPORTED_TARGET = "home"
UNSUPPORTED_ARM_ERROR = 2001
UNSUPPORTED_TARGET_ERROR = 2002
INVALID_TIMEOUT_ERROR = 2003
```

每次 goal 处理都应输出结构化日志，至少包含：

```text
event
arm_name
target_name
timeout_sec
success
error_code
message
```

## 7. 验证流程

### 编译目标软件包

```bash
cd ~/bimanual_dexterous_mvp_ws

source /opt/ros/humble/setup.bash

colcon build \
  --packages-select assembly_interfaces fake_arm_control \
  --symlink-install
```

### 终端一：启动 Action Server

```bash
cd ~/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run fake_arm_control fake_arm_control_node
```

### 终端二：确认 Action 存在

```bash
source /opt/ros/humble/setup.bash
source ~/bimanual_dexterous_mvp_ws/install/setup.bash

ros2 action list | grep move_arm
ros2 action type /assembly/move_arm
```

预期 Action 类型：

```text
assembly_interfaces/action/MoveArm
```

### 调用合法请求

```bash
ros2 action send_goal \
  /assembly/move_arm \
  assembly_interfaces/action/MoveArm \
  "{arm_name: 'right_arm', target_name: 'home', timeout_sec: 5.0}" \
  --feedback
```

预期结果：

```text
success: true
error_code: 0
message: Arm moved to home successfully
```

预期能看到 feedback 进度：

```text
progress: 0.0
progress: 0.5
progress: 1.0
```

### 调用非法 timeout

```bash
ros2 action send_goal \
  /assembly/move_arm \
  assembly_interfaces/action/MoveArm \
  "{arm_name: 'right_arm', target_name: 'home', timeout_sec: 0.0}" \
  --feedback
```

预期结果：

```text
success: false
error_code: 2003
message: timeout_sec must be positive
```

### 调用不支持的机械臂

```bash
ros2 action send_goal \
  /assembly/move_arm \
  assembly_interfaces/action/MoveArm \
  "{arm_name: 'left_arm', target_name: 'home', timeout_sec: 5.0}" \
  --feedback
```

预期结果：

```text
success: false
error_code: 2001
message: unsupported arm_name
```

### 调用不支持的目标点

```bash
ros2 action send_goal \
  /assembly/move_arm \
  assembly_interfaces/action/MoveArm \
  "{arm_name: 'right_arm', target_name: 'pregrasp', timeout_sec: 5.0}" \
  --feedback
```

预期结果：

```text
success: false
error_code: 2002
message: unsupported target_name
```

## 8. 验收标准

以下条件全部满足后，本阶段完成：

1. `fake_arm_control` 可以成功编译；
2. 节点可以通过 `ros2 run` 启动；
3. `/assembly/move_arm` Action 可以被发现；
4. Action 类型正确；
5. 合法请求返回成功；
6. 非法 `timeout_sec` 请求返回失败；
7. 不支持的 `arm_name` 请求返回失败；
8. 不支持的 `target_name` 请求返回失败；
9. 合法请求执行期间能看到 feedback；
10. 每次 goal 都有日志；
11. 连续调用多次不会崩溃；
12. 执行后内部状态保持一致；
13. 不依赖 MoveIt、MuJoCo 或真实硬件。

## 9. 回归编译

```bash
cd ~/bimanual_dexterous_mvp_ws

source /opt/ros/humble/setup.bash

colcon build --symlink-install
source install/setup.bash
```

确保完整工作区仍然能够正常编译。

## 10. Git 提交

```bash
git status
git add src/fake_arm_control doc/04_MVP0_Fake机械臂控制器任务说明.md
git commit -m "feat: implement fake arm move action server"
git push
```

该提交形成项目的第一版 Fake Arm Action Server 基线。

## 11. 下一阶段入口

完成 Fake Arm Control 后，第五阶段实现：

```text
assembly_task 最小任务编排节点
```

它只需要串联：

```text
StartTask
→ ResetScene
→ MoveArm(right_arm, home)
→ SUCCESS
```

暂时不实现完整 Pick and Place，不实现灵巧手动作，不实现末端操作。
