# MVP-1 构建与测试结果

## 冻结信息

```text
冻结版本：mvp1.0.0
冻结提交：由 Git tag mvp1.0.0 指向；使用 git rev-parse mvp1.0.0^{commit} 查询
Git tag：mvp1.0.0
记录日期：2026-07-13
ROS 发行版：humble
Python 版本：Python 3.10.12
```

## 干净环境回归命令

```bash
cd /home/ace/bimanual_dexterous_mvp_ws
rm -rf build install log

unset CYCLONEDDS_URI
export ROS_LOCALHOST_ONLY=1
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOG_DIR=/tmp/bimanual_mvp1_ros_logs

source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

colcon test --event-handlers console_direct+
colcon test-result --verbose
```

## 构建结果

```text
命令：colcon build --symlink-install
结果：通过
摘要：Summary: 8 packages finished [2min 34s]
```

## 测试结果

```text
命令：colcon test --event-handlers console_direct+
结果：通过
摘要：Summary: 8 packages finished [3min 22s]
说明：5 packages had stderr output，内容为 pytest / ROS 运行期 warning，
      未产生 test failure。
```

`colcon test-result --verbose` 摘要：

```text
Summary: 57 tests, 0 errors, 0 failures, 8 skipped
```

关键集成测试：

```text
assembly_tests/mvp0_task_flow：通过，1 passed in 18.29s
assembly_tests/mvp1_pick_and_place_flow：通过，1 passed in 116.56s
```

## 失败项和处理方式

最终回归无失败项。

环境处理记录：

```text
当前交互 shell 原本带有 CYCLONEDDS_URI=file:///home/ace/cyclonedds.xml
和 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp。该组合在本机回归时无法枚举
网络接口，导致 rclpy 节点创建失败，测试尚未进入业务断言。

冻结回归改用本机测试环境：
unset CYCLONEDDS_URI
ROS_LOCALHOST_ONLY=1
RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ROS_LOG_DIR=/tmp/bimanual_mvp1_ros_logs
```

代码处理记录：

```text
1. assembly_task 增加运行中任务保护；已有任务执行时拒绝新的 StartTask。
2. assembly_tests 的 launch 清理改为清理整个进程组，避免 MVP-0 测试节点
   残留影响 MVP-1 集成测试。
```
