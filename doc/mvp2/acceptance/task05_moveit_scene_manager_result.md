# MVP-2 任务 05 验收记录：MoveIt 场景物体抓取与放置

## 验收结论

`moveit_scene_manager` 的 ResetScene、AttachObject 和 DetachObject 已在
官方 FR3 fake-hardware MoveIt 场景中完成服务级验收。

验证范围是 PlanningScene 的 world collision object 与 attached collision
object 转换；不包含真实抓取接触、夹爪闭合判断或滑移检测。

## 构建验证

```bash
cmake --build build/moveit_scene_manager --parallel 2
cmake --install build/moveit_scene_manager
```

结果：`moveit_scene_manager_node` 完成编译、链接和安装。

## 运行环境

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
export ROS_LOG_DIR=/tmp/bimanual_mvp2_scene_logs

ros2 launch franka_fr3_moveit_config moveit.launch.py \
  robot_ip:=dont-care \
  use_fake_hardware:=true \
  fake_sensor_commands:=true

ros2 run moveit_scene_manager moveit_scene_manager_node
```

运行时可见的关键节点和服务包括：

```text
/move_group
/rviz2
/moveit_scene_manager_node
/apply_planning_scene
/get_planning_scene
/assembly/reset_scene
/assembly/attach_object
/assembly/detach_object
```

本次使用官方模型中的 `fr3_hand` 作为 AttachObject 的 `link_name`。它是
真实 MoveIt robot model 的 link；MVP-1 的逻辑名称 `right_hand` 不用于本次
MoveIt 场景验证。

## 服务与场景验证

### ResetScene

```bash
ros2 service call /assembly/reset_scene assembly_interfaces/srv/ResetScene \
  "{task_id: mvp2_scene_acceptance}"
```

结果：

```text
success=True
error_code=0
message='mvp_object reset to pickup_zone'
```

随后读取 `/get_planning_scene`（world object geometry 和 attached object
components）确认：

```text
attached_collision_objects=[]
world.collision_objects contains mvp_object
world pose=(0.45, 0.00, 0.15)
box dimensions=(0.05, 0.05, 0.05)
```

### AttachObject

```bash
ros2 service call /assembly/attach_object assembly_interfaces/srv/AttachObject \
  "{task_id: mvp2_scene_acceptance, object_id: mvp_object, link_name: fr3_hand}"
```

结果：

```text
success=True
error_code=0
message='mvp_object attached successfully'
```

读取 PlanningScene 确认：

```text
attached_collision_objects contains mvp_object
attached link_name=fr3_hand
world.collision_objects=[]
```

重复调用相同 AttachObject：

```text
success=False
error_code=5003
message='object is already attached'
```

### DetachObject

```bash
ros2 service call /assembly/detach_object assembly_interfaces/srv/DetachObject \
  "{task_id: mvp2_scene_acceptance, object_id: mvp_object, target_location: place_zone}"
```

结果：

```text
success=True
error_code=0
message='mvp_object detached successfully'
```

读取 PlanningScene 确认：

```text
attached_collision_objects=[]
world.collision_objects contains mvp_object
world pose=(0.45, -0.20, 0.15)
```

该固定 world pose 是当前 MVP-2 对逻辑 `place_zone` 的物理映射。

再次调用 DetachObject：

```text
success=False
error_code=5004
message='object is not attached'
```

## RViz 状态与剩余项

官方 MoveIt launch 已启动 `/rviz2`，其日志显示已连接
`/monitored_planning_scene`，因此上述 PlanningScene 更新会发布给 RViz。

本记录不把节点存在和场景服务查询替代为人工视觉证据。仍需用户在该 RViz
窗口中确认物体可见、Attach 后随 `fr3_hand` 显示、Detach 后显示在
`place_zone`。完成该确认后，任务 05 的 RViz 可视验收可标记完成。

`GetObjectPose` 和 MVP-2 一键系统 launch 分别属于后续接口完善和任务 07，
不阻塞本任务的 PlanningScene 服务级验收。

## 测试工具环境说明

`ctest --test-dir build/moveit_scene_manager --output-on-failure` 已被执行，
但本机的 ament lint runner 缺少 `ament_cmake_test` Python package metadata，
四项 lint 均在启动前失败。该问题不影响上述已完成的 C++ 编译和运行时服务
验收；在 MVP-2 收尾冻结前需要修复该工具环境并重跑 lint。
