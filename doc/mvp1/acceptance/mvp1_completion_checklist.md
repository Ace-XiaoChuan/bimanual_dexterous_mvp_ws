# MVP-1 完成清单

冻结版本：`mvp1.0.0`

当前状态：代码和验收回归已通过；冻结提交由 Git tag `mvp1.0.0` 定位。

MVP-1 的冻结目标是一条纯软件 fake 单臂 Pick-and-Place 闭环。它验证任务
编排、接口调用、状态发布、错误处理、逻辑物体附着/释放和自动化集成测试，
不声明真实 FR3、真实 RH56DFX-2R、MoveIt、MuJoCo 或航空插头插接能力。

## 完成项

- [x] `assembly_interfaces` 接口生成通过。
- [x] `fake_scene_manager` 支持 `reset_scene`、`attach_object`、
  `detach_object` 和 `get_object_pose`。
- [x] `fake_hand_control` 支持 `open`、`preshape`、`close`、`hold`
  和 `release` 高层命令。
- [x] `fake_terminal_operation` 支持 `operation_type = PLACE`。
- [x] `fake_arm_control` 支持 `home`、`pregrasp`、`grasp`、`lift`、
  `preplace`、`place` 和 `retreat` 命名目标。
- [x] `assembly_task` 支持 `task_name = "pick_and_place_mvp"`。
- [x] MVP-1 Pick-and-Place 状态机完成。
- [x] MVP-1 配置文件 `mvp1_pick_and_place.yaml` 接入。
- [x] MVP-1 launch 文件 `mvp1_fake_pick_place.launch.py` 完成。
- [x] MVP-1 集成测试覆盖成功链路。
- [x] MVP-0 `mvp0_home` 回归仍通过。
- [x] 空 `task_name` 和非法 `task_name` 会被拒绝。
- [x] 运行中任务会拒绝新的并发 `StartTask` 请求。
- [x] 连续 10 次 `pick_and_place_mvp` 自动化执行通过。
- [x] README 已更新 MVP-1 运行入口和验收入口。
- [x] 最终冻结 commit 已创建。
- [x] Git tag `mvp1.0.0` 已创建。

## 验收证据

详细构建和测试结果见：

```text
doc/mvp1/acceptance/build_and_test_result.md
```

接口快照见：

```text
doc/mvp1/acceptance/interface_snapshot.md
```

已知限制见：

```text
doc/mvp1/acceptance/known_limitations.md
```
