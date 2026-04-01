#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "daidalus_node/synthetic_daa.hpp"
#include <flightmind_msgs/msg/traffic_report.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>
#include <std_msgs/msg/int32.hpp>

using std_msgs::msg::Float64MultiArray;
using std_msgs::msg::Int32;

class DaidalusNode : public rclcpp::Node
{
public:
  DaidalusNode()
  : rclcpp::Node("daidalus_node")
  {
    declare_parameter("lookahead_time_s", 180.0);
    declare_parameter("alerting_time_s", 55.0);
    declare_parameter("dmod_m", 2200.0);
    declare_parameter("zthr_ft", 450.0);
    declare_parameter("turn_rate_degps", 3.0);
    declare_parameter("red_time_s", 25.0);
    declare_parameter("use_daidalus_lib", false);

    pub_bands_ = create_publisher<Float64MultiArray>("/daidalus/bands_summary", 10);
    pub_alert_ = create_publisher<Int32>("/daidalus/alert_level", 10);
    pub_ra_ = create_publisher<Float64MultiArray>("/daidalus/resolution_advisory", 10);
    pub_hb_ = create_publisher<std_msgs::msg::Bool>("/daidalus/heartbeat", 10);

    sub_own_ = create_subscription<Float64MultiArray>(
      "/ownship/state", 10,
      std::bind(&DaidalusNode::on_ownship, this, std::placeholders::_1));

    sub_traffic_ = create_subscription<flightmind_msgs::msg::TrafficReport>(
      "/traffic/intruders", 10,
      std::bind(&DaidalusNode::on_traffic, this, std::placeholders::_1));

    timer_ = create_wall_timer(
      std::chrono::milliseconds(100),
      std::bind(&DaidalusNode::tick, this));

    hb_timer_ = create_wall_timer(
      std::chrono::seconds(1),
      std::bind(&DaidalusNode::publish_heartbeat, this));

    RCLCPP_INFO(
      get_logger(),
      "daidalus_node: synthetic DAA (DAIDALUS lib optional, use_daidalus_lib=false)");
  }

private:
  void on_ownship(const Float64MultiArray::SharedPtr msg)
  {
    if (msg->data.size() < 6U) {
      RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 5000, "ownship/state needs 6 fields");
      return;
    }
    own_.n = msg->data[0];
    own_.e = msg->data[1];
    own_.z = msg->data[2];
    own_.vn = msg->data[3];
    own_.ve = msg->data[4];
    own_.vd = msg->data[5];
    have_own_ = true;
  }

  void on_traffic(const flightmind_msgs::msg::TrafficReport::SharedPtr msg)
  {
    intruders_.clear();
    for (const auto &i : msg->intruders) {
      daidalus_node::IntruderState s;
      s.id = static_cast<uint32_t>(std::hash<std::string>{}(i.intruder_id));
      s.n = i.position_ned[0];
      s.e = i.position_ned[1];
      s.z = i.position_ned[2];
      s.vn = i.velocity_ned[0];
      s.ve = i.velocity_ned[1];
      s.vd = i.velocity_ned[2];
      intruders_.push_back(s);
    }
    have_traffic_ = true;
  }

  void publish_heartbeat()
  {
    std_msgs::msg::Bool m;
    m.data = true;
    pub_hb_->publish(m);
  }

  void tick()
  {
    if (!have_own_) {
      return;
    }
    daidalus_node::SyntheticDaaParams p;
    p.lookahead_time_s = get_parameter("lookahead_time_s").as_double();
    p.alerting_time_s = get_parameter("alerting_time_s").as_double();
    p.dmod_m = get_parameter("dmod_m").as_double();
    p.zthr_m = get_parameter("zthr_ft").as_double() * 0.3048;
    p.turn_rate_degps = get_parameter("turn_rate_degps").as_double();
    p.red_time_s = get_parameter("red_time_s").as_double();

    const bool use_lib = get_parameter("use_daidalus_lib").as_bool();
    (void)use_lib;

    auto out = daidalus_node::run_synthetic_daa(own_, intruders_, p);

    Float64MultiArray bands;
    bands.layout.dim.resize(1);
    bands.layout.dim[0].label = "bands_summary";
    bands.layout.dim[0].size = 3;
    bands.layout.dim[0].stride = 3;
    bands.data = {out.num_conflict, out.min_h, out.min_v};
    pub_bands_->publish(bands);

    Int32 al;
    al.data = out.alert_level;
    pub_alert_->publish(al);

    Float64MultiArray ra;
    ra.layout.dim.resize(1);
    ra.layout.dim[0].label = "resolution_advisory";
    ra.layout.dim[0].size = 3;
    ra.layout.dim[0].stride = 3;
    ra.data = {out.ra_hdg_deg, out.ra_gs_mps, out.ra_vs_mps};
    pub_ra_->publish(ra);
  }

  daidalus_node::OwnshipState own_{};
  std::vector<daidalus_node::IntruderState> intruders_;
  bool have_own_{false};
  bool have_traffic_{false};

  rclcpp::Publisher<Float64MultiArray>::SharedPtr pub_bands_;
  rclcpp::Publisher<Int32>::SharedPtr pub_alert_;
  rclcpp::Publisher<Float64MultiArray>::SharedPtr pub_ra_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr pub_hb_;
  rclcpp::Subscription<Float64MultiArray>::SharedPtr sub_own_;
  rclcpp::Subscription<flightmind_msgs::msg::TrafficReport>::SharedPtr sub_traffic_;
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::TimerBase::SharedPtr hb_timer_;
};

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<DaidalusNode>());
  rclcpp::shutdown();
  return 0;
}
