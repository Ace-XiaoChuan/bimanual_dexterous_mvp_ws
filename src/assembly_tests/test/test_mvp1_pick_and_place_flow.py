"""MVP-1 Pick-and-Place integration acceptance tests."""

import os
import signal
import subprocess
import threading
import time
import unittest

from assembly_interfaces.action import MoveArm
from assembly_interfaces.msg import TaskState
from assembly_interfaces.srv import AttachObject
from assembly_interfaces.srv import ControlHand
from assembly_interfaces.srv import DetachObject
from assembly_interfaces.srv import ExecuteTerminalOperation
from assembly_interfaces.srv import GetObjectPose
from assembly_interfaces.srv import ResetScene
from assembly_interfaces.srv import StartTask
import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor


START_TASK_SERVICE = '/assembly/start_task'
RESET_SCENE_SERVICE = '/assembly/reset_scene'
GET_OBJECT_POSE_SERVICE = '/assembly/get_object_pose'
CONTROL_HAND_SERVICE = '/assembly/control_hand'
ATTACH_OBJECT_SERVICE = '/assembly/attach_object'
DETACH_OBJECT_SERVICE = '/assembly/detach_object'
EXECUTE_TERMINAL_OPERATION_SERVICE = '/assembly/execute_terminal_operation'
MOVE_ARM_ACTION = '/assembly/move_arm'
TASK_STATE_TOPIC = '/assembly/task_state'

MVP0_TASK_NAME = 'mvp0_home'
MVP1_TASK_NAME = 'pick_and_place_mvp'
MVP_OBJECT_ID = 'mvp_object'
MVP1_TARGET_LOCATION = 'place_zone'

MVP0_SUCCESS_SEQUENCE = [
    'RESETTING',
    'ARM_HOME',
    'SUCCESS',
]

MVP1_SUCCESS_SEQUENCE = [
    'RESETTING',
    'ARM_HOME',
    'HAND_OPEN',
    'ARM_PREGRASP',
    'HAND_PRESHAPE',
    'ARM_GRASP',
    'HAND_CLOSE',
    'ATTACH_OBJECT',
    'ARM_LIFT',
    'ARM_PREPLACE',
    'ARM_PLACE',
    'TERMINAL_PLACE',
    'DETACH_OBJECT',
    'HAND_OPEN',
    'ARM_RETREAT',
    'ARM_HOME',
    'SUCCESS',
]


