"""Fake 场景管理器服务节点。"""

from dataclasses import dataclass

import rclpy
from assembly_interfaces.srv import AttachObject
from assembly_interfaces.srv import DetachObject
from assembly_interfaces.srv import GetObjectPose
from assembly_interfaces.srv import ResetScene
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


@dataclass
class SceneState:
    """保存 MVP-1 使用的 Fake 场景状态。"""

    scene_initialized: bool = False
    object_exists: bool = False
    object_attached: bool = False
    attached_link: str = ''
    object_location: str = 'unknown'
    last_task_id: str = ''

    def reset(self, task_id):
        """将场景状态重置到已知的初始物体位姿。"""
        self.scene_initialized = True
        self.object_exists = True
        self.object_attached = False
        self.attached_link = ''
        self.object_location = 'pickup_zone'
        self.last_task_id = task_id

    def attach(self, task_id, link_name):
        """将物体附着到指定 link。"""
        self.object_attached = True
        self.attached_link = link_name
        self.object_location = 'attached'
        self.last_task_id = task_id

    def detach(self, task_id, target_location):
        """释放物体，并更新物体的逻辑位置。"""
        self.object_attached = False
        self.attached_link = ''
        self.object_location = target_location
        self.last_task_id = task_id

    def to_log_fields(self):
        """把当前状态拼成一段结构化日志文本，方便调试。"""
        return (
            f'scene_initialized={self.scene_initialized} '
            f'object_exists={self.object_exists} '
            f'object_attached={self.object_attached} '
            f'attached_link={self.attached_link!r} '
            f'object_location={self.object_location!r} '
            f'last_task_id={self.last_task_id!r}'
        )


