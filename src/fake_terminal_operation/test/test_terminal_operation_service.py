"""Test the TerminalOperationNode service through a real ROS 2 client."""

import os
from pathlib import Path

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor

from assembly_interfaces.srv import ExecuteTerminalOperation
from fake_terminal_operation.fake_terminal_operation_node import TerminalOperationNode


@pytest.fixture
def terminal_service():
    """启动服务端节点、客户端节点和 executor."""
    ros_log_dir = Path('/tmp/fake_terminal_operation_ros_logs')
    ros_log_dir.mkdir(parents=True, exist_ok=True)
    os.environ['ROS_LOG_DIR'] = str(ros_log_dir)
    rclpy.init()

    server_node = TerminalOperationNode()
    client_node = rclpy.create_node('test_terminal_operation_client')

    executor = SingleThreadedExecutor()
    executor.add_node(server_node)
    executor.add_node(client_node)

    client = client_node.create_client(
        ExecuteTerminalOperation,
        TerminalOperationNode.SERVICE_NAME,
    )
    assert client.wait_for_service(timeout_sec=2.0)
    try:
        yield client, executor
    finally:
        executor.remove_node(client_node)
        executor.remove_node(server_node)
        client_node.destroy_node()
        server_node.destroy_node()
        executor.shutdown()

        if rclpy.ok():
            rclpy.shutdown()


def _call_terminal_operation(
    client,
    executor,
    task_id,
    operation_type,
    object_id,
    target_location,
    timeout_sec,
):
    """发送一次 TerminalOperationNode 请求，并等待服务端返回响应."""
    request = ExecuteTerminalOperation.Request()
    request.task_id = task_id
    request.operation_type = operation_type
    request.object_id = object_id
    request.target_location = target_location
    request.timeout_sec = timeout_sec

    future = client.call_async(request)
    executor.spin_until_future_complete(future, timeout_sec=2.0)

    assert future.done(), 'TerminalOperation service did not respond in time'
    assert future.exception() is None
    assert future.result() is not None
    return future.result()


def test_supported_operation_succeeds(terminal_service):
    """验证 MVP-1 支持的唯一一个 place 命令能成功返回."""
    client, executor = terminal_service

    response = _call_terminal_operation(
        # 这里有两层的合法:
        # 项目语义上的合法,来自配置和文档,比如 mvp_object、place_zone、PLACE。
        # 服务端代码实际校验的合法：当前只有 operation_type 必须等于 PLACE,其他都不严格要求.
        client,
        executor,
        task_id='pick_and_place_mvp',
        operation_type='PLACE',
        object_id='mvp_object',
        target_location='place_zone',
        timeout_sec=1.0,
    )
    assert response.success is True
    assert response.error_code == 0
    assert 'completed successfully' in response.message


def test_null_task_id_returns_1001(terminal_service):
    """验证为空的的 task_id 返回 1001."""
    client, executor = terminal_service

    response = _call_terminal_operation(
        client,
        executor,
        task_id='',
        operation_type='PLACE',
        object_id='mvp_object',
        target_location='place_zone',
        timeout_sec=1.0,
    )
    assert response.success is False
    assert response.error_code == 1001
    assert response.message == 'task_id must not be empty'


def test_unsupported_operation_type_returns_6001(terminal_service):
    """验证不支持的 operation_type 返回 6001."""
    client, executor = terminal_service

    response = _call_terminal_operation(
        client,
        executor,
        task_id='pick_and_place_mvp',
        operation_type='INSERT',
        object_id='mvp_object',
        target_location='place_zone',
        timeout_sec=1.0,
    )
    assert response.success is False
    assert response.error_code == 6001
    assert response.message == 'unsupported operation_type'


def test_empty_target_location_returns_6002(terminal_service):
    """验证 target_location 为空时返回 6002."""
    client, executor = terminal_service

    response = _call_terminal_operation(
        client,
        executor,
        task_id='pick_and_place_mvp',
        operation_type='PLACE',
        object_id='mvp_object',
        target_location='',
        timeout_sec=1.0,
    )

    assert response.success is False
    assert response.error_code == 6002
    assert response.message == 'target_location must not be empty'


def test_invalid_timeout_returns_6003(terminal_service):
    """验证 timeout_sec <= 0 时返回 6003."""
    client, executor = terminal_service

    response = _call_terminal_operation(
        client,
        executor,
        task_id='pick_and_place_mvp',
        operation_type='PLACE',
        object_id='mvp_object',
        target_location='place_zone',
        timeout_sec=0.0,
    )

    assert response.success is False
    assert response.error_code == 6003
    assert response.message == 'timeout_sec must be positive'


def test_empty_object_id_returns_6004(terminal_service):
    """验证 object_id 为空时返回 6004."""
    client, executor = terminal_service

    response = _call_terminal_operation(
        client,
        executor,
        task_id='pick_and_place_mvp',
        operation_type='PLACE',
        object_id='',
        target_location='place_zone',
        timeout_sec=1.0,
    )

    assert response.success is False
    assert response.error_code == 6004
    assert response.message == 'object_id must not be empty'