class TestMvp1PickAndPlaceFlow(unittest.TestCase):
    """通过公开 ROS 2 接口检查 MVP-1 fake Pick-and-Place 系统。"""

    @classmethod
    def setUpClass(cls):
        """启动 MVP-1 launch；整个测试类共享同一套被测系统。"""
        env = os.environ.copy()
        env.setdefault('ROS_LOG_DIR', os.path.join(os.getcwd(), 'ros_logs'))
        os.makedirs(env['ROS_LOG_DIR'], exist_ok=True)

        cls.launch_output = []
        cls.launch_process = subprocess.Popen(
            [
                'ros2',
                'launch',
                'assembly_bringup',
                'mvp1_fake_pick_place.launch.py',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            start_new_session=True,
        )
        cls.launch_output_thread = threading.Thread(
            target=cls._read_launch_output,
            daemon=True,
        )
        cls.launch_output_thread.start()

    @classmethod
    def tearDownClass(cls):
        """停止 launch 子进程。"""
        process = getattr(cls, 'launch_process', None)
        if process is not None and process.poll() is None:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait(timeout=5.0)

        output_thread = getattr(cls, 'launch_output_thread', None)
        if output_thread is not None:
            output_thread.join(timeout=2.0)

    @classmethod
    def _read_launch_output(cls):
        """持续读取 launch 输出，供失败断言展示尾部日志。"""
        for line in cls.launch_process.stdout:
            cls.launch_output.append(line)

    def setUp(self):
        """创建测试节点、客户端和状态订阅。"""
        rclpy.init()
        self.node = rclpy.create_node('mvp1_pick_and_place_test_node')

        self.states = []
        self.states_condition = threading.Condition()
        self.task_state_subscription = self.node.create_subscription(
            TaskState,
            TASK_STATE_TOPIC,
            self._handle_task_state,
            100,
        )

        self.start_task_client = self.node.create_client(
            StartTask,
            START_TASK_SERVICE,
        )
        self.reset_scene_client = self.node.create_client(
            ResetScene,
            RESET_SCENE_SERVICE,
        )
        self.get_object_pose_client = self.node.create_client(
            GetObjectPose,
            GET_OBJECT_POSE_SERVICE,
        )
        self.control_hand_client = self.node.create_client(
            ControlHand,
            CONTROL_HAND_SERVICE,
        )
        self.attach_object_client = self.node.create_client(
            AttachObject,
            ATTACH_OBJECT_SERVICE,
        )
        self.detach_object_client = self.node.create_client(
            DetachObject,
            DETACH_OBJECT_SERVICE,
        )
        self.execute_terminal_operation_client = self.node.create_client(
            ExecuteTerminalOperation,
            EXECUTE_TERMINAL_OPERATION_SERVICE,
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

        self._wait_for_mvp1_interfaces()

    def tearDown(self):
        """释放每个测试用例创建的 ROS 资源。"""
        self.stop_spinning.set()
        self.spin_thread.join(timeout=2.0)
        self.executor.shutdown()

        self.node.destroy_client(self.start_task_client)
        self.node.destroy_client(self.reset_scene_client)
        self.node.destroy_client(self.get_object_pose_client)
        self.node.destroy_client(self.control_hand_client)
        self.node.destroy_client(self.attach_object_client)
        self.node.destroy_client(self.detach_object_client)
        self.node.destroy_client(self.execute_terminal_operation_client)
        self.node.destroy_subscription(self.task_state_subscription)
        self.move_arm_client.destroy()
        self.node.destroy_node()
        rclpy.shutdown()

    def test_pick_and_place_acceptance_and_regressions(self):
        """覆盖 MVP-1 正常链路、MVP-0 回归、非法输入和连续运行。"""
        self._assert_start_task_rejects_empty_task_name()
        self._assert_start_task_rejects_unsupported_task_name()
        self._assert_mvp0_home_still_passes()

        first_response = self._run_pick_and_place_once()
        self.assertTrue(first_response.task_id)

        repeated_task_ids = []
        for _ in range(10):
            response = self._run_pick_and_place_once()
            repeated_task_ids.append(response.task_id)

        self.assertEqual(len(repeated_task_ids), len(set(repeated_task_ids)))
        self.assertEqual(
            self._task_numbers(repeated_task_ids),
            sorted(self._task_numbers(repeated_task_ids)),
        )

    def _spin(self):
        """后台 spin，驱动 service response 和 topic callback。"""
        while rclpy.ok() and not self.stop_spinning.is_set():
            self.executor.spin_once(timeout_sec=0.1)

    def _handle_task_state(self, state):
        """记录任务状态消息。"""
        with self.states_condition:
            self.states.append(state)
            self.states_condition.notify_all()

    def _wait_for_mvp1_interfaces(self):
        """等待 MVP-1 launch 暴露全部公开接口。"""
        self.assertTrue(
            self._wait_for_process_alive(timeout_sec=5.0),
            'mvp1_fake_pick_place launch process exited early:\n'
            f'{self._launch_output_tail()}',
        )
        service_clients = [
            (START_TASK_SERVICE, self.start_task_client),
            (RESET_SCENE_SERVICE, self.reset_scene_client),
            (GET_OBJECT_POSE_SERVICE, self.get_object_pose_client),
            (CONTROL_HAND_SERVICE, self.control_hand_client),
            (ATTACH_OBJECT_SERVICE, self.attach_object_client),
            (DETACH_OBJECT_SERVICE, self.detach_object_client),
            (
                EXECUTE_TERMINAL_OPERATION_SERVICE,
                self.execute_terminal_operation_client,
            ),
        ]
        for service_name, client in service_clients:
            self.assertTrue(
                client.wait_for_service(timeout_sec=15.0),
                f'{service_name} service is not available:\n'
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
        """在指定时间内确认 launch 进程没有提前退出。"""
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self.launch_process.poll() is not None:
                return False
            time.sleep(0.1)
        return self.launch_process.poll() is None

    def _wait_for_task_state_publisher(self, timeout_sec):
        """等待 /assembly/task_state 出现 publisher。"""
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if self.node.count_publishers(TASK_STATE_TOPIC) > 0:
                return True
            if self.launch_process.poll() is not None:
                return False
            time.sleep(0.1)
        return False

    def _assert_start_task_rejects_empty_task_name(self):
        """空 task_name 应被明确拒绝。"""
        response = self._call_start_task('')
        self.assertFalse(response.accepted)
        self.assertEqual(response.task_id, '')
        self.assertEqual(response.error_code, 3001)
        self.assertEqual(response.message, 'task_name must not be empty')

    def _assert_start_task_rejects_unsupported_task_name(self):
        """未知 task_name 应被明确拒绝。"""
        response = self._call_start_task('unknown_task')
        self.assertFalse(response.accepted)
        self.assertEqual(response.task_id, '')
        self.assertEqual(response.error_code, 3002)
        self.assertEqual(response.message, 'unsupported task_name')

    def _assert_mvp0_home_still_passes(self):
        """MVP-1 launch 下仍应兼容 MVP-0 的 mvp0_home 任务。"""
        response = self._call_start_task(MVP0_TASK_NAME)
        self.assertTrue(response.accepted)
        self.assertTrue(response.task_id)
        self.assertEqual(response.error_code, 0)
        self.assertEqual(response.message, 'Task accepted')

        final_state = self._wait_for_state(response.task_id, 'SUCCESS')
        self.assertEqual(final_state.error_code, 0)
        self.assertAlmostEqual(final_state.progress, 1.0, places=4)
        self._assert_state_sequence(response.task_id, MVP0_SUCCESS_SEQUENCE)

    def _run_pick_and_place_once(self):
        """执行一次 MVP-1 任务，并断言状态序列和最终物体位置。"""
        response = self._call_start_task(MVP1_TASK_NAME)
        self.assertTrue(response.accepted)
        self.assertTrue(response.task_id)
        self.assertEqual(response.error_code, 0)
        self.assertEqual(response.message, 'Task accepted')

        final_state = self._wait_for_state(
            response.task_id,
            'SUCCESS',
            timeout_sec=20.0,
        )
        self.assertEqual(final_state.error_code, 0)
        self.assertAlmostEqual(final_state.progress, 1.0, places=4)
        self._assert_state_sequence(response.task_id, MVP1_SUCCESS_SEQUENCE)
        self._assert_object_is_in_place_zone()
        return response

    def _call_start_task(self, task_name, timeout_sec=5.0):
        """调用 StartTask service。"""
        request = StartTask.Request()
        request.task_name = task_name
        future = self.start_task_client.call_async(request)
        self.assertTrue(
            self._wait_for_future(future, timeout_sec),
            f'timed out waiting for StartTask response for {task_name!r}',
        )
        return future.result()

    def _call_get_object_pose(self, object_id, timeout_sec=5.0):
        """调用 GetObjectPose service。"""
        request = GetObjectPose.Request()
        request.object_id = object_id
        future = self.get_object_pose_client.call_async(request)
        self.assertTrue(
            self._wait_for_future(future, timeout_sec),
            f'timed out waiting for GetObjectPose response for {object_id!r}',
        )
        return future.result()

    def _wait_for_future(self, future, timeout_sec):
        """等待 ROS 异步调用完成。"""
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            if future.done():
                return True
            if self.launch_process.poll() is not None:
                return False
            time.sleep(0.05)
        return future.done()

    def _wait_for_state(self, task_id, expected_state, timeout_sec=10.0):
        """等待某个 task_id 发布指定状态。"""
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

        seen_states = [
            state.current_state for state in self._states_for(task_id)
        ]
        self.fail(
            f'timed out waiting for {expected_state!r} for {task_id!r}; '
            f'seen states: {seen_states}\n'
            f'{self._launch_output_tail()}',
        )

    def _latest_state(self, task_id, expected_state):
        """从已收到的状态里找最近一个匹配项。"""
        for state in reversed(self.states):
            if (
                state.task_id == task_id
                and state.current_state == expected_state
            ):
                return state
        return None

    def _assert_state_sequence(self, task_id, expected_sequence):
        """断言任务状态序列完整且顺序严格匹配。"""
        actual_sequence = [
            state.current_state for state in self._states_for(task_id)
        ]
        self.assertEqual(actual_sequence, expected_sequence)

        states = self._states_for(task_id)
        for index, state in enumerate(states):
            expected_previous = (
                'IDLE' if index == 0 else states[index - 1].current_state
            )
            self.assertEqual(state.previous_state, expected_previous)
            self.assertEqual(state.error_code, 0)

    def _assert_object_is_in_place_zone(self):
        """断言 fake 场景中的 MVP 物体已经释放到 place_zone。"""
        response = self._call_get_object_pose(MVP_OBJECT_ID)
        self.assertTrue(response.success)
        self.assertEqual(response.object_location, MVP1_TARGET_LOCATION)
        self.assertFalse(response.object_attached)
        self.assertEqual(response.attached_link, '')
        self.assertEqual(response.error_code, 0)

    def _states_for(self, task_id):
        """按 task_id 过滤状态消息。"""
        with self.states_condition:
            return [
                state for state in self.states
                if state.task_id == task_id
            ]

    def _task_numbers(self, task_ids):
        """从 task_id 末尾提取递增编号。"""
        return [int(task_id.rsplit('_', 1)[1]) for task_id in task_ids]

    def _launch_output_tail(self, line_count=80):
        """返回 launch 输出尾部，方便定位失败原因。"""
        return ''.join(self.launch_output[-line_count:])
