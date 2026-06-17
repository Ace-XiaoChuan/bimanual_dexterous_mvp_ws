"""Fake 场景管理器服务节点。"""

from dataclasses import dataclass

import rclpy
from assembly_interfaces.srv import ResetScene
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


@dataclass
class SceneState:
    """保存 MVP-0 使用的 Fake 场景最小状态。"""

    scene_initialized: bool = False
    object_exists: bool = False
    object_attached: bool = False
    attached_link: str = ''
    object_location: str = 'unknown'

    def reset(self):
        """将场景状态重置到已知的初始物体位姿。"""
        self.scene_initialized = True
        self.object_exists = True
        self.object_attached = False
        self.attached_link = ''
        self.object_location = 'initial'

    def to_log_fields(self):
        """把当前状态拼成一段结构化日志文本，方便调试。"""
        return (
            f'scene_initialized={self.scene_initialized} '
            f'object_exists={self.object_exists} '
            f'object_attached={self.object_attached} '
            f'attached_link={self.attached_link!r} '
            f'object_location={self.object_location!r}'
        )


class FakeSceneManagerNode(Node):
    """处理 MVP-0 阶段的 Fake 场景管理请求。"""

    SERVICE_NAME = '/assembly/reset_scene'
    EMPTY_TASK_ID_ERROR = 1001

    def __init__(self):
        """初始化假场景管理器节点和 ResetScene 服务。"""
        super().__init__('fake_scene_manager_node')

        # 创建内部场景状态对象。
        self._scene_state = SceneState()
        # 注册 ResetScene 服务。这样服务对象会作为节点成员保存下来，生命周期跟节点一致。
        self._reset_scene_service = self.create_service(
            ResetScene,
            self.SERVICE_NAME,
            self._handle_reset_scene,
        )
        self.get_logger().info(
            'event=fake_scene_manager_started '
            f'service={self.SERVICE_NAME!r} '
            f'{self._scene_state.to_log_fields()}'
        )

    def _handle_reset_scene(self, request, response):
        """回调函数，校验 ResetScene 请求，并在合法时重置内部场景状态。"""
        task_id = request.task_id.strip()
        self.get_logger().info(
            f'event=reset_scene_request task_id={task_id!r}'
        )

        if not task_id:
            # 如果为空，就填充失败响应：
            response.success = False
            response.error_code = self.EMPTY_TASK_ID_ERROR
            response.message = 'task_id must not be empty'
            self.get_logger().warn(
                'event=reset_scene_response '
                f'task_id={task_id!r} success={response.success} '
                f'error_code={response.error_code} '
                f'message={response.message!r} '
                f'{self._scene_state.to_log_fields()}'
            )
            return response

        # 如果合法，就重置内部状态，然后填充成功响应：
        self._scene_state.reset()
        response.success = True
        response.error_code = 0
        response.message = 'Scene reset successfully'

        self.get_logger().info(
            'event=reset_scene_response '
            f'task_id={task_id!r} success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._scene_state.to_log_fields()}'
        )
        return response


def main(args=None):
    """运行 Fake 场景管理器节点。"""
    rclpy.init(args=args)
    node = FakeSceneManagerNode()

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
