// MoveIt 场景管理器服务节点。

#include <memory>
#include <string>
#include <vector>

#include "geometry_msgs/msg/pose.hpp"
#include "moveit/planning_scene_interface/planning_scene_interface.h"
#include "moveit_msgs/msg/attached_collision_object.hpp"
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
        get_object_pose_service_name,
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
          handle_attach_object(request, response);
        });
    RCLCPP_INFO(get_logger(), "attach_object_server started, service=%s",
                attach_object_service_name.c_str());

    detach_object_server_ = this->create_service<DetachObject>(
        detach_object_service_name,
        [this](const std::shared_ptr<DetachObject::Request> request,
               std::shared_ptr<DetachObject::Response> response) {
          handle_detach_object(request, response);
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
  bool object_exists = false;
  bool object_attached = false;
  std::string attached_link;
  std::string object_location;
  static constexpr int SUCCESS = 0;
  static constexpr int EMPTY_TASK_ID_ERROR = 1001;
  static constexpr int EMPTY_OBJECT_ID_ERROR = 5001;
  static constexpr int OBJECT_NOT_EXIST_ERROR = 5002;
  static constexpr int WHEN_ATTACH_OBJECT_HAS_BEEN_ATTACH_ERROR = 5003;
  static constexpr int WHEN_DETACH_OBJECT_HAS_BEEN_DETACH_ERROR = 5004;
  static constexpr int EMPTY_LINK_ERROR = 5005;
  static constexpr int EMPTY_TARGET_LOCATION_ERROR = 5006;
  static constexpr int PLANNING_SCENE_UPDATE_ERROR = 6001;

  rclcpp::Service<ResetScene>::SharedPtr scene_reset_server_;
  rclcpp::Service<GetObjectPose>::SharedPtr get_object_pose_server_;
  rclcpp::Service<AttachObject>::SharedPtr attach_object_server_;
  rclcpp::Service<DetachObject>::SharedPtr detach_object_server_;

  // 操作 PlanningScene 的对象
  moveit::planning_interface::PlanningSceneInterface planning_scene_interface_;

  void handle_reset_scene(const std::shared_ptr<ResetScene::Request> request,
                          std::shared_ptr<ResetScene::Response> response) {
    // 1. 校验 task_id
    const auto task_id = request->task_id;
    if (task_id.empty()) {
      response->success = false;
      response->error_code = EMPTY_TASK_ID_ERROR;
      response->message = "task_id must not be empty.";
      return;
    }
    const auto mvp_object = make_mvp_object_at_pickup();
    // 4. 通过 PlanningSceneInterface 同步写入 MoveIt
    const bool applied =
        planning_scene_interface_.applyCollisionObject(mvp_object);
    // 5. 根据结果填写 response
    if (!applied) {
      response->success = false;
      response->error_code = PLANNING_SCENE_UPDATE_ERROR;
      response->message = "failed to add mvp_object to PlanningScene";
      return;
    }
    RCLCPP_INFO(
        get_logger(),
        "object_id=%s, object_location=%s, frame_id=%s, x=%f, y=%f, z=%f",
        "mvp_object", "pickup_zone", "fr3_link0",
        mvp_object.primitive_poses.front().position.x,
        mvp_object.primitive_poses.front().position.y,
        mvp_object.primitive_poses.front().position.z);

    object_exists = true;
    object_attached = false;
    attached_link.clear();
    object_location = "pickup_zone";
    response->success = true;
    response->error_code = SUCCESS;
    response->message = "mvp_object reset to pickup_zone";
  }
  void
  handle_attach_object(const std::shared_ptr<AttachObject::Request> request,
                       std::shared_ptr<AttachObject::Response> response) {
    const auto task_id = request->task_id;
    const auto object_id = request->object_id;
    const auto link_name = request->link_name;
    if (task_id.empty()) {
      response->success = false;
      response->error_code = EMPTY_TASK_ID_ERROR;
      response->message = "task_id must not be empty.";
      return;
    }
    if (object_id.empty()) {
      response->success = false;
      response->error_code = EMPTY_OBJECT_ID_ERROR;
      response->message = "object_id must not be empty.";
      return;
    }
    if (link_name.empty()) {
      response->success = false;
      response->error_code = EMPTY_LINK_ERROR;
      response->message = "attached link must not be empty.";
      return;
    }
    if (object_id != "mvp_object") {
      response->success = false;
      response->error_code = OBJECT_NOT_EXIST_ERROR;
      response->message = "invalid object_id or object not in ResetScene.";
      return;
    }
    const auto attached_objects =
        planning_scene_interface_.getAttachedObjects({object_id});
    const bool is_attached =
        attached_objects.find(object_id) != attached_objects.end();
    if (is_attached) {
      response->success = false;
      response->error_code = WHEN_ATTACH_OBJECT_HAS_BEEN_ATTACH_ERROR;
      response->message = "object is already attached";
      return;
    }

    const auto world_objects = planning_scene_interface_.getObjects({object_id});
    const auto world_object = world_objects.find(object_id);
    if (world_object == world_objects.end()) {
      response->success = false;
      response->error_code = OBJECT_NOT_EXIST_ERROR;
      response->message = "object is not in the world scene; call ResetScene first";
      return;
    }

    moveit_msgs::msg::AttachedCollisionObject attached_object;
    attached_object.link_name = link_name;
    attached_object.object = world_object->second;
    attached_object.object.operation = moveit_msgs::msg::CollisionObject::ADD;
    // MVP-2 只允许请求的末端 link 与被抓物体接触。
    attached_object.touch_links = {link_name};

    if (!planning_scene_interface_.applyAttachedCollisionObject(attached_object)) {
      response->success = false;
      response->error_code = PLANNING_SCENE_UPDATE_ERROR;
      response->message = "failed to attach mvp_object to PlanningScene";
      return;
    }

    const auto confirmed_attached_objects =
        planning_scene_interface_.getAttachedObjects({object_id});
    if (confirmed_attached_objects.find(object_id) ==
        confirmed_attached_objects.end()) {
      response->success = false;
      response->error_code = PLANNING_SCENE_UPDATE_ERROR;
      response->message = "mvp_object attach was not confirmed by PlanningScene";
      return;
    }

    object_exists = true;
    object_attached = true;
    attached_link = link_name;
    object_location = "attached";
    response->success = true;
    response->error_code = SUCCESS;
    response->message = "mvp_object attached successfully";
  }

  void
  handle_detach_object(const std::shared_ptr<DetachObject::Request> request,
                       std::shared_ptr<DetachObject::Response> response) {
    const auto task_id = request->task_id;
    const auto object_id = request->object_id;
    const auto target_location = request->target_location;
    if (task_id.empty()) {
      response->success = false;
      response->error_code = EMPTY_TASK_ID_ERROR;
      response->message = "task_id must not be empty.";
      return;
    }
    if (object_id.empty()) {
      response->success = false;
      response->error_code = EMPTY_OBJECT_ID_ERROR;
      response->message = "object_id must not be empty.";
      return;
    }
    if (target_location.empty()) {
      response->success = false;
      response->error_code = EMPTY_TARGET_LOCATION_ERROR;
      response->message = "target_location must not be empty.";
      return;
    }
    if (object_id != "mvp_object") {
      response->success = false;
      response->error_code = OBJECT_NOT_EXIST_ERROR;
      response->message = "invalid object_id or object not in ResetScene.";
      return;
    }

    const auto attached_objects =
        planning_scene_interface_.getAttachedObjects({object_id});
    if (attached_objects.find(object_id) == attached_objects.end()) {
      response->success = false;
      response->error_code = WHEN_DETACH_OBJECT_HAS_BEEN_DETACH_ERROR;
      response->message = "object is not attached";
      return;
    }

    moveit_msgs::msg::AttachedCollisionObject remove_attached_object;
    remove_attached_object.link_name = attached_objects.at(object_id).link_name;
    remove_attached_object.object.id = object_id;
    remove_attached_object.object.operation =
        moveit_msgs::msg::CollisionObject::REMOVE;
    if (!planning_scene_interface_.applyAttachedCollisionObject(
            remove_attached_object)) {
      response->success = false;
      response->error_code = PLANNING_SCENE_UPDATE_ERROR;
      response->message = "failed to detach mvp_object from PlanningScene";
      return;
    }

    const auto world_object = make_mvp_object_at_place();
    if (!planning_scene_interface_.applyCollisionObject(world_object)) {
      response->success = false;
      response->error_code = PLANNING_SCENE_UPDATE_ERROR;
      response->message = "failed to return mvp_object to the world scene";
      return;
    }

    const auto world_objects = planning_scene_interface_.getObjects({object_id});
    if (world_objects.find(object_id) == world_objects.end()) {
      response->success = false;
      response->error_code = PLANNING_SCENE_UPDATE_ERROR;
      response->message = "mvp_object world update was not confirmed by PlanningScene";
      return;
    }

    object_exists = true;
    object_attached = false;
    attached_link.clear();
    object_location = target_location;
    response->success = true;
    response->error_code = SUCCESS;
    response->message = "mvp_object detached successfully";
  }

  moveit_msgs::msg::CollisionObject make_mvp_object_at_pickup() {
    return make_mvp_object_at(0.45, 0.00, 0.15);
  }

  moveit_msgs::msg::CollisionObject make_mvp_object_at_place() {
    // MVP-2 当前只将逻辑 target_location 映射到固定的 place_zone 位姿。
    return make_mvp_object_at(0.45, -0.20, 0.15);
  }

  moveit_msgs::msg::CollisionObject make_mvp_object_at(double x, double y,
                                                        double z) {
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

    geometry_msgs::msg::Pose pose;
    pose.position.x = x;
    pose.position.y = y;
    pose.position.z = z;
    pose.orientation.w = 1.0;
    mvp_object.primitive_poses.push_back(pose);
    return mvp_object;
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
