# MVP-3 第二阶段：MuJoCo 场景与模型加载

## 1. 工作目标

建立最小 MuJoCo 场景，并在 headless 模式稳定加载 FR3、夹爪化 RH56、桌面和
connector plug/socket。模型加载先于 ROS 2 控制链路验证。

## 2. 场景组成

```text
world
table / fixture
FR3 arm
RH56 visual or gripper-preset model
connector plug: dynamic free body
connector socket: fixed world body
pickup_zone / place_zone marker or fixed reference frame
```

connector mesh 可以先复用：

```text
assets/meshes/connector_plug_visual.stl
assets/meshes/connector_socket_visual.stl
scale = 0.001
```

首轮 visual 和 collision 可使用同一简化 STL。正式接入前必须检查 socket 开口、
mesh 闭合性和尺度，而不是只检查三角形数量。

## 3. 模型边界

```text
FR3 关节范围、阻尼、执行器和 home keyframe 明确
RH56 不要求每根手指独立任务控制
plug 质量、惯量、碰撞体和初始 pose 明确
socket 只做固定场景物，不定义插接成功条件
```

STL 的几何中心不是功能坐标系。须在 MJCF 中显式定义 plug grasp frame、
pickup frame 和 place frame。

## 4. 验收标准

```text
mj_loadXML 或等价加载无错误
模型可至少运行固定数量 simulation steps
FR3、手部、table、plug 和 socket body 均可按名称查询
home / reset keyframe 可恢复确定初始 qpos 和 object pose
headless 模式不依赖 RViz 或 GUI
```

## 5. 非目标

```text
不做真实材料参数标定
不做插接容差或接触力阈值设计
不要求 RH56 多指碰撞抓取成功
```
