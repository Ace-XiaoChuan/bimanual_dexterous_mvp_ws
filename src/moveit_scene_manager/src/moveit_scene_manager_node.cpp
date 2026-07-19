// MoveIt 场景管理器服务节点。

#include <algorithm>
#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "geometry_msgs/msg/pose.hpp"
#include "moveit/planning_scene_interface/planning_scene_interface.h"
#include "moveit_msgs/action/move_group.hpp"
#include "moveit_msgs/msg/collision_object.hpp"
#include "rclcpp/rclcpp.hpp"
#include "shape_msgs/msg/solid_primitive.hpp"

#include "assembly_interfaces/srv/attach_object.hpp"
#include "assembly_interfaces/srv/detach_object.hpp"
#include "assembly_interfaces/srv/get_object_pose.hpp"
#include "assembly_interfaces/srv/reset_scene.hpp"

namespace moveit_scene_manager {
class MoveItSceneManagerNode : public rclcpp::Node {
public:
  using AttachObject = assembly_interfaces::srv::AttachObject;
  using DetachObject = assembly_interfaces::srv::DetachObject;
  using GetObjectPose = assembly_interfaces::srv::GetObjectPose;
  using ResetScene = assembly_interfaces::srv::ResetScene;

  MoveItSceneManagerNode() : Node("moveit_scene_manager_node") {

    scene_reset_server_ = this->create_service<ResetScene>(
        reset_scene_service_name,
        [this](const std::shared_ptr<ResetScene::Request> request,
               std::shared_ptr<ResetScene::Response> response) {
          handle_reset_scene(request, response);
        });
    RCLCPP_INFO(get_logger(), "scene_reset_server started, server=%s",
                SERVER_NAME.c_str());

    get_object_pose_server_ = this->create_service<GetObjectPose>(
        "/assembly/get_object_pose",
        [this](const std::shared_ptr<GetObjectPose::Request> request,
               std::shared_ptr<GetObjectPose::Response> response) {
          (void)request;
          response->success = false;
          response->error_code = 5002;
          response->message = "get object callback not implemented";
          RCLCPP_WARN(get_logger(),
                      "GetObjectPose service is registered, but its "
                      "implementation is not ready");
        });
    RCLCPP_INFO(get_logger(), "get_object_server started, server=%s",
                SERVER_NAME.c_str());

    attach_object_server_ = this->create_service<AttachObject>(
        attach_object_service_name,
        [this](const std::shared_ptr<AttachObject::Request> request,
               std::shared_ptr<AttachObject::Response> response) {
          (void)request;
          response->success = false;
          response->error_code = 9001;
          response->message = "attach object callback not implemented";
          RCLCPP_WARN(get_logger(), "AttachObject service is registered, but "
                                    "its implementation is not ready");
        });
    RCLCPP_INFO(get_logger(), "attach_object_server started, service=%s",
                attach_object_service_name.c_str());

    detach_object_server_ = this->create_service<DetachObject>(
        detach_object_service_name,
        [this](const std::shared_ptr<DetachObject::Request> request,
               std::shared_ptr<DetachObject::Response> response) {
          (void)request;
          response->success = false;
          response->error_code = 9001;
          response->message = "detach object callback not implemented";
          RCLCPP_WARN(get_logger(), "DetachObject service is registered, but "
                                    "its implementation is not ready");
        });
    RCLCPP_INFO(get_logger(), "detach_object_server started, service=%s",
                detach_object_service_name.c_str());
  };

private:
  static inline const std::string SERVER_NAME =
      "/assembly/moveit_scene_manager";
  static inline const std::string attach_object_service_name =
      "/assembly/attach_object";
  static inline const std::string detach_object_service_name =
      "/assembly/detach_object";
  static inline const std::string get_object_pose_service_name =
      "/assembly/get_object_pose";
  static inline const std::string reset_scene_service_name =
      "/assembly/reset_scene";
  static constexpr int SUCCESS = 0;
  static constexpr int EMPTY_TASK_ID_ERROR = 1001;
  static constexpr int EMPTY_OBJECT_ID_ERROR = 5001;
  static constexpr int OBJECT_NOT_EXIST_ERROR = 5002;
  static constexpr int WHEN_ATTACH_OBJECT_HAS_BEEN_ATTACH_ERROR = 5003;
  static constexpr int WHEN_DETACH_OBJECT_HAS_BEEN_DETACH_ERROR = 5004;
  static constexpr int PLANNING_SCENE_UPDATE_ERROR = 6001;
  static constexpr int NOT_IMPLEMENTED_ERROR = 9001;

  rclcpp::Service<ResetScene>::SharedPtr scene_reset_server_;
  rclcpp::Service<GetObjectPose>::SharedPtr get_object_pose_server_;
  rclcpp::Service<AttachObject>::SharedPtr attach_object_server_;
  rclcpp::Service<DetachObject>::SharedPtr detach_object_server_;

  // 操作 PlanningScene 的对象
  moveit::planning_interface::PlanningSceneInterface planning_scene_interface_;

  void handle_reset_scene(const std::shared_ptr<ResetScene::Request> request,
                          std::shared_ptr<ResetScene::Response> response) {
    // 应做以下流程：
    // 1. 校验 task_id
    // 2. 准备一个 mvp_object 的 CollisionObject
    // 3. 设置它的形状和 pickup_zone 对应的真实位姿
    // 4. 通过 PlanningSceneInterface 同步写入 MoveIt
    // 5. 根据结果填写 response
    const auto task_id = request->task_id;
    if (task_id.empty()) {
      response->success = false;
      response->error_code = EMPTY_TASK_ID_ERROR;
      response->message = "task_id must not be empty.";
      return;
    }
    moveit_msgs::msg::CollisionObject mvp_object;
    mvp_object.id = "mvp_object";
    mvp_object.header.frame_id = "fr3_link0";
    mvp_object.operation = moveit_msgs::msg::CollisionObject::ADD;

    shape_msgs::msg::SolidPrimitive box;
    box.type = shape_msgs::msg::SolidPrimitive::BOX;
    box.dimensions.resize(3);
    box.dimensions[shape_msgs::msg::SolidPrimitive::BOX_X] = 0.05;
    box.dimensions[shape_msgs::msg::SolidPrimitive::BOX_Y] = 0.05;
    box.dimensions[shape_msgs::msg::SolidPrimitive::BOX_Z] = 0.05;

    mvp_object.primitives.push_back(box);

    geometry_msgs::msg::Pose pickup_pose;

    pickup_pose.position.x = 0.45;
    pickup_pose.position.y = 0.00;
    pickup_pose.position.z = 0.15;
    pickup_pose.orientation.w = 1.0;

    mvp_object.primitive_poses.push_back(pickup_pose);

    const bool applied =
        planning_scene_interface_.applyCollisionObject(mvp_object);
    if (!applied) {
      response->success = false;
      response->error_code = PLANNING_SCENE_UPDATE_ERROR;
      response->message = "failed to add mvp_object to PlanningScene";
      return;
    }
    RCLCPP_INFO(
        get_logger(),
        "object_id=%s, object_location=%s, frame_id=%s, x=%f, y=%f, z=%f",
        "mvp_object", "pickup_zone", "fr3_link0", pickup_pose.position.x,
        pickup_pose.position.y, pickup_pose.position.z);

    response->success = true;
    response->error_code = SUCCESS;
    response->message = "mvp_object reset to pickup_zone";
  }
};
} // namespace moveit_scene_manager

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<moveit_scene_manager::MoveItSceneManagerNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
