# MVP-2 第五阶段：AttachedCollisionObject 抓取放置

## 1. 工作目标

把 MVP-1 中的逻辑 `AttachObject` / `DetachObject` 扩展为 MoveIt 中的
attached collision object 语义。

## 2. 推荐行为

AttachObject 后：

```text
object_attached = true
attached_link = 指定末端 link
PlanningScene 中 object 变为 attached object
```

DetachObject 后：

```text
object_attached = false
attached_link = ""
object_location = target_location
object 回到 PlanningScene
```

## 3. 验收标准

```text
AttachObject 后 RViz 中 object 跟随末端 link
DetachObject 后 object 回到 place_zone
重复 attach 返回明确错误
未 attach 时 detach 返回明确错误
TaskState 可观察 attach / detach 阶段
```

## 4. 非目标

```text
不做真实抓取接触检测
不根据夹爪闭合判断抓取成功
不做滑移检测
```
