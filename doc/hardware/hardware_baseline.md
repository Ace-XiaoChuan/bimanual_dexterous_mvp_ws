# Hardware Baseline

本文件记录当前项目的真实硬件选型。MVP-0 仍然使用纯软件 fake 节点，
该硬件基线用于后续 URDF / MoveIt / MuJoCo / ros2_control / 真机 bringup
的命名和集成规划。

## 已确定硬件

| 角色 | 型号 | 当前工程映射 |
| --- | --- | --- |
| 机械臂 | Franka Research 3 | `right_arm` 先映射到首个或右侧 FR3 |
| 灵巧手 | 因时 RH56DFTP-2R | `right_hand` 先映射到首个或右侧 RH56DFTP-2R |

## 命名约定

* `right_arm` / `right_hand` 是当前单臂单手链路的默认逻辑目标。
* `left_arm` / `left_hand` 作为双臂双手扩展的预留逻辑名称。
* 若后续采购第二套硬件或左手机械手镜像型号，应在本文档中补充左侧型号、
  序列号、IP、控制器命名和 TF 前缀。

## MVP-0 边界

MVP-0 不加载 Franka Research 3 或因时 RH56DFTP-2R 的真实驱动，
也不下发真实关节命令。当前 fake 节点只验证：

```text
StartTask
-> ResetScene
-> MoveArm(right_arm, home)
-> TaskState
```

真实硬件接入应从单节点 bringup、joint_states、TF、限速、急停和低速
空载动作开始，不应直接把完整 Pick-and-Place 或 Peg-in-Hole 绑定到真机。
