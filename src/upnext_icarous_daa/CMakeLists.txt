cmake_minimum_required(VERSION 3.16)
project(upnext_icarous_daa)

set(CMAKE_CXX_STANDARD 17)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(px4_msgs REQUIRED)
find_package(std_msgs REQUIRED)

# ICAROUS checkout: workspace/third_party/icarous (from this file: ../../..)
set(ICAROUS_HOME "${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/icarous" CACHE PATH "ICAROUS root")

if(NOT EXISTS "${ICAROUS_HOME}/Modules/lib/libTrafficMonitor.so")
  message(FATAL_ERROR "ICAROUS Modules not built. Build: cd ${ICAROUS_HOME}/Modules/build && cmake .. && make")
endif()

include_directories(
  ${ICAROUS_HOME}/Modules/Core/TrafficMonitor
  ${ICAROUS_HOME}/Modules/Core/Interfaces
  ${ICAROUS_HOME}/Modules
)

link_directories(${ICAROUS_HOME}/Modules/lib)

add_executable(daa_traffic_monitor_node src/daa_traffic_monitor_node.cpp)
ament_target_dependencies(daa_traffic_monitor_node rclcpp px4_msgs std_msgs)
target_link_libraries(daa_traffic_monitor_node TrafficMonitor ACCoRD)

set_target_properties(daa_traffic_monitor_node PROPERTIES
  INSTALL_RPATH "${ICAROUS_HOME}/Modules/lib"
  BUILD_WITH_INSTALL_RPATH TRUE
)

install(TARGETS daa_traffic_monitor_node DESTINATION lib/${PROJECT_NAME})
install(
  PROGRAMS
    scripts/fake_px4_for_daa_test
    scripts/daa_demo_viz
    scripts/px4_sitl_takeoff
    scripts/px4_sitl_set_offboard
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY config DESTINATION share/${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(DIRECTORY meshes DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  # Primer test de integración: fake PX4 + TrafficMonitor (sin Gazebo)
  ament_add_test(
    test_daa_fake_stack
    COMMAND bash "${CMAKE_CURRENT_SOURCE_DIR}/test/test_daa_fake_stack.sh"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../.."
    TIMEOUT 180
    GENERATE_RESULT_FOR_RETURN_CODE_ZERO
  )
endif()

ament_package()
