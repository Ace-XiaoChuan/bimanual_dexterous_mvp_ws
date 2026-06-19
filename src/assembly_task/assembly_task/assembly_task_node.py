"""MVP-0 最小任务编排节点。"""

import threading
import time

import rclpy
from assembly_interfaces.action import MoveArm
from assembly_interfaces.msg import TaskState
from assembly_interfaces.srv import ResetScene
from assembly_interfaces.srv import StartTask
from rclpy.action import ActionClient
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class AssemblyTaskNode(Node):
    """串联 StartTask、ResetScene 和 MoveArm 的最小任务节点。"""

    # 类属性：属于“这个类本身”，所有对象共享，适合放固定配置、常量。
    START_TASK_SERVICE = '/assembly/start_task'
    RESET_SCENE_SERVICE = '/assembly/reset_scene'
    MOVE_ARM_ACTION = '/assembly/move_arm'
    TASK_STATE_TOPIC = '/assembly/task_state'

    SUPPORTED_TASK_NAME = 'mvp0_home'
    TARGET_ARM = 'right_arm'
    TARGET_NAME = 'home'
    MOVE_ARM_TIMEOUT_SEC = 5.0

    # error code
    EMPTY_TASK_NAME_ERROR = 3001
    UNSUPPORTED_TASK_NAME_ERROR = 3002
    RESET_SCENE_UNAVAILABLE_ERROR = 3101
    MOVE_ARM_UNAVAILABLE_ERROR = 3201

    def __init__(self):
        """初始化任务编排节点和所需 ROS 通信接口。"""
        super().__init__('assembly_task_node')

        # 构造函数里的属性：属于“某一个对象实例”，每个对象各有一份，适合放运行时状态和资源。
        self._task_counter = 0
        self._state_lock = threading.Lock() # 创建一个互斥锁
        self._current_state = 'IDLE' # 空闲
        self._previous_state = ''

        self._start_task_service = self.create_service(
            StartTask,
            self.START_TASK_SERVICE,
            self._handle_start_task,
        )
        self._reset_scene_client = self.create_client(
            ResetScene,
            self.RESET_SCENE_SERVICE,
        )
        self._move_arm_action_client = ActionClient(
            self,
            MoveArm,
            self.MOVE_ARM_ACTION,
        )
        self._task_state_publisher = self.create_publisher(
            TaskState,
            self.TASK_STATE_TOPIC,
            10,
        )

        self.get_logger().info(
            'event=assembly_task_started '
            f'start_task_service={self.START_TASK_SERVICE!r} '
            f'reset_scene_service={self.RESET_SCENE_SERVICE!r} '
            f'move_arm_action={self.MOVE_ARM_ACTION!r} '
            f'task_state_topic={self.TASK_STATE_TOPIC!r}'
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

        if task_name != self.SUPPORTED_TASK_NAME:
            response.accepted = False
            response.task_id = ''
            response.error_code = self.UNSUPPORTED_TASK_NAME_ERROR
            response.message = 'unsupported task_name'
            return response

        task_id = self._generate_task_id()
        response.accepted = True
        response.task_id = task_id
        response.error_code = 0
        response.message = 'Task accepted'

        task_thread = threading.Thread(
            target=self._run_task,
            args=(task_id,),
            daemon=True,
        )
        task_thread.start()

        self.get_logger().info(
            'event=start_task_response '
            f'task_id={task_id!r} accepted={response.accepted} '
            f'error_code={response.error_code} '
            f'message={response.message!r}'
        )
        return response

    def _generate_task_id(self):
        """生成 MVP-0 阶段使用的简单递增任务编号。"""
        with self._state_lock:
            self._task_counter += 1
            return f'mvp0_task_{self._task_counter:04d}'

    def _run_task(self, task_id):
        """按固定顺序执行最小任务链路。"""
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

        success, error_code, message = self._call_move_arm_home()
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
        future = self._reset_scene_client.call_async(request)

        if not self._wait_for_future(future, timeout_sec=5.0):
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

    def _call_move_arm_home(self):
        """调用 Fake Arm Control 的 MoveArm Action。"""
        if not self._move_arm_action_client.wait_for_server(timeout_sec=2.0):
            return (
                False,
                self.MOVE_ARM_UNAVAILABLE_ERROR,
                'move_arm action server not available',
            )

        goal = MoveArm.Goal()
        goal.arm_name = self.TARGET_ARM
        goal.target_name = self.TARGET_NAME
        goal.timeout_sec = self.MOVE_ARM_TIMEOUT_SEC

        send_goal_future = self._move_arm_action_client.send_goal_async(
            goal,
            feedback_callback=self._handle_move_arm_feedback,
        )
        if not self._wait_for_future(send_goal_future, timeout_sec=5.0):
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
        if not self._wait_for_future(result_future, timeout_sec=10.0):
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
