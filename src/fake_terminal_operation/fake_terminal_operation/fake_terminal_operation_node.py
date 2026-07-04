"""Fake 末端操作节点."""

from dataclasses import dataclass

import rclpy
from assembly_interfaces.srv import ExecuteTerminalOperation
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


@dataclass
class TerminalState:
    """保存 MVP-1 使用的 Fake 终端操作状态."""

    last_task_id: str = ''
    last_operation_type: str = ''
    last_object_id: str = ''
    last_target_location: str = ''
    operation_completed: bool = False
    last_error_code: int = 0
    last_message: str = ''
    terminal_operation_request: bool = False

    def place(self, task_id, object_id, target_location):
        """记录一次成功的 PLACE 操作."""
        self.terminal_operation_request = True
        self.last_task_id = task_id
        self.last_operation_type = 'PLACE'
        self.last_object_id = object_id
        self.last_target_location = target_location
        self.operation_completed = True
        self.last_error_code = 0
        self.last_message = 'PLACE operation completed successfully'

    def record_error(
        self,
        task_id,
        operation_type,
        object_id,
        target_location,
        error_code,
        message,
    ):
        """记录最近一次失败响应."""
        self.terminal_operation_request = True
        self.last_task_id = task_id
        self.last_operation_type = operation_type
        self.last_object_id = object_id
        self.last_target_location = target_location
        self.operation_completed = False
        self.last_error_code = error_code
        self.last_message = message

    def to_log_fields(self):
        """把当前状态拼成一段结构化日志文本，方便调试."""
        return (
            f'terminal_operation_request={self.terminal_operation_request} '
            f'last_task_id={self.last_task_id!r} '
            f'last_operation_type={self.last_operation_type!r} '
            f'last_object_id={self.last_object_id!r} '
            f'last_target_location={self.last_target_location!r} '
            f'operation_completed={self.operation_completed} '
            f'last_error_code={self.last_error_code} '
            f'last_message={self.last_message!r}'
        )


class TerminalOperationNode(Node):
    """处理 MVP-1 阶段的 Fake 终端操作请求."""

    SERVICE_NAME = '/assembly/execute_terminal_operation'
    SUPPORTED_OPERATION_TYPE = 'PLACE'

    # error codes
    EMPTY_TASK_ID_ERROR = 1001
    UNSUPPORTED_OPERATION_TYPE_ERROR = 6001
    NULL_TARGET_LOCATION_ERROR = 6002
    INVALID_TIMEOUT_SEC_ERROR = 6003
    NULL_OBJECT_ID_ERROR = 6004

    def __init__(self):
        """初始化 Fake 终端操作节点."""
        super().__init__('fake_terminal_operation_node')
        self._terminal_state = TerminalState()
        self._place_service = self.create_service(
            ExecuteTerminalOperation,
            self.SERVICE_NAME,
            self._handle_place_service,
        )
        self.get_logger().info(
            'event=fake_terminal_operation_node_started '
            f'place_service={self.SERVICE_NAME!r} '
            f'{self._terminal_state.to_log_fields()}'
        )

    def _handle_place_service(self, request, response):
        """处理 ExecuteTerminalOperation 请求，校验后返回 fake 结果."""
        task_id = request.task_id.strip()
        operation_type = request.operation_type.strip()
        object_id = request.object_id.strip()
        target_location = request.target_location.strip()
        timeout_sec = request.timeout_sec

        self.get_logger().info(
            'event=terminal_operation_request '
            f'task_id={task_id!r} '
            f'operation_type={operation_type!r} '
            f'object_id={object_id!r} '
            f'target_location={target_location!r} '
            f'timeout_sec={timeout_sec}'
        )

        if not task_id:
            return self._make_error_response(
                response,
                self.EMPTY_TASK_ID_ERROR,
                'task_id must not be empty',
                task_id=task_id,
                operation_type=operation_type,
                object_id=object_id,
                target_location=target_location,
            )

        if operation_type != self.SUPPORTED_OPERATION_TYPE:
            return self._make_error_response(
                response,
                self.UNSUPPORTED_OPERATION_TYPE_ERROR,
                'unsupported operation_type',
                task_id=task_id,
                operation_type=operation_type,
                object_id=object_id,
                target_location=target_location,
            )

        if not object_id:
            return self._make_error_response(
                response,
                self.NULL_OBJECT_ID_ERROR,
                'object_id must not be empty',
                task_id=task_id,
                operation_type=operation_type,
                object_id=object_id,
                target_location=target_location,
            )

        if not target_location:
            return self._make_error_response(
                response,
                self.NULL_TARGET_LOCATION_ERROR,
                'target_location must not be empty',
                task_id=task_id,
                operation_type=operation_type,
                object_id=object_id,
                target_location=target_location,
            )

        if timeout_sec <= 0.0:
            return self._make_error_response(
                response,
                self.INVALID_TIMEOUT_SEC_ERROR,
                'timeout_sec must be positive',
                task_id=task_id,
                operation_type=operation_type,
                object_id=object_id,
                target_location=target_location,
            )

        self._terminal_state.place(task_id, object_id, target_location)
        response.success = True
        response.error_code = 0
        response.message = 'PLACE operation completed successfully'

        self.get_logger().info(
            'event=terminal_operation_response '
            f'task_id={task_id!r} '
            f'operation_type={operation_type!r} '
            f'object_id={object_id!r} '
            f'target_location={target_location!r} '
            f'success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._terminal_state.to_log_fields()}'
        )
        return response

    def _make_error_response(
        self,
        response,
        error_code,
        message,
        task_id='',
        operation_type='',
        object_id='',
        target_location='',
    ):
        """填充失败响应，并记录当前终端操作状态."""
        self._terminal_state.record_error(
            task_id,
            operation_type,
            object_id,
            target_location,
            error_code,
            message,
        )
        response.success = False
        response.error_code = error_code
        response.message = message
        self.get_logger().warn(
            'event=terminal_operation_response '
            f'task_id={task_id!r} '
            f'operation_type={operation_type!r} '
            f'object_id={object_id!r} '
            f'target_location={target_location!r} '
            f'success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._terminal_state.to_log_fields()}'
        )
        return response


def main(args=None):
    """运行 Fake 末端操作节点."""
    rclpy.init(args=args)
    node = TerminalOperationNode()

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
