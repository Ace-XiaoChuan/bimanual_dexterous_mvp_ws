# MVP-1 已知限制

MVP-1 是纯软件 fake Pick-and-Place 基线。它的价值在于冻结任务层接口、
状态机、错误码、日志和自动化验收方式，不代表真实装配能力已经完成。

## 当前不包含

- 不控制真实 Franka Research 3。
- 不控制真实 因时 RH56DFX-2R 全关节。
- 不加载真实硬件驱动。
- 不下发真实关节命令。
- 不做真实抓取。
- 不做真实接触建模。
- 不做物理仿真。
- 不做视觉定位。
- 不做力/力矩反馈。
- 不做阻抗、导纳或柔顺控制。
- 不做 MoveIt 规划。
- 不做 MoveIt Task Constructor 流程。
- 不做 MuJoCo。
- 不做 Peg-in-Hole。
- 不做双臂协同。
- 不支持任务取消、暂停、恢复。
- 不支持多个任务并发执行。
- 已有任务运行时，新的 `StartTask` 请求会被拒绝并返回错误码 `3003`。
- 不支持运行时动态生成抓取位姿。
- 不支持真实碰撞检测。
- 不支持 rosbag2 验收记录。

## Fake 语义说明

`fake_arm_control` 只接受固定命名目标并返回成功/失败结果，不产生真实轨迹。

`fake_hand_control` 只接受 `open`、`preshape`、`close`、`hold`、`release`
高层命令，不控制 RH56DFX-2R 的真实手指关节。

`fake_scene_manager` 使用逻辑状态表示物体位置和附着关系：

```text
pickup_zone -> attached -> place_zone
```

这不是物理接触，也不是仿真碰撞结果。

`fake_terminal_operation` 的 `PLACE` 只是末端操作占位，用于把任务结构从
Pick-and-Place 过渡到未来的装配任务。`INSERT`、孔轴对准、插入搜索和
卡阻恢复都不属于 MVP-1。

## 后续演进方向

MVP-2 重点是把 fake arm 能力替换为 RViz / MoveIt / MTC 中的单 FR3
规划执行，同时尽量保持 `StartTask`、`TaskState` 和任务状态机语义稳定。

MVP-3 重点是进入 MuJoCo 或等价物理仿真，验证关节控制、场景重置和物体
状态同步。

真实硬件、双臂、灵巧手精细操作和 Peg-in-Hole 属于 Post-MVP 或后续研究
支线，不作为 MVP-1 冻结标准。
