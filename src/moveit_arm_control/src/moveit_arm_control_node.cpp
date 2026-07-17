// MoveIt 机械臂控制 Action 节点。

#include <algorithm>
#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "assembly_interfaces/action/move_arm.hpp"
#include "moveit/move_group_interface/move_group_interface.h"
#include "moveit_msgs/action/move_group.hpp"
#include "rclcpp/rclcpp.hpp"
#include "rclcpp_action/rclcpp_action.hpp"

namespace moveit_arm_control {

class MoveItArmControlNode : public rclcpp::Node {
public:
  using MoveArm = assembly_interfaces::action::MoveArm;
  using GoalHandleMoveArm = rclcpp_action::ServerGoalHandle<MoveArm>;
  using MoveGroupInterface = moveit::planning_interface::MoveGroupInterface;

  MoveItArmControlNode() : Node("moveit_arm_control_node") {
    move_arm_action_server_ = rclcpp_action::create_server<MoveArm>(
        this, ACTION_NAME,
        [this](const rclcpp_action::GoalUUID &uuid,
               std::shared_ptr<const MoveArm::Goal> goal) {
          return handle_goal(uuid, goal);
        },
        [this](const std::shared_ptr<GoalHandleMoveArm> goal_handle) {
          return handle_cancel(goal_handle);
        },
        [this](const std::shared_ptr<GoalHandleMoveArm> goal_handle) {
          handle_accepted(goal_handle);
        });

    RCLCPP_INFO(get_logger(), "moveit_arm_control started, action=%s",
                ACTION_NAME.c_str());
  }

  bool initialize_move_group() {
    // 做两轮验证，先检查 /move_group 是否存在，
    // 再捕获 MoveGroupInterface构造异常。

    // shared_from_this() 的作用是：从当前对象 this 获取一个指向自身的
    // std::shared_ptr。
    auto move_group_action_client =
        rclcpp_action::create_client<moveit_msgs::action::MoveGroup>(
            shared_from_this(), "move_group");

    // 检查 /move_group 是否存在
    if (!move_group_action_client->wait_for_action_server(
            std::chrono::duration<double>(MOVEIT_SERVER_WAIT_SEC))) {
      RCLCPP_ERROR(get_logger(),
                   "MoveIt move_group action server is unavailable");
      return false;
    }

    try {
      // 创建一个 MoveGroupInterface 对象，并告诉它：
      // 请操作 robot model 中名为 fr3_arm 的规划组。
      // 规划组本身来自 MoveIt 的机器人模型和 SRDF。
      // 构造这个对象时，MoveIt 可能需要：
      // 加载 robot_description
      // 加载 robot_description_semantic
      // 查找 fr3_arm 规划组
      // 创建 /move_group Action Client
      // 初始化 TF 和机器人状态监视器
      // 读取规划相关参数
      // 这些都是运行时操作，任何一项失败都可能导致构造失败.
      // 没有 catch 时，异常会继续向上传播，最终可能导致整个节点退出。
      // 有了 catch，节点可以保留 Action
      // Server，并在收到请求时返回错误信息和错误代码。
      move_group_ = std::make_shared<MoveGroupInterface>(
          shared_from_this(), PLANNING_GROUP, nullptr,
          rclcpp::Duration::from_seconds(MOVEIT_SERVER_WAIT_SEC));
    } catch (const std::exception &exception) {
      RCLCPP_ERROR(get_logger(), "failed to initialize MoveIt: %s",
                   exception.what());
      return false;
    }

    if (!move_group_->getMoveGroupClient().action_server_is_ready()) {
      RCLCPP_ERROR(get_logger(),
                   "MoveIt move_group action server is unavailable");
      move_group_.reset();
      return false;
    }

    moveit_available_ = true;
    RCLCPP_INFO(get_logger(),
                "MoveGroupInterface initialized, planning_group=%s",
                PLANNING_GROUP.c_str());
    return true;
  }

private:
  static inline const std::string ACTION_NAME = "/assembly/move_arm";
  static inline const std::string SUPPORTED_ARM = "right_arm";
  static inline const std::string PLANNING_GROUP = "fr3_arm";
  static inline const std::vector<std::string> SUPPORTED_TARGETS = {
      "home", "pregrasp", "grasp", "lift", "preplace", "place", "retreat",
  };

