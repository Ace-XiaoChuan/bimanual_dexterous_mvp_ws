# MVP-2 第六阶段：Pick-and-Place 任务编排接入

## 1. 工作目标

让 `assembly_task` 在 MVP-2 中调用 MoveIt 适配后的 `MoveArm.action`，完成
固定单臂 Pick-and-Place 任务闭环。

## 2. 推荐状态机

```text
IDLE
-> RESETTING
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
-> TERMINAL_OPERATION_PLACE
-> ARM_RETREAT
-> ARM_HOME
-> SUCCESS
```

MVP-2 中 `fake_hand_control` 和 `fake_terminal_operation` 可以继续使用，重点替换
机械臂运动底层能力。

## 3. 验收标准

```text
StartTask(pick_and_place_mvp) 可触发完整流程
MoveArm 阶段由 MoveIt 执行
TaskState 能发布每个关键阶段
任一 MoveIt 规划或执行失败时进入 FAILED
重复执行不崩溃、不死锁
```

## 4. 非目标

```text
不新增复杂任务选择
不做动态抓取点生成
不做真实手部控制
```
