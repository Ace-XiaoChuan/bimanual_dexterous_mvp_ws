# MVP-0 Known Limitations

生成时间：2026-06-24 13:32:37 CST

最后更新：2026-06-24 14:59:29 HKT

基准 commit：`fcd7a22`

## 总体定位

MVP-0 是纯软件 fake 链路验证，不证明真实装配能力。它的目标是让 ROS 2
package、service、action、topic、launch 和集成测试形成一个可重复运行的最小
闭环。

## 当前限制

1. 不连接真实 Franka Research 3 机械臂。
2. 不连接真实因时 RH56DFX-2R 灵巧手。
3. 不加载真实硬件驱动、控制器或安全限制。
4. 不使用 MoveIt、MTC、ros2_control 或 MuJoCo。
5. 不执行真实 Pick-and-Place。
6. 不执行 Peg-in-Hole、接触建模、柔顺控制或力反馈。
7. `right_arm` 仅是逻辑名，当前由 fake action server 处理。
8. `right_hand` 仅做命名和硬件基线预留，MVP-0 不控制灵巧手。
9. 当前只支持一个任务名：`mvp0_home`。
10. 当前只支持一个机械臂目标：`right_arm -> home`。
11. `task_id` 是进程内递增编号，节点重启后会从初始计数重新开始。
12. `StartTask` 接受任务后在后台线程执行；MVP-0 没有任务取消、暂停、恢复或查询接口。
13. MVP-0 没有持久化任务数据库或实验记录系统。
14. 集成测试覆盖连续 10 次合法任务，但不是压力测试或长时间稳定性测试。
15. 当前自动化测试覆盖成功链路和非法任务名，不覆盖所有底层依赖失败组合。

## 已降级的失败注入测试

MVP-0 总体任务说明中已将以下专项测试降级为后续增强验收项：

```text
未启动 ResetScene 时进入 FAILED
未启动 MoveArm 时进入 FAILED
```

原因：

- 当前 MVP-0 收尾优先冻结已经可运行的一键启动和成功路径验收。
- 任务层代码保留 ResetScene 和 MoveArm 不可用时发布 `FAILED` 的处理路径。
- 对缺失依赖进行自动化失败注入需要额外 launch/test 编排，适合在后续测试能力提升时补充。

该降级不改变 MVP-0 的运行范围：MVP-0 仍要求失败时有错误码、状态和日志路径，
但不把这两个专项自动化用例作为阶段 6 完成阻塞项。

## ROS 2 发现与 daemon

部分环境中可能出现普通 `ros2 service call` 等待 service，而 `--no-daemon`
可以看到节点和 service 的情况。这通常与 ROS 2 daemon 缓存或发现状态有关。

排查方式已记录在 `doc/mvp0/tasks/00_MVP0_总体任务说明.md`：

```bash
ros2 daemon stop
ros2 node list --no-daemon --spin-time 5
ros2 service list --no-daemon --spin-time 5
```

## 版本标签

干净环境回归已经通过，冻结版本标签为 `mvp0.0.0`。

## 后续建议

MVP-1 可在此基础上扩展 Fake 单臂 + 夹爪化末端 Pick-and-Place，但仍建议继续
保持单臂、纯软件和可自动化测试的约束，避免过早引入真实硬件、双臂协同或
复杂接触任务。
