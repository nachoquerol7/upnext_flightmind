cmake_minimum_required(VERSION 3.16)
project(acas_node)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_gtest REQUIRED)
find_package(ament_index_cpp REQUIRED)
find_package(flightmind_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)

add_library(acas_nnet STATIC src/nnet_loader.cpp)
target_include_directories(acas_nnet PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

add_executable(acas_node_exe src/acas_node.cpp)
target_link_libraries(acas_node_exe acas_nnet)
ament_target_dependencies(acas_node_exe rclcpp flightmind_msgs std_msgs ament_index_cpp)
set_target_properties(acas_node_exe PROPERTIES OUTPUT_NAME acas_node)

install(TARGETS acas_node_exe DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY config launch DESTINATION share/${PROJECT_NAME}/)
install(DIRECTORY nnets DESTINATION share/${PROJECT_NAME}/)

ament_add_gtest(test_nnet_loader test/test_nnet_loader.cpp)
if(TARGET test_nnet_loader)
  target_link_libraries(test_nnet_loader acas_nnet)
  target_include_directories(test_nnet_loader PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)
endif()

ament_add_gtest(test_acas_neural test/test_acas_neural.cpp)
if(TARGET test_acas_neural)
  target_link_libraries(test_acas_neural acas_nnet)
endif()

ament_package()
