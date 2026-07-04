# MVP-2 第四阶段：PlanningScene 物体接入

## 1. 工作目标

把 MVP-1 中的 fake object 映射为 MoveIt PlanningScene 中的 collision object。

本阶段只处理规划场景几何对象，不做物理接触仿真。

## 2. 推荐能力

```text
ResetScene 后添加 mvp_object
object 初始位置映射到 pickup_zone
重复 reset 不产生重复 object
object pose / location 可通过日志或测试确认
```

## 3. 与 fake_scene_manager 的关系

MVP-2 可以先复用 `fake_scene_manager` 的 service 语义，但内部实现需要逐步接入
MoveIt PlanningScene。

推荐保持接口：

```text
ResetScene
GetObjectPose
AttachObject
DetachObject
```

## 4. 验收标准

```text
RViz PlanningScene 中可见 mvp_object
ResetScene 后 object 回到 pickup_zone
object 不重复叠加
日志可定位 object_id 和 object_location
```

## 5. 非目标

```text
不模拟真实接触
不计算真实物体动力学
不做视觉定位
```
