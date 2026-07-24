# MVP-3 第三阶段：ROS 2 - MuJoCo 桥接与仿真时间

## 1. 工作目标

建立 MuJoCo 仿真循环与 ROS 2 的最小 bridge，使 ROS 图能观察仿真时间、FR3
关节状态、TF 和对象状态，并能把受控命令送入仿真。

## 2. 最小数据流

```text
MuJoCo step loop
-> /clock
-> /joint_states
-> /tf
-> simulation object state

trajectory / joint target command
-> bridge command buffer
-> MuJoCo actuator or controller
```

bridge 应明确谁驱动 step：固定速率仿真循环驱动 MuJoCo，ROS callback 只更新
命令缓存，不直接在 callback 内执行长时间仿真。

## 3. 时间与复位要求

```text
use_sim_time=true 的节点可以收到递增 /clock
暂停、恢复和 reset 后时间行为明确并记录
reset 后 joint state、TF 和 object state 在有限时间内重新发布
bridge 关闭时不遗留后台仿真线程
```

## 4. 接口建议

实现可以选择 topic、service 或 ros2_control 适配，但必须提供等价能力：

```text
发送 FR3 joint target 或 JointTrajectory
读取 FR3 joint state
读取 plug pose / attached state
请求仿真 reset
```

若采用 ros2_control，MuJoCo bridge 是 sim hardware 的实现者；若采用专用
bridge，必须保持其命令和状态语义可被上层 adapter 消费。两种实现不能并行
成为同一关节的控制源。

## 5. 验收标准

```text
ros2 topic echo 可获得递增 /clock
joint state 名称、数量和顺序与 FR3 模型一致
robot_state_publisher 可产生完整 TF 链
无命令时仿真稳定保持
一条受控 joint target 可改变对应 qpos
```

## 6. 非目标

```text
不在本阶段接入 MoveArm.action
不做任务状态机
不做物体抓取判定
```
