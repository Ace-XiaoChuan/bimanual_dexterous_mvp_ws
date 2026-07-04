# MVP-2 第二阶段：FR3 模型与 MoveIt 配置接入

## 1. 工作目标

在 RViz / MoveIt 中加载 FR3 模型、TF、planning group、controller 配置和
fake/dummy hardware，为后续规划执行做基础验证。

## 2. 本阶段范围

涉及内容：

```text
FR3 URDF / Xacro
SRDF
MoveIt config
robot_state_publisher
joint_state_publisher 或 joint_state_broadcaster
ros2_control fake/dummy hardware
RViz
```

## 3. 推荐验证顺序

```text
模型可加载
TF 连通
joint name 与 MoveIt 配置一致
planning group 可发现
home named target 可规划
fake/dummy hardware 可执行轨迹
```

## 4. 验收标准

```text
一条 launch 命令能启动 FR3 MoveIt / RViz demo
RViz 中能看到 FR3 模型
MoveIt planning group 可用
home 目标可规划
轨迹可在 fake/dummy hardware 上执行
```

## 5. 非目标

```text
不接真实 FR3
不接 RH56DFX 真手
不加载真实场景物体
不做完整任务编排
```
