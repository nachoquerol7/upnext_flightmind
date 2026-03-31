/**
 * Bridges PX4 (vehicle_global_position + vehicle_local_position) to ICAROUS
 * TrafficMonitor (DAIDALUS). Optional synthetic intruder offset in NED (m).
 */

#include <cmath>
#include <cstring>
#include <filesystem>
#include <memory>
#include <stdexcept>
#include <string>

#include "TrafficMonitor.h"
#include "px4_msgs/msg/vehicle_global_position.hpp"
#include "px4_msgs/msg/vehicle_local_position.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64_multi_array.hpp"

namespace {

constexpr double kEarthRadius = 6378137.0;

void ned_to_trk_gs_vs(double vn, double ve, double vd, double &trk_deg, double &gs, double &vs)
{
  trk_deg = std::atan2(ve, vn) * 180.0 / M_PI;
  gs = std::hypot(vn, ve);
  vs = -vd;
}

}  // namespace

class DaaTrafficMonitorNode : public rclcpp::Node
{
public:
  DaaTrafficMonitorNode()
  : Node("daa_traffic_monitor")
  {
    this->declare_parameter<std::string>("daa_config_file", "");
    this->declare_parameter<std::string>("topic_global", "/fmu/out/vehicle_global_position");
    this->declare_parameter<std::string>("topic_local", "/fmu/out/vehicle_local_position");
    this->declare_parameter<bool>("intruder_enable", true);
    this->declare_parameter<double>("intruder_n_m", 80.0);
    this->declare_parameter<double>("intruder_e_m", 0.0);
    this->declare_parameter<double>("intruder_vn", 0.0);
    this->declare_parameter<double>("intruder_ve", 0.0);
    this->declare_parameter<double>("intruder_vd", 0.0);
    this->declare_parameter<double>("rate_hz", 10.0);

    std::string cfg = this->get_parameter("daa_config_file").as_string();
    if (cfg.empty()) {
      RCLCPP_ERROR(this->get_logger(), "param daa_config_file is empty (path to DAA .txt)");
      throw std::runtime_error("daa_config_file required");
    }
    if (!std::filesystem::exists(cfg)) {
      RCLCPP_ERROR(this->get_logger(), "daa_config_file not found: %s", cfg.c_str());
      throw std::runtime_error("daa_config_file missing");
    }

    tm_ = newDaidalusTrafficMonitor("Ownship", cfg.c_str());
    if (!tm_) {
      throw std::runtime_error("newDaidalusTrafficMonitor failed");
    }

    std::memset(sigma_pos_, 0, sizeof(sigma_pos_));
    std::memset(sigma_vel_, 0, sizeof(sigma_vel_));

    const auto qos = rclcpp::SensorDataQoS().keep_last(10);

    sub_global_ = this->create_subscription<px4_msgs::msg::VehicleGlobalPosition>(
      this->get_parameter("topic_global").as_string(), qos,
      std::bind(&DaaTrafficMonitorNode::on_global, this, std::placeholders::_1));

    sub_local_ = this->create_subscription<px4_msgs::msg::VehicleLocalPosition>(
      this->get_parameter("topic_local").as_string(), qos,
      std::bind(&DaaTrafficMonitorNode::on_local, this, std::placeholders::_1));

    pub_bands_ = this->create_publisher<std_msgs::msg::Float64MultiArray>("~/daa/bands_summary", 10);

    double hz = this->get_parameter("rate_hz").as_double();
    if (hz < 1.0) {
      hz = 1.0;
    }
    timer_ = this->create_wall_timer(
      std::chrono::duration<double>(1.0 / hz),
      std::bind(&DaaTrafficMonitorNode::on_timer, this));

    RCLCPP_INFO(this->get_logger(), "ICAROUS TrafficMonitor ready, config=%s", cfg.c_str());
  }

  ~DaaTrafficMonitorNode() override
  {
    if (tm_) {
      delDaidalusTrafficMonitor(tm_);
      tm_ = nullptr;
    }
  }

private:
  void on_global(const px4_msgs::msg::VehicleGlobalPosition::SharedPtr m)
  {
    if (!m->lat_lon_valid) {
      return;
    }
    g_lat_ = m->lat;
    g_lon_ = m->lon;
    g_alt_ = static_cast<double>(m->alt);
    have_global_ = true;
    t_global_ = this->now();
  }

