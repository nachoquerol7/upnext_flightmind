cmake_minimum_required(VERSION 3.16)
project(daidalus_node)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_gtest REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(flightmind_msgs REQUIRED)

add_library(synthetic_daa STATIC src/synthetic_daa.cpp)
target_include_directories(synthetic_daa PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

add_executable(daidalus_node src/daidalus_node.cpp)
target_link_libraries(daidalus_node synthetic_daa)
ament_target_dependencies(daidalus_node rclcpp std_msgs flightmind_msgs)

install(TARGETS daidalus_node DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY config DESTINATION share/${PROJECT_NAME}/)

ament_add_gtest(test_synthetic_daa test/test_synthetic_daa.cpp)
if(TARGET test_synthetic_daa)
  target_link_libraries(test_synthetic_daa synthetic_daa)
  target_include_directories(test_synthetic_daa PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)
endif()

ament_package()
