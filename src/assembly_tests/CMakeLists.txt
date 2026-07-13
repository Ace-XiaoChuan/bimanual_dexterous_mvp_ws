cmake_minimum_required(VERSION 3.8)
project(assembly_tests)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)

  file(MAKE_DIRECTORY "${CMAKE_BINARY_DIR}/ros_logs")
  ament_add_pytest_test(
    mvp0_task_flow
    test/test_mvp0_task_flow.py
    TIMEOUT 150
    ENV
      "ROS_LOG_DIR=${CMAKE_BINARY_DIR}/ros_logs"
  )
  ament_add_pytest_test(
    mvp1_pick_and_place_flow
    test/test_mvp1_pick_and_place_flow.py
    TIMEOUT 300
    ENV
      "ROS_LOG_DIR=${CMAKE_BINARY_DIR}/ros_logs"
  )

  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  # Avoid network access to the ROS package XML schema in restricted CI.
  set(ament_cmake_xmllint_FOUND TRUE)
  # Keep educational Chinese docstrings without forcing pep257 punctuation.
  set(ament_cmake_pep257_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