  static constexpr int SUCCESS = 0;
  static constexpr int UNSUPPORTED_ARM_ERROR = 2001;
  static constexpr int UNSUPPORTED_TARGET_ERROR = 2002;
  static constexpr int INVALID_TIMEOUT_ERROR = 2003;
  static constexpr int MOVEIT_TARGET_MAPPING_ERROR = 2004;
  static constexpr int MOVEIT_UNAVAILABLE_ERROR = 2005;
  static constexpr int PLANNING_FAILED_ERROR = 2006;
  static constexpr int EXECUTION_FAILED_ERROR = 2007;
  static constexpr int EXECUTION_TIMEOUT_ERROR = 2008;
  static constexpr double MOVEIT_SERVER_WAIT_SEC = 5.0;

  rclcpp_action::Server<MoveArm>::SharedPtr move_arm_action_server_;
  std::shared_ptr<MoveGroupInterface> move_group_;
  // 互斥锁对象 mutex
  std::mutex move_group_mutex_;
  bool moveit_available_{false};

  rclcpp_action::GoalResponse
  handle_goal(const rclcpp_action::GoalUUID &,
              std::shared_ptr<const MoveArm::Goal> goal) {
    RCLCPP_INFO(
        get_logger(),
        "move_arm goal received: arm_name=%s target_name=%s timeout_sec=%.2f",
        goal->arm_name.c_str(), goal->target_name.c_str(), goal->timeout_sec);

    return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
  }

  rclcpp_action::CancelResponse
  handle_cancel(const std::shared_ptr<GoalHandleMoveArm>) {
    RCLCPP_INFO(get_logger(), "move_arm cancel requested");
    return rclcpp_action::CancelResponse::ACCEPT;
  }

  void handle_accepted(const std::shared_ptr<GoalHandleMoveArm> goal_handle) {
    std::thread{
        std::bind(&MoveItArmControlNode::execute, this, std::placeholders::_1),
        goal_handle}
        .detach();
  }

  void execute(const std::shared_ptr<GoalHandleMoveArm> goal_handle) {
    const auto goal = goal_handle->get_goal();

    const auto validation_result = validate_goal(*goal);
    if (validation_result != nullptr) {
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(validation_result);
      return;
    }

    publish_feedback(goal_handle, "accepted", 0.0);
    const auto moveit_target = resolve_moveit_target(goal->target_name);

    if (moveit_target.empty()) {
      auto result = make_result(false, MOVEIT_TARGET_MAPPING_ERROR,
                                "target has no MoveIt mapping yet!");
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(result);
      return;
    }
    RCLCPP_INFO(get_logger(), "logical target=%s mapped to MoveIt target=%s",
                goal->target_name.c_str(), moveit_target.c_str());

    if (!moveit_available_ || move_group_ == nullptr) {
      auto result =
          make_result(false, MOVEIT_UNAVAILABLE_ERROR, "MoveIt is unavailable");
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(result);
      return;
    }

    if (goal_handle->is_canceling()) {
      auto result = make_result(false, EXECUTION_FAILED_ERROR,
                                "goal canceled before planning");
      goal_handle->canceled(result);
      return;
    }

    std::lock_guard<std::mutex> lock(move_group_mutex_);
    move_group_->setPlanningTime(static_cast<double>(goal->timeout_sec));

    if (!move_group_->setNamedTarget(moveit_target)) {
      auto result = make_result(false, PLANNING_FAILED_ERROR,
                                "MoveIt named target is unavailable");
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(result);
      return;
    }

    publish_feedback(goal_handle, "planning", 0.25);
    const auto start_time = std::chrono::steady_clock::now();
    MoveGroupInterface::Plan plan;
    const auto planning_result = move_group_->plan(plan);
    if (planning_result != moveit::core::MoveItErrorCode::SUCCESS) {
      auto result =
          make_result(false, PLANNING_FAILED_ERROR, "MoveIt planning failed");
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(result);
      return;
    }

    const auto planning_elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start_time);
    if (planning_elapsed.count() >= goal->timeout_sec) {
      auto result = make_result(false, EXECUTION_TIMEOUT_ERROR,
                                "MoveIt planning exceeded timeout");
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(result);
      return;
    }

