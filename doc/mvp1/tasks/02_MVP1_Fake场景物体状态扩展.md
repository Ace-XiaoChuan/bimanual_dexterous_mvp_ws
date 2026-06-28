# MVP-1 第二阶段：Fake 场景物体状态扩展

## 1. 工作目标

扩展 `fake_scene_manager`，让它不只会 reset scene，还能维护 MVP-1 所需的
物体 fake 状态。

本阶段重点验证：

```text
物体是否存在
物体当前逻辑位置
物体是否被附着
物体附着在哪个 link
reset / attach / detach 后状态是否正确变化
```

## 2. 本阶段范围

涉及软件包：

```text
fake_scene_manager
assembly_interfaces
assembly_tests
```

推荐实现接口：

```text
/assembly/get_object_pose
/assembly/attach_object
/assembly/detach_object
```

保留并扩展：

```text
/assembly/reset_scene
```

## 3. 状态模型

建议在 `fake_scene_manager_node` 中维护：

```text
scene_initialized: bool
object_exists: bool
object_attached: bool
attached_link: string
object_location: string
last_task_id: string
```

reset 后的初始状态：

```text
scene_initialized = true
object_exists = true
object_attached = false
attached_link = ""
object_location = "pickup_zone"
```

attach 后：

```text
object_attached = true
attached_link = link_name
object_location = "attached"
```

detach 后：

```text
object_attached = false
attached_link = ""
object_location = target_location
```

## 4. 错误处理

必须返回明确错误码：

```text
object_id 为空 -> 5001
object 不存在 -> 5002
attach 时已经附着 -> 5003
detach 时尚未附着 -> 5004
```

如果 `task_id` 为空，可以沿用 ResetScene 的风格返回明确错误。

## 5. 日志要求

每次状态变化至少记录：

```text
event
task_id
object_id
object_exists
object_attached
attached_link
object_location
success
error_code
message
```

## 6. 单模块验收

建议手动或测试验证：

```text
ResetScene -> object_location = pickup_zone
GetObjectPose -> success
AttachObject -> object_attached = true
GetObjectPose -> attached 状态可见
DetachObject -> object_attached = false
GetObjectPose -> object_location = place_zone
重复 attach 或错误 detach 返回错误码
```

## 7. 完成标准

```text
colcon build 通过
fake_scene_manager 单包测试通过
MVP-0 reset_scene 行为不回退
对象状态可被后续 assembly_task 和集成测试验证
```