class FakeSceneManagerNode(Node):
    """处理 MVP-1 阶段的 Fake 场景管理请求。"""

    RESET_SCENE_SERVICE_NAME = '/assembly/reset_scene'
    GET_OBJECT_POSE_SERVICE_NAME = '/assembly/get_object_pose'
    ATTACH_OBJECT_SERVICE_NAME = '/assembly/attach_object'
    DETACH_OBJECT_SERVICE_NAME = '/assembly/detach_object'
    SUPPORTED_OBJECT_ID = 'mvp_object'

    # error codes
    EMPTY_TASK_ID_ERROR = 1001
    EMPTY_OBJECT_ID_ERROR = 5001
    OBJECT_NOT_EXIST_ERROR = 5002
    WHEN_ATTACH_OBJECT_HAS_BEEN_ATTACH_ERROR = 5003
    WHEN_DETACH_OBJECT_HAS_BEEN_DETACH_ERROR = 5004

    def __init__(self):
        """初始化假场景管理器节点和场景服务。"""
        super().__init__('fake_scene_manager_node')

        # 创建内部场景状态对象。
        self._scene_state = SceneState()
        # 注册场景服务。服务对象作为节点成员保存，生命周期跟节点一致。
        self._reset_scene_service = self.create_service(
            ResetScene,
            self.RESET_SCENE_SERVICE_NAME,
            self._handle_reset_scene,
        )
        self._get_object_pose_service = self.create_service(
            GetObjectPose,
            self.GET_OBJECT_POSE_SERVICE_NAME,
            self._handle_get_object_pose,
        )
        self._attach_object_service = self.create_service(
            AttachObject,
            self.ATTACH_OBJECT_SERVICE_NAME,
            self._handle_attach_object,
        )
        self._detach_object_service = self.create_service(
            DetachObject,
            self.DETACH_OBJECT_SERVICE_NAME,
            self._handle_detach_object,
        )
        self.get_logger().info(
            'event=fake_scene_manager_started '
            f'reset_scene_service={self.RESET_SCENE_SERVICE_NAME!r} '
            f'get_object_pose_service={self.GET_OBJECT_POSE_SERVICE_NAME!r} '
            f'attach_object_service={self.ATTACH_OBJECT_SERVICE_NAME!r} '
            f'detach_object_service={self.DETACH_OBJECT_SERVICE_NAME!r} '
            f'{self._scene_state.to_log_fields()}'
        )

    def _handle_reset_scene(self, request, response):
        """回调函数，校验 ResetScene 请求，并在合法时重置内部场景状态。"""
        task_id = request.task_id.strip()
        self.get_logger().info(
            f'event=reset_scene_request task_id={task_id!r}'
        )

        # task_id 为空时，沿用 MVP-0 的明确错误响应。
        if not task_id:
            return self._make_error_response(
                response,
                self.EMPTY_TASK_ID_ERROR,
                'task_id must not be empty',
                'reset_scene_response',
                task_id=task_id,
            )

        # 如果合法，就重置内部状态，然后填充成功响应。
        self._scene_state.reset(task_id)
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

    def _handle_get_object_pose(self, request, response):
        """回调函数，返回指定 object 的 fake 场景状态。"""
        object_id = request.object_id.strip()
        self.get_logger().info(
            'event=get_object_pose_request '
            f'object_id={object_id!r} '
            f'{self._scene_state.to_log_fields()}'
        )

        if not object_id:
            return self._make_error_response(
                response,
                self.EMPTY_OBJECT_ID_ERROR,
                'object_id must not be empty',
                'get_object_pose_response',
                object_id=object_id,
            )

        if not self._object_exists(object_id):
            return self._make_error_response(
                response,
                self.OBJECT_NOT_EXIST_ERROR,
                'object does not exist',
                'get_object_pose_response',
                object_id=object_id,
            )

        self._fill_object_state_response(response)
        response.success = True
        response.error_code = 0
        response.message = 'Object state returned successfully'
        self.get_logger().info(
            'event=get_object_pose_response '
            f'object_id={object_id!r} '
            f'success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._scene_state.to_log_fields()}'
        )
        return response

    def _handle_attach_object(self, request, response):
        """回调函数，校验 AttachObject 请求，并在合法时附着物体。"""
        task_id = request.task_id.strip()
        object_id = request.object_id.strip()
        link_name = request.link_name.strip()
        self.get_logger().info(
            'event=attach_object_request '
            f'task_id={task_id!r} '
            f'object_id={object_id!r} '
            f'link_name={link_name!r} '
            f'{self._scene_state.to_log_fields()}'
        )

        if not task_id:
            return self._make_error_response(
                response,
                self.EMPTY_TASK_ID_ERROR,
                'task_id must not be empty',
                'attach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        if not object_id:
            return self._make_error_response(
                response,
                self.EMPTY_OBJECT_ID_ERROR,
                'object_id must not be empty',
                'attach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        if not self._object_exists(object_id):
            return self._make_error_response(
                response,
                self.OBJECT_NOT_EXIST_ERROR,
                'object does not exist',
                'attach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        if self._scene_state.object_attached:
            return self._make_error_response(
                response,
                self.WHEN_ATTACH_OBJECT_HAS_BEEN_ATTACH_ERROR,
                'object is already attached',
                'attach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        self._scene_state.attach(task_id, link_name)
        response.success = True
        response.error_code = 0
        response.message = 'Object attached successfully'
        self.get_logger().info(
            'event=attach_object_response '
            f'task_id={task_id!r} '
            f'object_id={object_id!r} '
            f'success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._scene_state.to_log_fields()}'
        )
        return response

    def _handle_detach_object(self, request, response):
        """回调函数，校验 DetachObject 请求，并在合法时释放物体。"""
        task_id = request.task_id.strip()
        object_id = request.object_id.strip()
        target_location = request.target_location.strip()
        self.get_logger().info(
            'event=detach_object_request '
            f'task_id={task_id!r} '
            f'object_id={object_id!r} '
            f'target_location={target_location!r} '
            f'{self._scene_state.to_log_fields()}'
        )

        if not task_id:
            return self._make_error_response(
                response,
                self.EMPTY_TASK_ID_ERROR,
                'task_id must not be empty',
                'detach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        if not object_id:
            return self._make_error_response(
                response,
                self.EMPTY_OBJECT_ID_ERROR,
                'object_id must not be empty',
                'detach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        if not self._object_exists(object_id):
            return self._make_error_response(
                response,
                self.OBJECT_NOT_EXIST_ERROR,
                'object does not exist',
                'detach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        if not self._scene_state.object_attached:
            return self._make_error_response(
                response,
                self.WHEN_DETACH_OBJECT_HAS_BEEN_DETACH_ERROR,
                'object is not attached',
                'detach_object_response',
                task_id=task_id,
                object_id=object_id,
            )

        self._scene_state.detach(task_id, target_location)
        response.success = True
        response.error_code = 0
        response.message = 'Object detached successfully'
        self.get_logger().info(
            'event=detach_object_response '
            f'task_id={task_id!r} '
            f'object_id={object_id!r} '
            f'success={response.success} '
            f'error_code={response.error_code} '
            f'message={response.message!r} '
            f'{self._scene_state.to_log_fields()}'
        )
        return response

    def _object_exists(self, object_id):
        """判断请求中的 object_id 是否指向当前 fake 物体。"""
        return (
            self._scene_state.object_exists
            and object_id == self.SUPPORTED_OBJECT_ID
        )

    def _fill_object_state_response(self, response):
        """给带 object 状态字段的响应填充当前场景状态。"""
        if hasattr(response, 'object_location'):
            response.object_location = self._scene_state.object_location
        if hasattr(response, 'object_attached'):
            response.object_attached = self._scene_state.object_attached
        if hasattr(response, 'attached_link'):
            response.attached_link = self._scene_state.attached_link

    def _make_error_response(
        self,
        response,
        error_code,
        message,
        event,
        task_id='',
        object_id='',
    ):
        """填充失败响应，并记录当前场景状态。"""
        self._fill_object_state_response(response)
        response.success = False
        response.error_code = error_code
        response.message = message
        self.get_logger().warn(
            f'event={event} '
            f'task_id={task_id!r} '
            f'object_id={object_id!r} '
            f'success={response.success} '
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
