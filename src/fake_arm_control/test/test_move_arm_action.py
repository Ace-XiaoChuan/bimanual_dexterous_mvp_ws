"""Test the FakeArmControlNode action through a real ROS 2 client."""

import os
from pathlib import Path

import pytest
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor

from assembly_interfaces.action import MoveArm
from fake_arm_control.fake_arm_control_node import FakeArmControlNode


@pytest.fixture
def arm_action():
    """启动 action 服务端节点、客户端节点和 executor."""
    ros_log_dir = Path('/tmp/fake_arm_control_ros_logs')
    ros_log_dir.mkdir(parents=True, exist_ok=True)
    os.environ['ROS_LOG_DIR'] = str(ros_log_dir)

    rclpy.init()

    # 服务端就是被测对象：它会注册 /assembly/move_arm action。
    server_node = FakeArmControlNode()

    # 客户端节点模拟真实调用者，例如后续的 assembly_task_node。
    client_node = rclpy.create_node('test_move_arm_client')

    # SingleThreadedExecutor 负责在同一个线程里调度 server 和 client 的回调。
    executor = SingleThreadedExecutor()
    executor.add_node(server_node)
    executor.add_node(client_node)

    action_client = ActionClient(
        client_node,
        MoveArm,
        FakeArmControlNode.ACTION_NAME,
    )

    # action client 等 action server；
    assert action_client.wait_for_server(timeout_sec=2.0)

    try:
        yield action_client, executor
    finally:
        executor.remove_node(client_node)
        executor.remove_node(server_node)
        client_node.destroy_node()
        server_node.destroy_node()
        executor.shutdown()

        if rclpy.ok():
            rclpy.shutdown()


def _send_move_arm_goal(
    action_client,
    executor,
    arm_name,
    target_name,
    timeout_sec=1.0,
):
    """发送一次 MoveArm action goal，并等待最终 result."""
    goal = MoveArm.Goal()
    goal.arm_name = arm_name
    goal.target_name = target_name
    goal.timeout_sec = timeout_sec

    feedback_list = []

    def feedback_callback(feedback_msg):
        """记录 action 执行过程中收到的 feedback."""
        feedback_list.append(feedback_msg.feedback)

    # send_goal_async() 是 Action 客户端向 Action 服务端发送一个目标（goal） 的函数。
    # 在它执行过程中，把反馈交给 feedback_callback 处理。”
    # 它不会立刻返回“运动成功/失败”，而是立刻返回一个 Future 对象
    send_goal_future = action_client.send_goal_async(
        goal,
        feedback_callback=feedback_callback,
    )
    executor.spin_until_future_complete(send_goal_future, timeout_sec=2.0)

    assert send_goal_future.done(), 'MoveArm goal was not accepted in time'
    assert send_goal_future.exception() is None

    goal_handle = send_goal_future.result()
    assert goal_handle is not None
    assert goal_handle.accepted is True

    result_future = goal_handle.get_result_async()
    executor.spin_until_future_complete(result_future, timeout_sec=3.0)

    assert result_future.done(), 'MoveArm result did not return in time'
    assert result_future.exception() is None

    result_response = result_future.result()
    assert result_response is not None

    return result_response.result, feedback_list


# pytest 的参数化测试。
# 把同一个测试函数，用不同的 target_name 值自动运行多次。
@pytest.mark.parametrize(
    'target_name',
    [
        'home',
        'pregrasp',
        'grasp',
        'lift',
        'preplace',
        'place',
        'retreat',
    ],
)
def test_supported_targets_succeed(arm_action, target_name):
    """验证 MVP-1 支持的机械臂目标都能成功."""
    action_client, executor = arm_action

    result, feedback_list = _send_move_arm_goal(
        action_client,
        executor,
        arm_name='right_arm',
        target_name=target_name,
        timeout_sec=1.0,
    )

    assert result.success is True
    assert result.error_code == 0
    assert target_name in result.message

    assert [feedback.current_state for feedback in feedback_list] == [
        'accepted',
        'moving',
        'succeeded',
    ]
    assert [feedback.progress for feedback in feedback_list] == [
        0.0,
        0.5,
        1.0,
    ]


def test_unsupported_arm_returns_2001(arm_action):
    """验证不支持的 arm_name 返回 2001."""
    action_client, executor = arm_action

    result, feedback_list = _send_move_arm_goal(
        action_client,
        executor,
        arm_name='left_arm',
        target_name='home',
        timeout_sec=1.0,
    )

    assert result.success is False
    assert result.error_code == 2001
    assert result.message == 'unsupported arm_name'
    assert feedback_list == []


def test_unsupported_target_returns_2002(arm_action):
    """验证不支持的 target_name 返回 2002."""
    action_client, executor = arm_action

    result, feedback_list = _send_move_arm_goal(
        action_client,
        executor,
        arm_name='right_arm',
        target_name='bad_target',
        timeout_sec=1.0,
    )

    assert result.success is False
    assert result.error_code == 2002
    assert result.message == 'unsupported target_name'
    assert feedback_list == []


def test_invalid_timeout_returns_2003(arm_action):
    """验证 timeout_sec <= 0 时返回 2003."""
    action_client, executor = arm_action

    result, feedback_list = _send_move_arm_goal(
        action_client,
        executor,
        arm_name='right_arm',
        target_name='home',
        timeout_sec=0.0,
    )

    assert result.success is False
    assert result.error_code == 2003
    assert result.message == 'timeout_sec must be positive'
    assert feedback_list == []
