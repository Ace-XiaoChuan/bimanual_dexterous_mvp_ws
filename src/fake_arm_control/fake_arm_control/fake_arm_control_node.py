"""Fake 机械臂控制 Action 节点。"""

from dataclasses import dataclass
import time

import rclpy
from assembly_interfaces.action import MoveArm
from rclpy.action import ActionServer
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


@dataclass
class ArmState:
    """保存 MVP-0 使用的 Fake 机械臂最小状态。"""

    current_arm: str = ''
    current_target: str = 'unknown'
    is_moving: bool = False
    last_goal_success: bool = False
    last_error_code: int = 0
    last_message: str = ''

    def update_result(self, arm_name, target_name, success, error_code, message):
        """记录最近一次 MoveArm goal 的执行结果。"""
        self.current_arm = arm_name
        self.current_target = target_name
        self.is_moving = False
        self.last_goal_success = success
        self.last_error_code = error_code
        self.last_message = message

    def to_log_fields(self):
        """把当前状态拼成一段结构化日志文本，方便调试。"""
        return (
            f'current_arm={self.current_arm!r} '
            f'current_target={self.current_target!r} '
            f'is_moving={self.is_moving} '
            f'last_goal_success={self.last_goal_success} '
            f'last_error_code={self.last_error_code} '
            f'last_message={self.last_message!r}'
        )


class FakeArmControlNode(Node):
    """处理 MVP-0 阶段的 Fake 机械臂动作请求。"""

    ACTION_NAME = '/assembly/move_arm'
    SUPPORTED_ARM = 'right_arm'
    SUPPORTED_TARGET = 'home'
    HARDWARE_ARM_MODEL = 'Franka Research 3'
    HARDWARE_HAND_MODEL = '因时 RH56DFTP-2R'

    UNSUPPORTED_ARM_ERROR = 2001
    UNSUPPORTED_TARGET_ERROR = 2002
    INVALID_TIMEOUT_ERROR = 2003

    def __init__(self):
        """初始化假机械臂节点和 MoveArm Action Server。"""
        super().__init__('fake_arm_control_node')

        self._arm_state = ArmState()
        self._move_arm_action_server = ActionServer(
            self,
            MoveArm,
            self.ACTION_NAME,
            self._execute_move_arm,
        )
        self.get_logger().info(
            'event=fake_arm_control_started '
            f'action={self.ACTION_NAME!r} '
            f'supported_arm={self.SUPPORTED_ARM!r} '
            f'hardware_arm_model={self.HARDWARE_ARM_MODEL!r} '
            f'paired_hand_model={self.HARDWARE_HAND_MODEL!r} '
            f'{self._arm_state.to_log_fields()}'
        )

    def _execute_move_arm(self, goal_handle):
        """执行 Fake MoveArm action，并返回业务层面的执行结果。"""
        request = goal_handle.request
        self.get_logger().info(
            'event=move_arm_goal_received '
            f'arm_name={request.arm_name!r} '
            f'target_name={request.target_name!r} '
            f'timeout_sec={request.timeout_sec}'
        )

        result = self._validate_request(request)
        if result is not None:
            self._finish_goal(goal_handle, request, result)
            return result

        self._arm_state.is_moving = True
        self._publish_feedback(goal_handle, 'accepted', 0.0)
        time.sleep(0.5)

        self._publish_feedback(goal_handle, 'moving', 0.5)
        time.sleep(0.5)

        result = MoveArm.Result()
        result.success = True
        result.error_code = 0
        result.message = 'Arm moved to home successfully'

        self._publish_feedback(goal_handle, 'succeeded', 1.0)
        self._finish_goal(goal_handle, request, result)
        return result

    def _validate_request(self, request):
        """校验 goal 请求；合法时返回 None，非法时返回失败结果。"""
        if request.timeout_sec <= 0.0:
            return self._make_result(
                False,
                self.INVALID_TIMEOUT_ERROR,
                'timeout_sec must be positive',
            )

        if request.arm_name != self.SUPPORTED_ARM:
            return self._make_result(
                False,
                self.UNSUPPORTED_ARM_ERROR,
                'unsupported arm_name',
            )

        if request.target_name != self.SUPPORTED_TARGET:
            return self._make_result(
                False,
                self.UNSUPPORTED_TARGET_ERROR,
                'unsupported target_name',
            )

        return None

    def _publish_feedback(self, goal_handle, current_state, progress):
        """向当前 goal 发布执行进度反馈。"""
        feedback = MoveArm.Feedback()
        feedback.current_state = current_state
        feedback.progress = progress
        goal_handle.publish_feedback(feedback)
        self.get_logger().info(
            'event=move_arm_feedback '
            f'current_state={current_state!r} progress={progress}'
        )

    def _finish_goal(self, goal_handle, request, result):
        """记录结果、输出日志，并结束当前 goal。"""
        self._arm_state.update_result(
            request.arm_name,
            request.target_name,
            result.success,
            result.error_code,
            result.message,
        )
        goal_handle.succeed()
        self.get_logger().info(
            'event=move_arm_result '
            f'arm_name={request.arm_name!r} '
            f'target_name={request.target_name!r} '
            f'timeout_sec={request.timeout_sec} '
            f'success={result.success} '
            f'error_code={result.error_code} '
            f'message={result.message!r} '
            f'{self._arm_state.to_log_fields()}'
        )

    def _make_result(self, success, error_code, message):
        """创建 MoveArm action 的结果对象。"""
        result = MoveArm.Result()
        result.success = success
        result.error_code = error_code
        result.message = message
        return result


def main(args=None):
    """运行 Fake 机械臂控制节点。"""
    rclpy.init(args=args)
    node = FakeArmControlNode()

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
