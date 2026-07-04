# MVP-2 第七阶段：RViz 一键启动与集成验收

## 1. 工作目标

提供一条 launch 命令启动 MVP-2 所需节点，使用户可以在 RViz 中观察 FR3、
规划场景、object 和任务状态。

## 2. 推荐 launch

```text
src/assembly_bringup/launch/mvp2_moveit_system.launch.py
```

建议启动：

```text
robot_state_publisher
MoveIt move_group
RViz
moveit_arm_control
fake_scene_manager 或 moveit_scene_manager
fake_hand_control
fake_terminal_operation
assembly_task
```

## 3. 验收标准

```text
一条 launch 命令可启动完整 MVP-2 系统
ros2 node list 能看到关键节点
ros2 action list 能看到 MoveArm
ros2 service list 能看到 scene / hand / terminal services
一条 StartTask 请求可触发任务
RViz 中可观察 FR3 规划和 object 状态
```

## 4. 非目标

```text
不启动真实 FR3 驱动
不启动 MuJoCo
不做真机安全检查
```
