# MVP-3 第七阶段：Pick-and-Place 任务编排接入

## 1. 工作目标

将 `assembly_task` 接入 MuJoCo 执行与对象状态同步，完成固定单臂 connector
plug Pick-and-Place 的仿真闭环。

## 2. 推荐成功路径

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
-> HAND_RELEASE
-> ARM_RETREAT
-> ARM_HOME
-> SUCCESS
```

每个状态必须等待对应 action/service 的完成结果和仿真状态确认，不能只以命令
发送成功作为下一状态的条件。

## 3. 接入原则

```text
StartTask / TaskState 接口保持不变
MoveArm 使用 MuJoCo execution adapter
ControlHand 使用仿真手部 preset
AttachObject / DetachObject 与 MuJoCo grasp-hold 和 object state 同步
PLACE 仍是放置语义，不代表 CONNECTOR_INSERT
```

## 4. 失败路径

```text
MuJoCo bridge unavailable -> FAILED
MoveArm plan / execute timeout -> FAILED
hand command or grasp-hold creation failed -> FAILED
object state mirror mismatch -> FAILED
reset failed or simulation clock stalled -> FAILED
```

失败后必须清理 active task、停止待执行轨迹、删除不应保留的 grasp constraint，并
发布带错误码的最终 `TaskState`。

## 5. 验收标准

```text
StartTask 可驱动完整 MuJoCo Pick-and-Place
每个关键 TaskState 可观测
plug 在 lift 阶段随手部移动，在 detach 后留在 place_zone
任一关键失败路径进入 FAILED 且下一次任务仍可启动
重复运行不死锁、不残留 constraint 或旧 object state
```

## 6. 非目标

```text
不做任务动态重排序
不做视觉抓取点生成
不做插接、力控或自动恢复策略
```
