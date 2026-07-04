# MVP-2 第三阶段：MoveItArmControl 适配节点

## 1. 工作目标

新增 `moveit_arm_control`，让它对上继续提供 `MoveArm.action`，对下调用
MoveIt 2 完成 FR3 命名目标或位姿目标规划执行。

不要把 `fake_arm_control` 改造成 MoveIt 节点。MVP-1 fake 链路应继续保留。

## 2. 推荐接口

对上保持：

```text
assembly_interfaces/action/MoveArm.action
```

支持目标：

```text
home
pregrasp
grasp
lift
preplace
place
retreat
```

## 3. 错误处理建议

```text
不支持的 arm_name
不支持的 target_name
MoveIt 不可用
规划失败
执行失败
执行超时
```

错误码范围可在 MVP-2 第一阶段冻结。

## 4. 验收标准

```text
moveit_arm_control package 可构建
ros2 action list 可发现 MoveArm action
MoveArm(right_arm, home) 可驱动 MoveIt 规划执行
非法 target_name 返回明确失败
MoveIt 不可用时返回明确失败
```

## 5. 非目标

```text
不实现真实 FR3 FCI / libfranka 控制
不实现抓取规划
不实现碰撞物体 attach/detach
```
