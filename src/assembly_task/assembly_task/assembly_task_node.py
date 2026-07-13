"""MVP-1 最小任务编排节点。"""

import threading
import time
from pathlib import Path

import yaml
import rclpy
from ament_index_python.packages import get_package_share_directory
from assembly_interfaces.action import MoveArm
from assembly_interfaces.msg import TaskState
from assembly_interfaces.srv import AttachObject
from assembly_interfaces.srv import ControlHand
from assembly_interfaces.srv import DetachObject
from assembly_interfaces.srv import ExecuteTerminalOperation
from assembly_interfaces.srv import GetObjectPose
from assembly_interfaces.srv import ResetScene
from assembly_interfaces.srv import StartTask
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class AssemblyTaskNode(Node):
    """串联各个任务节点的最小任务节点。"""

    # 类属性：属于“这个类本身”，所有对象共享，适合放固定配置、常量。
    START_TASK_SERVICE = '/assembly/start_task'
    RESET_SCENE_SERVICE = '/assembly/reset_scene'
    MOVE_ARM_ACTION = '/assembly/move_arm'
    TASK_STATE_TOPIC = '/assembly/task_state'
    CONTROL_HAND_CLIENT = '/assembly/control_hand'
    ATTACH_OBJECT_CLIENT = '/assembly/attach_object'
    DETACH_OBJECT_CLIENT = '/assembly/detach_object'
    GET_OBJECT_POSE_CLIENT = '/assembly/get_object_pose'
    EXECUTE_TERMINAL_OPERATION_CLIENT = '/assembly/execute_terminal_operation'

    MVP0_HOME = 'mvp0_home'
    PICK_AND_PLACE_MVP = 'pick_and_place_mvp'
    TARGET_NAME = 'home'
    TARGET_ARM_MODEL = 'Franka Research 3'
    TARGET_HAND_MODEL = '因时 RH56DFX-2R'

    # error code
    EMPTY_TASK_NAME_ERROR = 3001
    UNSUPPORTED_TASK_NAME_ERROR = 3002
    TASK_ALREADY_RUNNING_ERROR = 3003
    RESET_SCENE_UNAVAILABLE_ERROR = 3101
    MOVE_ARM_UNAVAILABLE_ERROR = 3201
    CONTROL_HAND_UNAVAILABLE_ERROR = 7001
    SCENE_OBJECT_UNAVAILABLE_ERROR = 7002
    TERMINAL_OPERATION_UNAVAILABLE_ERROR = 7003

    def __init__(self):
        """
        初始化任务编排节点和所需 ROS 通信接口。
            将会初始化诸多接口,并做合法性校验：

        """
        super().__init__('assembly_task_node')

        # 构造函数初始化属性：每个对象各有一份。
        self._task_counter = 0
        self._state_lock = threading.Lock()  # 状态互斥锁
        self._current_state = 'IDLE'  # 空闲
        self._previous_state = ''
        self._active_task_id = None

        # 读取 config 配置的 yaml
        self._mvp1_config = self._load_mvp1_config()
        self._task_config = self._mvp1_config['task']
        self._arm_targets = self._mvp1_config['arm_targets']
        self._hand_commands = self._mvp1_config['hand_commands']
        self._timeouts = self._mvp1_config['timeouts']
        self._grasp_config = self._mvp1_config['grasp']
        self._mvp1_task_name = self._task_config.get(
            'name',
            self.PICK_AND_PLACE_MVP,
        )
        self._supported_task_names = [
            self.MVP0_HOME,
            self._mvp1_task_name,
        ]

        # 初始化 ROS2 接口
        # StartTask service
        self._start_task_service = self.create_service(
            StartTask,
            self.START_TASK_SERVICE,
            self._handle_start_task,
        )

        # ResetScene client
        self._reset_scene_client = self.create_client(
            ResetScene,
            self.RESET_SCENE_SERVICE,
        )

        # ControlHand client
        self._control_hand_client = self.create_client(
            ControlHand,
            self.CONTROL_HAND_CLIENT)

        # AttachObject client
        self._attach_object_client = self.create_client(
            AttachObject,
            self.ATTACH_OBJECT_CLIENT)

        # DetachObject client
        self._detach_object_client = self.create_client(
            DetachObject,
            self.DETACH_OBJECT_CLIENT)

        # GetObjectPose client
        self._get_object_pose_client = self.create_client(
            GetObjectPose,
            self.GET_OBJECT_POSE_CLIENT)

        # ExecuteTerminalOperation client
        self._execute_terminal_operation_client = self.create_client(
            ExecuteTerminalOperation,
            self.EXECUTE_TERMINAL_OPERATION_CLIENT)

        # MoveArm action client
        self._move_arm_action_client = ActionClient(
            self,
            MoveArm,
            self.MOVE_ARM_ACTION,
        )

        # TaskState publisher
        self._task_state_publisher = self.create_publisher(
            TaskState,
            self.TASK_STATE_TOPIC,
            10,
        )

        self.get_logger().info(
            'event=assembly_task_started '
            f'start_task_service={self.START_TASK_SERVICE!r} '
            f'reset_scene_service={self.RESET_SCENE_SERVICE!r} '
            f'control_hand_client={self.CONTROL_HAND_CLIENT!r} '
            f'attach_object_client={self.ATTACH_OBJECT_CLIENT!r} '
            f'detach_object_client={self.DETACH_OBJECT_CLIENT!r} '
            f'get_object_pose_client={self.GET_OBJECT_POSE_CLIENT!r} '
            f'execute_terminal_operation_client={self.EXECUTE_TERMINAL_OPERATION_CLIENT!r} '
            f'move_arm_action={self.MOVE_ARM_ACTION!r} '
            f'task_state_topic={self.TASK_STATE_TOPIC!r} '
            f'target_arm={self._task_config["arm_name"]!r} '
            f'target_arm_model={self.TARGET_ARM_MODEL!r} '
            f'target_hand_model={self.TARGET_HAND_MODEL!r}'
        )

    def _handle_start_task(self, request, response):
        """校验 StartTask 请求，接受合法任务，并启动后台执行流程。"""
        task_name = request.task_name.strip()
        self.get_logger().info(
            f'event=start_task_request task_name={task_name!r}'
        )

        if not task_name:
            response.accepted = False
            response.task_id = ''
            response.error_code = self.EMPTY_TASK_NAME_ERROR
            response.message = 'task_name must not be empty'
            return response

        if task_name not in self._supported_task_names:
            response.accepted = False
            response.task_id = ''
            response.error_code = self.UNSUPPORTED_TASK_NAME_ERROR
            response.message = 'unsupported task_name'
            return response

        with self._state_lock:
            if self._active_task_id is not None:
                response.accepted = False
                response.task_id = ''
                response.error_code = self.TASK_ALREADY_RUNNING_ERROR
                response.message = 'another task is already running'
                return response

            self._task_counter += 1
            task_id = f'mvp0_task_{self._task_counter:04d}'
            self._active_task_id = task_id

        response.accepted = True
        response.task_id = task_id
        response.error_code = 0
        response.message = 'Task accepted'

        # 创建一个后台线程，并让任务在后台执行。
        task_thread = threading.Thread(
            target=self._run_task_safely,
            args=(task_id, task_name),
            daemon=True,  # 表示这是一个守护线程。主程序退出时，这个后台线程不会阻止程序退出。
        )
        task_thread.start()

        self.get_logger().info(
            'event=start_task_response '
            f'task_id={task_id!r} accepted={response.accepted} '
            f'error_code={response.error_code} '
            f'message={response.message!r}'
        )
        return response

    def _run_task_safely(self, task_id, task_name):
        """执行任务，并在结束后释放并发保护。"""
        try:
            self._run_task(task_id, task_name)
        finally:
            with self._state_lock:
                if self._active_task_id == task_id:
                    self._active_task_id = None

    def _load_mvp1_config(self):
        """从安装后的 share 目录读取 MVP-1 Pick-and-Place 配置。"""
        package_share = get_package_share_directory('assembly_task')
        config_path = Path(package_share) / 'config' / 'mvp1_pick_and_place.yaml'

        with config_path.open('r', encoding='utf-8') as config_file:
            return yaml.safe_load(config_file)

    def _run_task(self, task_id, task_name):
        """按固定顺序执行最小任务链路。"""
        # 分支1：mvp-0
        if task_name == self.MVP0_HOME:
            previous_state = 'IDLE'
            previous_state = self._publish_task_state(
                task_id,
                'RESETTING',
                previous_state,
                0.2,
                0,
                'Resetting scene',
            )

            success, error_code, message = self._call_reset_scene(task_id)
            if not success:
                self._publish_task_state(
                    task_id,
                    'FAILED',
                    previous_state,
                    0.2,
                    error_code,
                    message,
                )
                return

            previous_state = self._publish_task_state(
                task_id,
                'ARM_HOME',
                previous_state,
                0.6,
                0,
                'Moving right_arm to home',
            )

            success, error_code, message = self._call_move_arm_target(
                self.TARGET_NAME
            )
            if not success:
                self._publish_task_state(
                    task_id,
                    'FAILED',
                    previous_state,
                    0.6,
                    error_code,
                    message,
                )
                return

            self._publish_task_state(
                task_id,
                'SUCCESS',
                previous_state,
                1.0,
                0,
                'Task completed successfully',
            )

        # 分支2：mvp-1
        if task_name == self._mvp1_task_name:
            previous_state = 'IDLE'

            pick_and_place_steps = [
                (
                    'RESETTING',
                    0.06,
                    'Resetting scene',
                    lambda: self._call_reset_scene(task_id),
                ),
                (
                    'ARM_HOME',
                    0.12,
                    'Moving right_arm to home',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['home'],
                    ),
                ),
                (
                    'HAND_OPEN',
                    0.18,
                    'Opening right_hand',
                    lambda: self._call_control_hand(
                        self._hand_commands['open'],
                    ),
                ),
                (
                    'ARM_PREGRASP',
                    0.24,
                    'Moving right_arm to pregrasp',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['pregrasp'],
                    ),
                ),
                (
                    'HAND_PRESHAPE',
                    0.30,
                    'Preshaping right_hand',
                    lambda: self._call_control_hand(
                        self._hand_commands['preshape'],
                    ),
                ),
                (
                    'ARM_GRASP',
                    0.36,
                    'Moving right_arm to grasp',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['grasp'],
                    ),
                ),
                (
                    'HAND_CLOSE',
                    0.42,
                    'Closing right_hand',
                    lambda: self._call_control_hand(
                        self._hand_commands['close'],
                    ),
                ),
                (
                    'ATTACH_OBJECT',
                    0.48,
                    f'Attaching {self._task_config["object_id"]} '
                    f'to {self._task_config["hand_name"]}',
                    lambda: self._call_attach_object(task_id),
                ),
                (
                    'ARM_LIFT',
                    0.54,
                    'Moving right_arm to lift',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['lift'],
                    ),
                ),
                (
                    'ARM_PREPLACE',
                    0.60,
                    'Moving right_arm to preplace',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['preplace'],
                    ),
                ),
                (
                    'ARM_PLACE',
                    0.66,
                    'Moving right_arm to place',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['place'],
                    ),
                ),
                (
                    'TERMINAL_PLACE',
                    0.72,
                    'Executing terminal PLACE operation',
                    lambda: self._call_terminal_place(task_id),
                ),
                (
                    'DETACH_OBJECT',
                    0.78,
                    f'Detaching {self._task_config["object_id"]} '
                    f'to {self._task_config["target_location"]}',
                    lambda: self._call_detach_object(task_id),
                ),
                (
                    'HAND_OPEN',
                    0.84,
                    'Opening right_hand',
                    lambda: self._call_control_hand(
                        self._hand_commands['open'],
                    ),
                ),
                (
                    'ARM_RETREAT',
                    0.90,
                    'Moving right_arm to retreat',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['retreat'],
                    ),
                ),
                (
                    'ARM_HOME',
                    0.96,
                    'Moving right_arm to home',
                    lambda: self._call_move_arm_target(
                        self._arm_targets['home'],
                    ),
                ),
            ]

            for current_state, progress, message, step_call in pick_and_place_steps:
                success, previous_state = self._run_step(
                    task_id,
                    previous_state,
                    current_state,
                    progress,
                    message,
                    step_call,
                )
                if not success:
                    return

            self._publish_task_state(
                task_id,
                'SUCCESS',
                previous_state,
                1.0,
                0,
                'Task completed successfully',
            )

    def _run_step(
        self,
        task_id,
        previous_state,
        current_state,
        progress,
        message,
        step_call,
    ):
        """发布一个状态，执行对应动作；失败时统一进入 FAILED。"""
        previous_state = self._publish_task_state(
            task_id,
            current_state,
            previous_state,
            progress,
            0,
            message,
        )

        success, error_code, result_message = step_call()
        if not success:
            self._publish_task_state(
                task_id,
                'FAILED',
                previous_state,
                progress,
                error_code,
                result_message,
            )
            return False, previous_state

        return True, previous_state

    def _publish_task_state(
        self,
        task_id,
        current_state,
        previous_state,
        progress,
        error_code,
        message,
    ):
        """发布任务状态，并返回当前状态供下一次状态转换使用。"""
        with self._state_lock:
            self._previous_state = previous_state
            self._current_state = current_state

        state_msg = TaskState()
        state_msg.task_id = task_id
        state_msg.current_state = current_state
        state_msg.previous_state = previous_state
        state_msg.progress = progress
        state_msg.error_code = error_code
        state_msg.message = message
        self._task_state_publisher.publish(state_msg)

        self.get_logger().info(
            'event=task_state '
            f'task_id={task_id!r} '
            f'previous_state={previous_state!r} '
            f'current_state={current_state!r} '
            f'progress={progress} '
            f'error_code={error_code} '
            f'message={message!r}'
        )
        return current_state

    def _call_reset_scene(self, task_id):
        """调用 Fake Scene Manager 的 ResetScene 服务。"""
        if not self._reset_scene_client.wait_for_service(timeout_sec=2.0):
            return (
                False,
                self.RESET_SCENE_UNAVAILABLE_ERROR,
                'reset_scene service not available',
            )

        request = ResetScene.Request()
        request.task_id = task_id

        # 已经发出请求了，异步等待
        future = self._reset_scene_client.call_async(request)

        if not self._wait_for_future(
            future,
            timeout_sec=self._timeouts['scene_operation_sec'],
        ):
            return (
                False,
                self.RESET_SCENE_UNAVAILABLE_ERROR,
                'reset_scene service call timed out',
            )

        result = future.result()
        if result is None:
            return (
                False,
                self.RESET_SCENE_UNAVAILABLE_ERROR,
                'reset_scene service returned no response',
            )

        return result.success, result.error_code, result.message

    def _call_move_arm_target(self, target_name):
        """调用 Fake Arm Control 的 MoveArm Action。"""
        if not self._move_arm_action_client.wait_for_server(timeout_sec=2.0):
            return (
                False,
                self.MOVE_ARM_UNAVAILABLE_ERROR,
                'move_arm action server not available',
            )

        goal = MoveArm.Goal()
        goal.arm_name = self._task_config['arm_name']
        goal.target_name = target_name
        goal.timeout_sec = self._timeouts['move_arm_sec']

        send_goal_future = self._move_arm_action_client.send_goal_async(
            goal,
            feedback_callback=self._handle_move_arm_feedback,
        )
        if not self._wait_for_future(
            send_goal_future,
            timeout_sec=self._timeouts['move_arm_sec'],
        ):
            return (
                False,
                self.MOVE_ARM_UNAVAILABLE_ERROR,
                'move_arm send goal timed out',
            )

        goal_handle = send_goal_future.result()
        if goal_handle is None or not goal_handle.accepted:
            return (
                False,
                self.MOVE_ARM_UNAVAILABLE_ERROR,
                'move_arm goal was rejected',
            )

        result_future = goal_handle.get_result_async()
        if not self._wait_for_future(
            result_future,
            timeout_sec=self._timeouts['move_arm_sec'],
        ):
            return (
                False,
                self.MOVE_ARM_UNAVAILABLE_ERROR,
                'move_arm result timed out',
            )

        action_result = result_future.result()
        if action_result is None:
            return (
                False,
                self.MOVE_ARM_UNAVAILABLE_ERROR,
                'move_arm returned no result',
            )

        result = action_result.result
        return result.success, result.error_code, result.message

    def _call_control_hand(self, command):
        """调用 Fake Hand Control 的 ControlHand 服务。"""
        if not self._control_hand_client.wait_for_service(timeout_sec=2.0):
            return (
                False,
                self.CONTROL_HAND_UNAVAILABLE_ERROR,
                'control_hand service not available',
            )

        request = ControlHand.Request()
        request.hand_name = self._task_config['hand_name']
        request.command = command
        request.grasp_name = self._grasp_config['name']
        request.timeout_sec = self._timeouts['control_hand_sec']

        future = self._control_hand_client.call_async(request)

        if not self._wait_for_future(
            future,
            timeout_sec=self._timeouts['control_hand_sec'],
        ):
            return (
                False,
                self.CONTROL_HAND_UNAVAILABLE_ERROR,
                'control_hand service call timed out',
            )

        result = future.result()
        if result is None:
            return (
                False,
                self.CONTROL_HAND_UNAVAILABLE_ERROR,
                'control_hand service returned no response',
            )

        return result.success, result.error_code, result.message

    def _call_attach_object(self, task_id):
        """调用 Fake Scene Manager 的 AttachObject 服务。"""
        if not self._attach_object_client.wait_for_service(timeout_sec=2.0):
            return (
                False,
                self.SCENE_OBJECT_UNAVAILABLE_ERROR,
                'attach_object service not available',
            )

        request = AttachObject.Request()
        request.task_id = task_id
        request.object_id = self._task_config['object_id']
        request.link_name = self._task_config['hand_name']

        future = self._attach_object_client.call_async(request)

        if not self._wait_for_future(
            future,
            timeout_sec=self._timeouts['scene_operation_sec'],
        ):
            return (
                False,
                self.SCENE_OBJECT_UNAVAILABLE_ERROR,
                'attach_object service call timed out',
            )

        result = future.result()
        if result is None:
            return (
                False,
                self.SCENE_OBJECT_UNAVAILABLE_ERROR,
                'attach_object service returned no response',
            )

        return result.success, result.error_code, result.message

    def _call_detach_object(self, task_id):
        """调用 Fake Scene Manager 的 DetachObject 服务。"""
        if not self._detach_object_client.wait_for_service(timeout_sec=2.0):
            return (
                False,
                self.SCENE_OBJECT_UNAVAILABLE_ERROR,
                'detach_object service not available',
            )

        request = DetachObject.Request()
        request.task_id = task_id
        request.object_id = self._task_config['object_id']
        request.target_location = self._task_config['target_location']

        future = self._detach_object_client.call_async(request)

        if not self._wait_for_future(
            future,
            timeout_sec=self._timeouts['scene_operation_sec'],
        ):
            return (
                False,
                self.SCENE_OBJECT_UNAVAILABLE_ERROR,
                'detach_object service call timed out',
            )

        result = future.result()
        if result is None:
            return (
                False,
                self.SCENE_OBJECT_UNAVAILABLE_ERROR,
                'detach_object service returned no response',
            )

        return result.success, result.error_code, result.message

    def _call_terminal_place(self, task_id):
        """调用 Fake Terminal Operation 的 PLACE 服务。"""
        if not self._execute_terminal_operation_client.wait_for_service(
            timeout_sec=2.0,
        ):
            return (
                False,
                self.TERMINAL_OPERATION_UNAVAILABLE_ERROR,
                'execute_terminal_operation service not available',
            )

        request = ExecuteTerminalOperation.Request()
        request.task_id = task_id
        request.operation_type = self._task_config['terminal_operation']
        request.object_id = self._task_config['object_id']
        request.target_location = self._task_config['target_location']
        request.timeout_sec = self._timeouts['terminal_operation_sec']

        future = self._execute_terminal_operation_client.call_async(request)

        if not self._wait_for_future(
            future,
            timeout_sec=self._timeouts['terminal_operation_sec'],
        ):
            return (
                False,
                self.TERMINAL_OPERATION_UNAVAILABLE_ERROR,
                'execute_terminal_operation service call timed out',
            )

        result = future.result()
        if result is None:
            return (
                False,
                self.TERMINAL_OPERATION_UNAVAILABLE_ERROR,
                'execute_terminal_operation service returned no response',
            )

        return result.success, result.error_code, result.message

    def _handle_move_arm_feedback(self, feedback_msg):
        """记录 MoveArm Action 的执行反馈。"""
        feedback = feedback_msg.feedback
        self.get_logger().info(
            'event=move_arm_feedback '
            f'current_state={feedback.current_state!r} '
            f'progress={feedback.progress}'
        )

    def _wait_for_future(self, future, timeout_sec):
        """等待异步调用完成；executor 仍由主线程 rclpy.spin 负责驱动。"""
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not future.done():
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)
        return future.done()


def main(args=None):
    """运行总体任务节点。"""
    rclpy.init(args=args)
    node = AssemblyTaskNode()

    try:
        rclpy.spin(node)
    except (ExternalShutdownException, KeyboardInterrupt):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
