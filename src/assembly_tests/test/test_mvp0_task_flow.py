"""MVP-0 integration acceptance tests."""

import os
import subprocess
import threading
import time
import unittest

from assembly_interfaces.action import MoveArm
from assembly_interfaces.msg import TaskState
from assembly_interfaces.srv import ResetScene
from assembly_interfaces.srv import StartTask
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor


START_TASK_SERVICE = '/assembly/start_task'
RESET_SCENE_SERVICE = '/assembly/reset_scene'
MOVE_ARM_ACTION = '/assembly/move_arm'
TASK_STATE_TOPIC = '/assembly/task_state'


class TestMvp0TaskFlow(unittest.TestCase):
    """Verify the MVP-0 fake system through public ROS interfaces."""

    @classmethod
    def setUpClass(cls):
        """Start the real MVP-0 launch file once for this test class."""
        env = os.environ.copy()
        env.setdefault('ROS_LOG_DIR', os.path.join(os.getcwd(), 'ros_logs'))
        os.makedirs(env['ROS_LOG_DIR'], exist_ok=True)

        cls.launch_output = []
        cls.launch_process = subprocess.Popen(
            [
                'ros2',
                'launch',
                'assembly_bringup',
                'mvp0_fake_system.launch.py',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        cls.launch_output_thread = threading.Thread(
            target=cls._read_launch_output,
            daemon=True,
        )
        cls.launch_output_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Stop the launch process even if the test assertion fails."""
        process = getattr(cls, 'launch_process', None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)

        output_thread = getattr(cls, 'launch_output_thread', None)
        if output_thread is not None:
            output_thread.join(timeout=2.0)

    @classmethod
    def _read_launch_output(cls):
        for line in cls.launch_process.stdout:
            cls.launch_output.append(line)

    def setUp(self):
        """Create one ROS test node and wait for the launched system."""
        rclpy.init()
        self.node = rclpy.create_node('mvp0_task_flow_test_node')

        self.states = []
        self.states_condition = threading.Condition()
        self.task_state_subscription = self.node.create_subscription(
            TaskState,
            TASK_STATE_TOPIC,
            self._handle_task_state,
            10,
        )
        self.start_task_client = self.node.create_client(
            StartTask,
            START_TASK_SERVICE,
        )
        self.reset_scene_client = self.node.create_client(
            ResetScene,
            RESET_SCENE_SERVICE,
        )
        self.move_arm_client = ActionClient(
            self.node,
            MoveArm,
            MOVE_ARM_ACTION,
        )

        self.executor = MultiThreadedExecutor()
        self.executor.add_node(self.node)
        self.stop_spinning = threading.Event()
        self.spin_thread = threading.Thread(
            target=self._spin,
            daemon=True,
        )
        self.spin_thread.start()

        self._wait_for_mvp0_interfaces()

    def tearDown(self):
        """Stop the ROS executor and release test node resources."""
        self.stop_spinning.set()
        self.spin_thread.join(timeout=2.0)
        self.executor.shutdown()

        self.node.destroy_client(self.start_task_client)
        self.node.destroy_client(self.reset_scene_client)
        self.node.destroy_subscription(self.task_state_subscription)
        self.move_arm_client.destroy()
        self.node.destroy_node()
        rclpy.shutdown()

    def test_mvp0_task_flow_accepts_rejects_and_repeats(self):
        """Cover valid, invalid, state publishing, and repeated requests."""
        first_response = self._call_start_task('mvp0_home')
        self.assertTrue(first_response.accepted)
        self.assertTrue(first_response.task_id)
        self.assertEqual(first_response.error_code, 0)
        self.assertEqual(first_response.message, 'Task accepted')

        first_final_state = self._wait_for_state(
            first_response.task_id,
            'SUCCESS',
        )
        self._assert_successful_task_states(first_response.task_id)
        self.assertAlmostEqual(first_final_state.progress, 1.0, places=4)
        self.assertEqual(first_final_state.error_code, 0)

        empty_response = self._call_start_task('')
        self.assertFalse(empty_response.accepted)
        self.assertEqual(empty_response.task_id, '')
        self.assertEqual(empty_response.error_code, 3001)
        self.assertEqual(empty_response.message, 'task_name must not be empty')

        unsupported_response = self._call_start_task('unknown_task')
        self.assertFalse(unsupported_response.accepted)
        self.assertEqual(unsupported_response.task_id, '')
        self.assertEqual(unsupported_response.error_code, 3002)
        self.assertEqual(unsupported_response.message, 'unsupported task_name')

        repeated_task_ids = []
        for _ in range(10):
            response = self._call_start_task('mvp0_home')
            self.assertTrue(response.accepted)
            self.assertEqual(response.error_code, 0)
            final_state = self._wait_for_state(response.task_id, 'SUCCESS')
            self.assertEqual(final_state.error_code, 0)
            self._assert_successful_task_states(response.task_id)
            repeated_task_ids.append(response.task_id)

        self.assertEqual(len(repeated_task_ids), len(set(repeated_task_ids)))
        self.assertEqual(
            self._task_numbers(repeated_task_ids),
            sorted(self._task_numbers(repeated_task_ids)),
        )

    def _spin(self):
        while rclpy.ok() and not self.stop_spinning.is_set():
            self.executor.spin_once(timeout_sec=0.1)

    def _handle_task_state(self, state):
        with self.states_condition:
            self.states.append(state)
            self.states_condition.notify_all()

    def _wait_for_mvp0_interfaces(self):
        self.assertTrue(
            self._wait_for_process_alive(timeout_sec=5.0),
            'mvp0_fake_system launch process exited early:\n'
            f'{self._launch_output_tail()}',
        )
        self.assertTrue(
            self.start_task_client.wait_for_service(timeout_sec=15.0),
            f'{START_TASK_SERVICE} service is not available:\n'
            f'{self._launch_output_tail()}',
        )
        self.assertTrue(
            self.reset_scene_client.wait_for_service(timeout_sec=15.0),
            f'{RESET_SCENE_SERVICE} service is not available:\n'
            f'{self._launch_output_tail()}',
        )
        self.assertTrue(
            self.move_arm_client.wait_for_server(timeout_sec=15.0),
            f'{MOVE_ARM_ACTION} action server is not available:\n'
            f'{self._launch_output_tail()}',
        )
        self.assertTrue(
            self._wait_for_task_state_publisher(timeout_sec=15.0),
            f'{TASK_STATE_TOPIC} publisher is not available:\n'
            f'{self._launch_output_tail()}',
        )
        time.sleep(0.2)

    def _wait_for_process_alive(self, timeout_sec):
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self.launch_process.poll() is not None:
                return False
            time.sleep(0.1)
        return self.launch_process.poll() is None

    def _wait_for_task_state_publisher(self, timeout_sec):
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self.node.count_publishers(TASK_STATE_TOPIC) > 0:
                return True
            if self.launch_process.poll() is not None:
                return False
            time.sleep(0.1)
        return False

    def _call_start_task(self, task_name, timeout_sec=5.0):
        request = StartTask.Request()
        request.task_name = task_name
        future = self.start_task_client.call_async(request)
        self.assertTrue(
            self._wait_for_future(future, timeout_sec),
            f'timed out waiting for StartTask response for {task_name!r}',
        )
        return future.result()

    def _wait_for_future(self, future, timeout_sec):
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if future.done():
                return True
            if self.launch_process.poll() is not None:
                return False
            time.sleep(0.05)
        return future.done()

    def _wait_for_state(self, task_id, expected_state, timeout_sec=10.0):
        deadline = time.monotonic() + timeout_sec
        with self.states_condition:
            while time.monotonic() < deadline:
                state = self._latest_state(task_id, expected_state)
                if state is not None:
                    return state
                if self.launch_process.poll() is not None:
                    break
                remaining = max(0.0, deadline - time.monotonic())
                self.states_condition.wait(timeout=min(0.1, remaining))

        seen_states = [state.current_state for state in self._states_for(task_id)]
        self.fail(
            f'timed out waiting for {expected_state!r} for {task_id!r}; '
            f'seen states: {seen_states}\n'
            f'{self._launch_output_tail()}',
        )

    def _latest_state(self, task_id, expected_state):
        for state in reversed(self.states):
            if state.task_id == task_id and state.current_state == expected_state:
                return state
        return None

    def _assert_successful_task_states(self, task_id):
        states = [state.current_state for state in self._states_for(task_id)]
        expected_sequence = ['RESETTING', 'ARM_HOME', 'SUCCESS']
        indices = []
        for expected_state in expected_sequence:
            self.assertIn(expected_state, states)
            indices.append(states.index(expected_state))
        self.assertEqual(indices, sorted(indices))

    def _states_for(self, task_id):
        with self.states_condition:
            return [
                state for state in self.states
                if state.task_id == task_id
            ]

    def _task_numbers(self, task_ids):
        return [int(task_id.rsplit('_', 1)[1]) for task_id in task_ids]

    def _launch_output_tail(self, line_count=60):
        return ''.join(self.launch_output[-line_count:])