  void on_local(const px4_msgs::msg::VehicleLocalPosition::SharedPtr m)
  {
    if (!m->v_xy_valid) {
      return;
    }
    vn_ = m->vx;
    ve_ = m->vy;
    vd_ = m->vz;
    have_local_ = true;
    t_local_ = this->now();
  }

  void on_timer()
  {
    if (!have_global_ || !have_local_) {
      return;
    }
    if ((this->now() - t_global_).seconds() > 1.0 || (this->now() - t_local_).seconds() > 1.0) {
      return;
    }

    const double t_sec = this->now().seconds();

    double otrk = 0, ogs = 0, ovs = 0;
    ned_to_trk_gs_vs(vn_, ve_, vd_, otrk, ogs, ovs);

    double opos[3] = {g_lat_, g_lon_, g_alt_};
    double ovel[3] = {otrk, ogs, ovs};

    TrafficMonitor_InputOwnshipData(tm_, opos, ovel, t_sec, sigma_pos_, sigma_vel_);

    if (this->get_parameter("intruder_enable").as_bool()) {
      const double dn = this->get_parameter("intruder_n_m").as_double();
      const double de = this->get_parameter("intruder_e_m").as_double();
      const double lat_rad = g_lat_ * M_PI / 180.0;
      const double dlat = (dn / kEarthRadius) * (180.0 / M_PI);
      const double dlon = (de / (kEarthRadius * std::cos(lat_rad))) * (180.0 / M_PI);
      const double ilat = g_lat_ + dlat;
      const double ilon = g_lon_ + dlon;
      const double ialt = g_alt_;

      const double ivn = this->get_parameter("intruder_vn").as_double();
      const double ive = this->get_parameter("intruder_ve").as_double();
      const double ivd = this->get_parameter("intruder_vd").as_double();
      double itrk = 0, igs = 0, ivs = 0;
      ned_to_trk_gs_vs(ivn, ive, ivd, itrk, igs, ivs);

      double tpos[3] = {ilat, ilon, ialt};
      double tvel[3] = {itrk, igs, ivs};
      char calls[32] = "SYNTH1";
      TrafficMonitor_InputIntruderData(
        tm_, 0 /* _TRAFFIC_SIM_ */, 1, calls, tpos, tvel, t_sec, sigma_pos_, sigma_vel_);
    }

    double wind[2] = {0.0, 0.0};
    TrafficMonitor_MonitorTraffic(tm_, wind);

    bands_t b{};
    TrafficMonitor_GetTrackBands(tm_, &b);

    std_msgs::msg::Float64MultiArray out;
    out.data.resize(6);
    out.data[0] = static_cast<double>(b.numConflictTraffic);
    out.data[1] = b.minHDist;
    out.data[2] = b.minVDist;
    out.data[3] = b.timeToViolation[0];
    out.data[4] = b.timeToViolation[1];
    out.data[5] = b.timeToRecovery;
    pub_bands_->publish(out);

    RCLCPP_INFO_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000,
      "DAA: conflicts=%d minH=%.1f m minV=%.1f m", b.numConflictTraffic, b.minHDist, b.minVDist);
  }

  void * tm_{nullptr};
  double sigma_pos_[6]{};
  double sigma_vel_[6]{};

  bool have_global_{false};
  bool have_local_{false};
  double g_lat_{0}, g_lon_{0}, g_alt_{0};
  double vn_{0}, ve_{0}, vd_{0};
  rclcpp::Time t_global_;
  rclcpp::Time t_local_;

  rclcpp::Subscription<px4_msgs::msg::VehicleGlobalPosition>::SharedPtr sub_global_;
  rclcpp::Subscription<px4_msgs::msg::VehicleLocalPosition>::SharedPtr sub_local_;
  rclcpp::Publisher<std_msgs::msg::Float64MultiArray>::SharedPtr pub_bands_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  try {
    rclcpp::spin(std::make_shared<DaaTrafficMonitorNode>());
  } catch (const std::exception & e) {
    RCLCPP_ERROR(rclcpp::get_logger("daa_traffic_monitor"), "%s", e.what());
    return 1;
  }
  rclcpp::shutdown();
  return 0;
}