    if (goal_handle->is_canceling()) {
      move_group_->stop();
      auto result = make_result(false, EXECUTION_FAILED_ERROR,
                                "goal canceled before execution");
      goal_handle->canceled(result);
      return;
    }

    publish_feedback(goal_handle, "executing", 0.5);
    const auto execution_result = move_group_->execute(plan);
    if (execution_result != moveit::core::MoveItErrorCode::SUCCESS) {
      auto result =
          make_result(false, EXECUTION_FAILED_ERROR, "MoveIt execution failed");
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(result);
      return;
    }

    const auto total_elapsed = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - start_time);
    if (total_elapsed.count() >= goal->timeout_sec) {
      auto result = make_result(false, EXECUTION_TIMEOUT_ERROR,
                                "MoveIt execution exceeded timeout");
      publish_feedback(goal_handle, "failed", 1.0);
      goal_handle->abort(result);
      return;
    }

    publish_feedback(goal_handle, "succeeded", 1.0);
    goal_handle->succeed(
        make_result(true, SUCCESS, "MoveIt target executed successfully"));
  }

  std::shared_ptr<MoveArm::Result>
  validate_goal(const MoveArm::Goal &goal) const {
    // 对传入的 goal 进行错误处理
    if (goal.timeout_sec <= 0.0F) {
      return make_result(false, INVALID_TIMEOUT_ERROR,
                         "timeout_sec must be positive");
    }

    if (goal.arm_name != SUPPORTED_ARM) {
      return make_result(false, UNSUPPORTED_ARM_ERROR, "unsupported arm_name");
    }

    if (std::find(SUPPORTED_TARGETS.begin(), SUPPORTED_TARGETS.end(),
                  goal.target_name) == SUPPORTED_TARGETS.end()) {
      return make_result(false, UNSUPPORTED_TARGET_ERROR,
                         "unsupported target_name");
    }

    return nullptr;
  }

  std::string resolve_moveit_target(const std::string &target_name) {
    // 把传入的 target_name 映射成 moveit target name
    if (target_name == "home" || target_name == "retreat") {
      return "ready";
    }
    if (target_name == "pregrasp") {
      return "extended";
    }
    return "";
  }

  void publish_feedback(const std::shared_ptr<GoalHandleMoveArm> goal_handle,
                        const std::string &current_state,
                        const float progress) const {
    auto feedback = std::make_shared<MoveArm::Feedback>();
    feedback->current_state = current_state;
    feedback->progress = progress;
    goal_handle->publish_feedback(feedback);
  }

  std::shared_ptr<MoveArm::Result>
  make_result(const bool success, const int error_code,
              const std::string &message) const {
    auto result = std::make_shared<MoveArm::Result>();
    result->success = success;
    result->error_code = error_code;
    result->message = message;
    return result;
  }
};

} // namespace moveit_arm_control

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  // 一个节点同时作为上游服务器和下游客户端。对上提供统一接口，对下调用具体控制框架。
  // 一个 ROS 2 节点不是只能拥有一个通信角色。
  // 节点更像一个通信容器，可以同时拥有各种服务端、客户端、发布者、订阅者等
  auto node = std::make_shared<moveit_arm_control::MoveItArmControlNode>();
  node->initialize_move_group();
  // 持续运行节点，不断处理 ros2 通信事件
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
