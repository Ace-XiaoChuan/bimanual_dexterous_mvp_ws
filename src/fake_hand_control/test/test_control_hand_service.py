"""Test the FakeHandControlNode service through a real ROS 2 client."""

import os
from pathlib import Path

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor

from assembly_interfaces.srv import ControlHand
from fake_hand_control.fake_hand_control_node import FakeHandControlNode


@pytest.fixture
def hand_service():
    """启动服务端节点、客户端节点和 executor."""
    # ROS 2 默认把日志写到 ~/.ros/log。
    # 在受限测试环境中，HOME 目录可能不可写，所以这里显式改到 /tmp。
    # 这只影响测试进程，不会改变 package 的正常运行方式。
    ros_log_dir = Path('/tmp/fake_hand_control_ros_logs')
    ros_log_dir.mkdir(parents=True, exist_ok=True)
    os.environ['ROS_LOG_DIR'] = str(ros_log_dir)

    rclpy.init()

    # 服务端就是被测对象：它会注册 /assembly/control_hand。
    # 这里不是直接调用 _handle_control_hand，而是让 ROS 2 service
    # 真正走一遍 client -> middleware -> server -> response 的路径。
    server_node = FakeHandControlNode()

    # 客户端节点模拟真实使用者，例如后续的 assembly_task_node。
    # ROS 2 中 client 也必须挂在某个 node 上，不能凭空发送请求。
    client_node = rclpy.create_node('test_control_hand_client')

    # Executor 负责调度节点回调。
    # 这里把服务端和客户端都加进去，测试进程才能同时发请求和处理服务回调。
    executor = SingleThreadedExecutor()
    executor.add_node(server_node)
    executor.add_node(client_node)

    client = client_node.create_client(
        ControlHand,
        FakeHandControlNode.SERVICE_NAME,
    )

    # wait_for_service 用来确认服务已经注册成功。
    # 如果这里失败，说明 /assembly/control_hand 本身不可发现。
    assert client.wait_for_service(timeout_sec=2.0)

    try:
        yield client, executor
    finally:
        # fixture 退出时清理节点和 ROS context。
        # 不清理会影响后面的测试，因为 service 名称和 node 名称可能残留。
        executor.remove_node(client_node)
        executor.remove_node(server_node)
        client_node.destroy_node()
        server_node.destroy_node()
        executor.shutdown()

        if rclpy.ok():
            rclpy.shutdown()


def _call_control_hand(
    client,
    executor,
    hand_name,
    command,
    grasp_name='default',
    timeout_sec=1.0,
):
    """发送一次 ControlHand 请求，并等待服务端返回响应."""
    request = ControlHand.Request()
    request.hand_name = hand_name
    request.command = command
    request.grasp_name = grasp_name
    request.timeout_sec = timeout_sec

    # call_async 不会立刻返回 response，而是返回一个 future。
    # executor.spin_until_future_complete 会不断处理回调，直到 future 完成。
    future = client.call_async(request)
    executor.spin_until_future_complete(future, timeout_sec=2.0)

    assert future.done(), 'ControlHand service did not respond in time'
    assert future.exception() is None
    assert future.result() is not None
    return future.result()


@pytest.mark.parametrize(
    'command',
    [
        'open',
        'preshape',
        'close',
        'hold',
        'release',
    ],
)
def test_supported_commands_succeed(hand_service, command):
    """验证 MVP-1 支持的五个手部命令都能成功返回."""
    client, executor = hand_service

    response = _call_control_hand(
        client,
        executor,
        hand_name='right_hand',
        command=command,
    )

    # 成功路径只要求 service contract 成立：
    # success=True、error_code=0、message 给出明确成功信息。
    assert response.success is True
    assert response.error_code == 0
    assert 'executed successfully' in response.message


def test_unsupported_hand_returns_4001(hand_service):
    """验证不支持的 hand_name 返回 4001."""
    client, executor = hand_service

    response = _call_control_hand(
        client,
        executor,
        hand_name='left_hand',
        command='open',
    )

    assert response.success is False
    assert response.error_code == 4001
    assert response.message == 'unsupported hand_name'


def test_unsupported_command_returns_4002(hand_service):
    """验证不支持的 command 返回 4002."""
    client, executor = hand_service

    response = _call_control_hand(
        client,
        executor,
        hand_name='right_hand',
        command='pinch',
    )

    assert response.success is False
    assert response.error_code == 4002
    assert response.message == 'unsupported command'


def test_invalid_timeout_returns_4003(hand_service):
    """验证 timeout_sec <= 0 时返回 4003."""
    client, executor = hand_service

    response = _call_control_hand(
        client,
        executor,
        hand_name='right_hand',
        command='open',
        timeout_sec=0.0,
    )

    assert response.success is False
    assert response.error_code == 4003
    assert response.message == 'timeout_sec must be positive'
