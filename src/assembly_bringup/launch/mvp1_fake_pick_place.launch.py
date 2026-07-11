"""Launch the MVP-1 fake Pick-and-Place system."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Start all nodes needed by the MVP-1 fake Pick-and-Place task loop."""
    return LaunchDescription([
        Node(
            package='fake_scene_manager',
            executable='fake_scene_manager_node',
            name='fake_scene_manager_node',
            output='screen',
        ),
        Node(
            package='fake_arm_control',
            executable='fake_arm_control_node',
            name='fake_arm_control_node',
            output='screen',
        ),
        Node(
            package='fake_hand_control',
            executable='fake_hand_control_node',
            name='fake_hand_control_node',
            output='screen',
        ),
        Node(
            package='fake_terminal_operation',
            executable='fake_terminal_operation_node',
            name='fake_terminal_operation_node',
            output='screen',
        ),
        Node(
            package='assembly_task',
            executable='assembly_task_node',
            name='assembly_task_node',
            output='screen',
        ),
    ])
