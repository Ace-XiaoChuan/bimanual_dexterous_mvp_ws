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

# Public ROS interfaces exercised by this test.
START_TASK_SERVICE = '/assembly/start_task'
RESET_SCENE_SERVICE = '/assembly/reset_scene'
MOVE_ARM_ACTION = '/assembly/move_arm'
TASK_STATE_TOPIC = '/assembly/task_state'


class TestMvp0TaskFlow(unittest.TestCase):
    """通过公开 ROS 2 接口检查 MVP-0 fake 系统。

    unittest.TestCase 是测试类的基本骨架。测试框架会自动寻找以
    test_ 开头的方法，并把它们当成测试用例执行。

    测试是否通过不靠手动 print，而是靠断言。只要某个断言失败，
    该测试就失败，并给出失败位置和错误信息。
    """

    # @classmethod 让方法接收类对象 cls，而不是某个测试实例 self。
    @classmethod
    def setUpClass(cls):
        """为该测试类启动一次真实 MVP-0 launch 文件。

        setUpClass、setUp、tearDown 和 tearDownClass 都是 unittest
        fixture，也就是测试夹具/测试环境：
        - setUpClass：整个类开始前运行一次，启动整套系统。
        - setUp：每个 test_* 前运行一次，创建客户端、订阅者和节点。
        - tearDown：每个 test_* 后运行一次，释放本次测试资源。
        - tearDownClass：整个类结束后运行一次，停止整套系统。
        """
        env = os.environ.copy()
        env.setdefault('ROS_LOG_DIR', os.path.join(os.getcwd(), 'ros_logs'))
        os.makedirs(env['ROS_LOG_DIR'], exist_ok=True)

        cls.launch_output = []

        # 测试不假设系统已经启动，而是自己负责启动被测系统。
        # 测试术语中，被测试对象叫 SUT，即 System Under Test。
        # 在这里，SUT 是整套 MVP-0 fake ROS 系统。
        #
        # Popen 会异步启动子进程并立刻返回。如果使用 subprocess.run，
        # 测试会卡住，直到 launch 进程退出。
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

        # 持续读取 launch 输出，失败时可把尾部日志放进断言消息。
        cls.launch_output_thread = threading.Thread(
            target=cls._read_launch_output,
            daemon=True,
        )
        cls.launch_output_thread.start()

    @classmethod
    def tearDownClass(cls):
        """停止 ros2 launch 子进程，并清理测试创建的类级资源。"""
        process = getattr(cls, 'launch_process', None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                # terminate 后仍不退出时，用 kill 兜底。
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
        # 测试本身也是 ROS 2 图中的参与者，像一个自动化验收员。
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
        """Cover valid, invalid, state publishing, and repeated requests.

        测试代码通常可以用一个非常实用的结构理解：
        - Arrange：准备环境。
        - Act：执行被测行为。
        - Assert：验证结果。
        """
        # 正常路径（Happy Path）：合法的 mvp0_home 请求应被接受。
        first_response = self._call_start_task('mvp0_home')
        # 断言要具体：是否接受、是否生成 task_id、错误码和消息是否正确。
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

        # 异常路径（Negative Test）：空 task_name 应被拒绝。
        empty_response = self._call_start_task('')
        self.assertFalse(empty_response.accepted)
        self.assertEqual(empty_response.task_id, '')
        self.assertEqual(empty_response.error_code, 3001)
        self.assertEqual(empty_response.message, 'task_name must not be empty')

        # 异常路径：未支持的任务名应被拒绝。
        unsupported_response = self._call_start_task('unknown_task')
        self.assertFalse(unsupported_response.accepted)
        self.assertEqual(unsupported_response.task_id, '')
        self.assertEqual(unsupported_response.error_code, 3002)
        self.assertEqual(unsupported_response.message, 'unsupported task_name')

        repeated_task_ids = []
        for _ in range(10):
            # 这里不是性能压测，而是轻量级连续运行检查。
            response = self._call_start_task('mvp0_home')
            self.assertTrue(response.accepted)
            self.assertEqual(response.error_code, 0)
            final_state = self._wait_for_state(response.task_id, 'SUCCESS')
            self.assertEqual(final_state.error_code, 0)
            self._assert_successful_task_states(response.task_id)
            repeated_task_ids.append(response.task_id)

        # 确认 task ID 唯一。
        self.assertEqual(len(repeated_task_ids), len(set(repeated_task_ids)))
        # 确认 task ID 中的数字是递增的。
        self.assertEqual(
            self._task_numbers(repeated_task_ids),
            sorted(self._task_numbers(repeated_task_ids)),
        )

    def _spin(self):
        while rclpy.ok() and not self.stop_spinning.is_set():
            self.executor.spin_once(timeout_sec=0.1)

    def _handle_task_state(self, state):
        """记录状态消息，并唤醒正在等待状态变化的测试线程。

        订阅 topic 的 callback 和主测试线程并发运行，所以这里用
        threading.Condition 保护共享的 self.states。
        """
        with self.states_condition:
            self.states.append(state)
            self.states_condition.notify_all()

    def _wait_for_mvp0_interfaces(self):
        """等待被测系统的公开 ROS 接口全部就绪。"""
        # 先检查 launch 有没有提前崩溃。
        self.assertTrue(
            self._wait_for_process_alive(timeout_sec=5.0),
            'mvp0_fake_system launch process exited early:\n'
            f'{self._launch_output_tail()}',
        )
        # 等待 StartTask service。
        self.assertTrue(
            self.start_task_client.wait_for_service(timeout_sec=15.0),
            f'{START_TASK_SERVICE} service is not available:\n'
            f'{self._launch_output_tail()}',
        )
        # 等待 ResetScene service。
        self.assertTrue(
            self.reset_scene_client.wait_for_service(timeout_sec=15.0),
            f'{RESET_SCENE_SERVICE} service is not available:\n'
            f'{self._launch_output_tail()}',
        )
        # 等待 MoveArm action server。
        self.assertTrue(
            self.move_arm_client.wait_for_server(timeout_sec=15.0),
            f'{MOVE_ARM_ACTION} action server is not available:\n'
            f'{self._launch_output_tail()}',
        )
        # 等待 TaskState topic publisher。
        self.assertTrue(
            self._wait_for_task_state_publisher(timeout_sec=15.0),
            f'{TASK_STATE_TOPIC} publisher is not available:\n'
            f'{self._launch_output_tail()}',
        )
        time.sleep(0.2)

    def _wait_for_process_alive(self, timeout_sec):
        """在超时时间内确认 launch 进程仍然存活。

        time.monotonic() 使用单调递增时间，避免系统时间校准、
        NTP 调整或虚拟机时间修正影响等待逻辑。
        """
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
        """异步调用 StartTask service，并用 timeout 避免无限等待。"""
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

        # 成功不只看最终 SUCCESS，还要确认关键过程状态顺序正确。
        expected_sequence = ['RESETTING', 'ARM_HOME', 'SUCCESS']
        indices = []
        for expected_state in expected_sequence:
            self.assertIn(expected_state, states)
            indices.append(states.index(expected_state))
        self.assertEqual(indices, sorted(indices))

    def _states_for(self, task_id):
        """按 task_id 过滤状态消息，因为 /assembly/task_state 是共享 topic。

        连续运行多次任务后，同一个 topic 上会混合多个 task_id 的状态。
        如果不先过滤，测试可能把别的任务状态当成当前任务状态。

        例如：
        - task_1: RESETTING -> ARM_HOME -> SUCCESS
        - task_2: RESETTING -> ARM_HOME -> SUCCESS
        - task_3: RESETTING -> ARM_HOME -> SUCCESS
        """
        with self.states_condition:
            return [
                state for state in self.states
                if state.task_id == task_id
            ]

    def _task_numbers(self, task_ids):
        return [int(task_id.rsplit('_', 1)[1]) for task_id in task_ids]

    def _launch_output_tail(self, line_count=60):
        return ''.join(self.launch_output[-line_count:])
