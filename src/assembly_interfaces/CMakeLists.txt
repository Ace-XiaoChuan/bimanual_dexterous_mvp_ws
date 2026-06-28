cmake_minimum_required(VERSION 3.8)
project(assembly_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/TaskState.msg"
  "srv/AttachObject.srv"
  "srv/ControlHand.srv"
  "srv/DetachObject.srv"
  "srv/ExecuteTerminalOperation.srv"
  "srv/GetObjectPose.srv"
  "srv/ResetScene.srv"
  "srv/StartTask.srv"
  "action/MoveArm.action"
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # Avoid network access to the ROS package XML schema in restricted CI.
  set(ament_cmake_xmllint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
