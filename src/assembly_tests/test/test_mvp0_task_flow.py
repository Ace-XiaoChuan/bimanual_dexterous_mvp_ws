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
        另外需要注意：setUpClass()函数其实没有被显式调用，
        这是因为 unittest 认识这个约定名称 setUpClass，于是替我调用它一次。
        正常情况下，类方法还是需要显式调用的，不要误会了。

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
        """在后台线程中持续保存 launch 输出。

        子进程的 stdout 像一根管道。测试主线程负责发请求和做断言，
        这个后台线程负责把管道里的日志读出来，存进 launch_output。

        这样做有两个好处：
        - launch 输出不会因为没人读取而堆积。
        - 测试失败时，断言消息可以带上最近的 launch 日志。
        """
        for line in cls.launch_process.stdout:
            cls.launch_output.append(line)

    def setUp(self):
        """为每个测试用例创建 ROS 测试节点。

        setUp() 会在每一个 test_* 方法执行前自动运行。
        这里创建的 node、service client、action client 和 topic subscription
        都属于“本次测试用例”的资源；测试结束后会在 tearDown() 中释放。
        """
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
        """释放每个测试用例创建的 ROS 资源。

        tearDown() 会在每一个 test_* 方法结束后自动运行。
        即使测试中间断言失败，测试框架通常也会尽量执行 tearDown()，
        所以这里适合做关闭线程、销毁 client/subscription/node 这类清理工作。
        """
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
        此函数会被测试框架自动发现并调用。
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
        """在后台线程中驱动 ROS 回调。

        ROS 2 的 service response、action result 和 topic callback 都需要
        executor 被 spin，回调才会被调度执行。测试主线程正在等待断言结果，
        所以这里单独开一个线程循环 spin_once()。
        """
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
        """等待 /assembly/task_state 上出现 publisher。

        service 和 action 有现成的 wait_for_service()/wait_for_server()，
        topic 这里用 count_publishers() 轮询。看到 publisher 后，说明
        assembly_task_node 至少已经创建了状态发布接口。
        """
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
        """等待 ROS 异步调用完成，并避免测试无限卡住。

        call_async() 不会立刻返回业务结果，而是返回一个 future。
        future.done() 变成 True 时，才表示 response 已经回来。

        测试里必须给等待动作加 timeout。否则被测系统如果崩溃或接口失联，
        测试就会一直挂住，而不是给出清楚的失败信息。
        """
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if future.done():
                return True
            if self.launch_process.poll() is not None:
                return False
            time.sleep(0.05)
        return future.done()

    def _wait_for_state(self, task_id, expected_state, timeout_sec=10.0):
        """等待某个 task_id 发布指定状态。

        /assembly/task_state 是一个共享 topic。连续执行任务时，多个 task_id
        的状态消息会混在同一个列表里，所以等待时必须同时匹配 task_id 和
        expected_state。

        这里使用 Condition，而不是简单 sleep 固定时间：
        - 收到新状态时，callback 会 notify_all() 叫醒等待线程。
        - 没收到状态时，等待线程最多每 0.1 秒醒来检查一次。
        这样既不会空转太厉害，也能比较快地响应新消息。
        """
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
        """从已收到的状态里找最近一个匹配项。

        reversed(self.states) 表示从列表尾部往前找。尾部是最新收到的消息，
        所以一旦找到匹配的 task_id 和 current_state，就可以直接返回。
        """
        for state in reversed(self.states):
            if state.task_id == task_id and state.current_state == expected_state:
                return state
        return None

    def _assert_successful_task_states(self, task_id):
        """断言一个任务经历了成功路径的关键状态。

        只检查最终 SUCCESS 还不够。一个错误实现可能跳过 RESETTING 或 ARM_HOME
        直接发布 SUCCESS。这个 helper 会确认三个关键状态都出现过，并且出现
        顺序是 RESETTING -> ARM_HOME -> SUCCESS。
        """
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
        """从 task_id 字符串中取出末尾编号。

        当前 task_id 格式类似 mvp0_task_0001。测试只关心最后的数字部分，
        用它检查连续任务的编号是否递增。
        """
        return [int(task_id.rsplit('_', 1)[1]) for task_id in task_ids]

    def _launch_output_tail(self, line_count=60):
        """返回 launch 输出的最后若干行，供失败消息使用。

        测试失败时，完整日志通常很长；最后几十行往往最接近失败现场。
        把这段日志拼进断言消息，可以少开一个终端翻日志。
        """
        return ''.join(self.launch_output[-line_count:])
