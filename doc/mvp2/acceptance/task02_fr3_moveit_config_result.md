# MVP-2 任务 02 验收记录：FR3 模型与 MoveIt 配置接入

## 验收结论

任务 02 已完成。

本阶段使用 Franka 官方 `franka_description` 和 `franka_fr3_moveit_config`
作为 FR3 模型、SRDF、MoveIt 配置和 fake hardware demo 来源。本仓库只保留
依赖清单与接入说明，不复制官方 MoveIt 配置作为自研代码。

## 依赖来源

```text
dependencies/franka_ros2_humble.repos
```

恢复到本地后，官方源码位于：

```text
src/third_party/franka_description/
src/third_party/franka_ros2/
```

上述目录由 `.gitignore` 忽略，不作为本仓库源码提交。

## 构建验证

已安装系统依赖：

```text
ros-humble-libfranka
```

已完成构建：

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-up-to franka_fr3_moveit_config \
  --cmake-args -DBUILD_TESTING=OFF
source install/setup.bash
```

`franka_fr3_moveit_config` 可被 ROS 2 发现：

```text
/home/ace/bimanual_dexterous_mvp_ws/install/franka_fr3_moveit_config
```

## 启动验证

启动命令：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch franka_fr3_moveit_config moveit.launch.py \
  robot_ip:=dont-care \
  use_fake_hardware:=true
```

已观察到的后端启动证据：

```text
robot_state_publisher 加载 FR3 link / hand link
move_group 加载 robot model 'fr3'
MoveIt planning pipeline 使用 OMPL
fr3_arm_controller 加载并激活
joint_state_broadcaster 加载并激活
MoveGroup 输出 “You can start planning now!”
```

## RViz / MoveIt 人工验收

已在 RViz MotionPlanning 面板中完成：

```text
FR3 模型可见
planning group fr3_arm 可用
官方 named target ready 可 Plan
ready 轨迹可 Execute 到 fake hardware
```

## 说明

Franka 官方 SRDF 当前提供的命名目标包括 `ready` 和 `extended`。MVP 配置中
冻结的逻辑目标 `home`、`pregrasp`、`grasp` 等不在任务 02 改写官方 SRDF；
后续由任务 03 的 `moveit_arm_control` 负责逻辑目标到 MoveIt named target
或 pose target 的映射。
