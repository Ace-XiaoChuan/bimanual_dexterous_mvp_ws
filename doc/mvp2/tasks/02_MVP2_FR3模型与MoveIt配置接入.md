# MVP-2 第二阶段：FR3 模型与 MoveIt 配置接入

## 1. 工作目标

在 RViz / MoveIt 中加载 FR3 模型、TF、planning group、controller 配置和
fake/dummy hardware，为后续规划执行做基础验证。

本阶段优先使用 Franka 官方 ROS 2 / MoveIt 配置，不手工复制或改写官方
`franka_fr3_moveit_config`。本仓库只保留依赖清单、上层 bringup 和后续
`moveit_arm_control` 适配逻辑。

## 2. 本阶段范围

涉及内容：

```text
franka_description 中的 FR3 URDF / Xacro
franka_description 中的 FR3 SRDF / Xacro
franka_fr3_moveit_config 官方 MoveIt config
robot_state_publisher
joint_state_publisher 或 joint_state_broadcaster
ros2_control fake/dummy hardware
RViz
```

## 3. 官方依赖接入方式

推荐使用仓库内的依赖清单恢复官方包：

```bash
cd /home/ace/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
vcs import src < dependencies/franka_ros2_humble.repos
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
colcon build --symlink-install
source install/setup.bash
```

当前官方 `franka_hardware` 构建会查找 `Franka 0.13.2`。如果 CMake 报
`Could not find a package configuration file provided by "Franka"`，先安装
`ros-humble-libfranka`，再重新执行 `rosdep` 和 `colcon build`。

官方包应作为 pinned upstream dependency 接入，不应把
`franka_fr3_moveit_config/config/`、`launch/`、`rviz/` 内容手工复制到
`assembly_bringup` 或 `moveit_arm_control` 中。

如果本机已经有完整 `/home/ace/franka_ros2_ws`，也可以先在终端中 source
该 workspace，再 source 本仓库 workspace；但该 workspace 必须包含
`franka_fr3_moveit_config`，仅有 `franka_description` 不足以完成本任务。

## 4. 推荐验证顺序

```text
franka_fr3_moveit_config package 可发现
模型可加载
TF 连通
joint name 与 MoveIt 配置一致
planning group 可发现
官方 ready named target 可规划
fake/dummy hardware 可执行轨迹
```

推荐先执行官方 fake hardware MoveIt demo：

```bash
ros2 launch franka_fr3_moveit_config moveit.launch.py \
  robot_ip:=dont-care \
  use_fake_hardware:=true
```

## 5. 验收标准

```text
ros2 pkg prefix franka_fr3_moveit_config 可找到官方配置包
一条 launch 命令能启动 FR3 MoveIt / RViz demo
RViz 中能看到 FR3 模型
MoveIt planning group fr3_arm 可用
官方 ready 目标可规划
轨迹可在 fake/dummy hardware 上执行
```

Franka 官方 SRDF 当前提供的命名目标包括 `ready` 和 `extended`。MVP 配置中
冻结的逻辑目标 `home`、`pregrasp`、`grasp` 等不在本阶段改写官方 SRDF；
后续由任务 03 的 `moveit_arm_control` 做逻辑目标到 MoveIt named target
或 pose target 的映射。

## 6. 非目标

```text
不手工生成自定义 fr3_moveit_config
不复制官方 MoveIt 配置作为本仓库自研代码
不接真实 FR3
不接 RH56DFX 真手
不加载真实场景物体
不做完整任务编排
```
