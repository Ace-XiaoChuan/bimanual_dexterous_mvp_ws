# MVP-0 第三阶段工作说明：Fake Scene Manager

## 1. 工作目标

在 `fake_scene_manager` 软件包中实现第一个可运行的 Fake Server：

```text
ResetScene Service Server
```

该节点接收场景重置请求，更新内部模拟状态并返回结果。

本阶段完成后，项目将从“只有接口定义”进入“具有可调用执行节点”的阶段。

## 2. 本阶段范围

实现：

```text
节点：fake_scene_manager_node
服务：/assembly/reset_scene
接口：assembly_interfaces/srv/ResetScene
```

暂不实现：

```text
AttachObject
DetachObject
物理仿真
PlanningScene
MuJoCo
物体模型
碰撞检测
失败注入
```

## 3. 内部场景状态

节点维护以下最小状态：

```text
scene_initialized
object_exists
object_attached
attached_link
object_location
```

初始状态建议为：

```text
scene_initialized = false
object_exists = false
object_attached = false
attached_link = ""
object_location = "unknown"
```

收到合法的 `ResetScene` 请求后，状态更新为：

```text
scene_initialized = true
object_exists = true
object_attached = false
attached_link = ""
object_location = "initial"
```

## 4. 服务处理规则

请求包含：

```text
task_id
```

处理流程：

```text
接收请求
→ 检查 task_id
→ 重置内部场景状态
→ 输出结构化日志
→ 返回成功结果
```

成功响应：

```text
success = true
error_code = 0
message = "Scene reset successfully"
```

当 `task_id` 为空时，建议返回：

```text
success = false
error_code = 1001
message = "task_id must not be empty"
```

本阶段只设置一个错误码，不建立完整错误码系统。

## 5. 文件修改范围

主要修改：

```text
fake_scene_manager/
├── fake_scene_manager/
│   ├── __init__.py
│   └── fake_scene_manager_node.py
├── resource/
│   └── fake_scene_manager
├── package.xml
├── setup.cfg
└── setup.py
```

在 `setup.py` 中注册可执行入口：

```text
fake_scene_manager_node
```

节点应通过以下命令启动：

```bash
ros2 run fake_scene_manager fake_scene_manager_node
```

## 6. 验证流程

### 终端一：启动服务节点

```bash
cd ~/bimanual_dexterous_mvp_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run fake_scene_manager fake_scene_manager_node
```

### 终端二：确认服务存在

```bash
source /opt/ros/humble/setup.bash
source ~/bimanual_dexterous_mvp_ws/install/setup.bash

ros2 service list | grep reset_scene
ros2 service type /assembly/reset_scene
```

预期服务类型：

```text
assembly_interfaces/srv/ResetScene
```

### 调用合法请求

```bash
ros2 service call \
  /assembly/reset_scene \
  assembly_interfaces/srv/ResetScene \
  "{task_id: 'test_task_001'}"
```

预期结果：

```text
success: true
error_code: 0
message: Scene reset successfully
```

### 调用非法请求

```bash
ros2 service call \
  /assembly/reset_scene \
  assembly_interfaces/srv/ResetScene \
  "{task_id: ''}"
```

预期结果：

```text
success: false
error_code: 1001
message: task_id must not be empty
```

## 7. 验收标准

以下条件全部满足后，本阶段完成：

1. `fake_scene_manager` 可以成功编译；
2. 节点可以通过 `ros2 run` 启动；
3. `/assembly/reset_scene` 服务可以被发现；
4. 服务类型正确；
5. 合法请求返回成功；
6. 空 `task_id` 请求返回失败；
7. 每次请求都有日志；
8. 连续调用多次不会崩溃；
9. 重置后内部状态保持一致；
10. 不依赖 MoveIt、MuJoCo 或真实硬件。

## 8. 回归编译

```bash
cd ~/bimanual_dexterous_mvp_ws

source /opt/ros/humble/setup.bash

colcon build --symlink-install
source install/setup.bash
```

确保完整工作区仍然能够正常编译。

## 9. Git 提交

```bash
git status
git add src/fake_scene_manager
git commit -m "feat: implement fake scene reset service"
git push
```

该提交形成项目的第一版 Fake Server 基线。

## 10. 下一阶段入口

完成 Fake Scene Manager 后，第四阶段实现：

```text
Fake Arm MoveArm Action Server
```

它只需支持：

```text
right_arm
home
```

其中 `right_arm` 是逻辑名，在当前硬件基线中映射到首个或右侧
Franka Research 3；第四阶段仍然只实现 fake Action Server。

然后即可开始连接：

```text
StartTask
→ ResetScene
→ MoveArm(home)
→ SUCCESS
```
