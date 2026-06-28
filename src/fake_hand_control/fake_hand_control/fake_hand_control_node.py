from dataclasses import dataclass

import rclpy
from assembly_interfaces.srv import ControlHand
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


@dataclass
class HandState:
    """保存 MVP-1 使用的 Fake 灵巧手状态。"""

    current_hand: str = 'right_hand'
    current_command: str = ''
    current_grasp: str = 'default'
    is_closed: bool = False
    is_holding: bool = False
    last_error_code: int = 0
    last_message: str = ''

    def apply_command(self, current_hand, current_command, current_grasp):
        """执行 Fake 命令，将各字段设置为目标状态。"""
        self.current_hand = current_hand
        self.current_command = current_command
        self.current_grasp = current_grasp or 'default'
        self.last_error_code = 0
        self.last_message = ''

        if current_command == 'open':
            self.is_closed = False
            self.is_holding = False
        elif current_command == 'preshape':
            self.is_closed = False
            self.is_holding = False
        elif current_command == 'close':
            self.is_closed = True
        elif current_command == 'hold':
            self.is_holding = True
        elif current_command == 'release':
            self.is_holding = False
            self.is_closed = False

    def to_log_fields(self):
        """把当前状态拼成一段结构化日志文本，方便调试。"""
        return (
            f'current_hand={self.current_hand!r} '
            f'current_command={self.current_command!r} '
            f'current_grasp={self.current_grasp!r} '
            f'is_closed={self.is_closed} '
            f'is_holding={self.is_holding} '
            f'last_error_code={self.last_error_code} '
            f'last_message={self.last_message!r}'
        )


class FakeHandControlNode(Node):
    """处理 MVP-1 阶段的 Fake Hand 请求。"""

    SERVICE_NAME = '/assembly/control_hand'
    SUPPORTED_HAND = 'right_hand'
    SUPPORTED_COMMANDS = {
        'open',
        'preshape',
        'close',
        'hold',
        'release',
    }

    # error codes
    UNSUPPORTED_HAND_ERROR = 4001
    UNSUPPORTED_COMMAND_ERROR = 4002
    INVALID_TIMEOUT_ERROR = 4003

    def __init__(self):
        super().__init__('fake_hand_control_node')

        # 保存灵巧手状态对象。
        self._hand_state = HandState()
        self._control_hand_service = self.create_service(
            ControlHand,
            self.SERVICE_NAME,
            self._handle_control_hand,
        )
        self.get_logger().info(
            'event=fake_hand_control_node_service_started '
            f'service={self.SERVICE_NAME!r} '
            f'{self._hand_state.to_log_fields()}'
        )

    def _handle_control_hand(self, request, response):
        """回调函数，校验 ControlHand 请求，并在合法时执行对灵巧手的控制。"""
        hand_name = request.hand_name.strip()
        command = request.command.strip()
        grasp_name = request.grasp_name.strip() or 'default'

        self.get_logger().info(
            'event=control_hand_request '
            f'hand_name={hand_name!r} '
            f'command={command!r} '
            f'grasp_name={grasp_name!r} '
            f'timeout_sec={request.timeout_sec} '
            f'{self._hand_state.to_log_fields()}'
        )

        # 错误响应
        # 1.灵巧手名字为空：
        if not hand_name:
            return self._make_error_response(
                response,
                self.UNSUPPORTED_HAND_ERROR,
                'hand_name must not be empty',
            )

        # 2.灵巧手名字不支持：
        if hand_name != self.SUPPORTED_HAND:
            return self._make_error_response(
                response,
                self.UNSUPPORTED_HAND_ERROR,
                'unsupported hand_name',
            )

        # 2.命令为空：
        if not command:
            return self._make_error_response(
                response,
                self.UNSUPPORTED_COMMAND_ERROR,
                'command must not be empty',
            )

        # 3.命令不支持：
        if command not in self.SUPPORTED_COMMANDS:
            return self._make_error_response(
                response,
                self.UNSUPPORTED_COMMAND_ERROR,
                'unsupported command',
            )

        # 4.抓型不支持：
        if grasp_name != 'default':
            return self._make_error_response(
                response,
                self.UNSUPPORTED_COMMAND_ERROR,
                'unsupported grasp_name',
            )

        # 5.超时时间非法：
        if request.timeout_sec <= 0.0:
            return self._make_error_response(
                response,
                self.INVALID_TIMEOUT_ERROR,
                'timeout_sec must be positive',
            )

        # 成功响应
        self._hand_state.apply_command(hand_name, command, grasp_name)
        response.success = True
        response.error_code = 0
        response.message = f'hand command {command} executed successfully'
        self.get_logger().info(
            'event=control_hand_response '
            f'success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._hand_state.to_log_fields()}'
        )
        return response

    def _make_error_response(self, response, error_code, message):
        """填充失败响应，并记录最近一次错误状态。"""
        response.success = False
        response.error_code = error_code
        response.message = message

        self._hand_state.last_error_code = error_code
        self._hand_state.last_message = message

        self.get_logger().warn(
            'event=control_hand_response '
            f'success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._hand_state.to_log_fields()}'
        )
        return response


def main(args=None):
    """运行 Fake 灵巧手管理节点。"""
    rclpy.init(args=args)
    node = FakeHandControlNode()
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
