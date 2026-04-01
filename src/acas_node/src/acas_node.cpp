#include "acas_node/nnet_loader.hpp"

#include <ament_index_cpp/get_package_share_directory.hpp>
#include <cstdio>
#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include <flightmind_msgs/msg/acas_advisory.hpp>
#include <flightmind_msgs/msg/navigation_state.hpp>
#include <flightmind_msgs/msg/traffic_report.hpp>
#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/float64_multi_array.hpp>

namespace acas_node {

namespace {

constexpr double kPi = 3.14159265358979323846;

double wrap_pi(double a)
{
  while (a > kPi) {
    a -= 2.0 * kPi;
  }
  while (a < -kPi) {
    a += 2.0 * kPi;
  }
  return a;
}

double yaw_from_quat(double w, double x, double y, double z)
{
  return std::atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z));
}

double horiz_hypot(double a, double b)
{
  return std::hypot(a, b);
}

int threat_class_from_geometry(
  double rel_n, double rel_e, double own_vn, double own_ve, double int_vn, double int_ve)
{
  const double sp_o = horiz_hypot(own_vn, own_ve);
  if (sp_o < 2.0) {
    return 3;  // GENERIC
  }
  const double uo_n = own_vn / sp_o;
  const double uo_e = own_ve / sp_o;
  const bool in_front = rel_n * uo_n + rel_e * uo_e > 0.0;
  const double own_trk = std::atan2(own_ve, own_vn);
  const double int_trk = std::atan2(int_ve, int_vn);
  double dpsi = std::abs(wrap_pi(own_trk - int_trk));
  const double sp_i = horiz_hypot(int_vn, int_ve);

  if (in_front && dpsi > (110.0 * kPi / 180.0)) {
    return 1;  // HEAD_ON
  }
  if (in_front && dpsi < (70.0 * kPi / 180.0) && sp_o > sp_i + 8.0) {
    return 2;  // OVERTAKE
  }
  return 3;  // GENERIC
}

double tcpa_horiz_s(
  double rel_n, double rel_e, double rvn, double rve)
{
  const double rho = horiz_hypot(rel_n, rel_e) + 1e-9;
  const double rdot = (rel_n * rvn + rel_e * rve) / rho;
  if (rdot >= -1e-3) {
    return 1e9;
  }
  return -rho / rdot;
}

}  // namespace

class AcasNode : public rclcpp::Node
{
public:
  AcasNode()
  : rclcpp::Node("acas_node")
  {
    traffic_topic_ = declare_parameter<std::string>("traffic_topic", "/traffic/intruders");
    navigation_topic_ = declare_parameter<std::string>("navigation_topic", "/navigation/state");
    ownship_topic_ = declare_parameter<std::string>("ownship_topic", "/ownship/state");
    nnet_subdir_ = declare_parameter<std::string>("nnet_subdir", "acas_xu_nnets");
    rho_norm_m_ = declare_parameter<double>("rho_norm_m", 185200.0);
    v_norm_mps_ = declare_parameter<double>("v_norm_mps", 250.0);
    timer_period_s_ = declare_parameter<double>("timer_period_s", 0.05);
    use_ownship_fallback_ = declare_parameter<bool>("use_ownship_fallback", true);

    pub_ = create_publisher<flightmind_msgs::msg::ACASAdvisory>("/acas/advisory", 10);

    sub_nav_ = create_subscription<flightmind_msgs::msg::NavigationState>(
      navigation_topic_, 10,
      std::bind(&AcasNode::on_nav, this, std::placeholders::_1));
    sub_traffic_ = create_subscription<flightmind_msgs::msg::TrafficReport>(
      traffic_topic_, 10,
      std::bind(&AcasNode::on_traffic, this, std::placeholders::_1));
    if (use_ownship_fallback_) {
      sub_own_ = create_subscription<std_msgs::msg::Float64MultiArray>(
        ownship_topic_, 10,
        std::bind(&AcasNode::on_ownship, this, std::placeholders::_1));
    }

    const std::string share = ament_index_cpp::get_package_share_directory("acas_node");
    const std::string net_dir = share + "/" + nnet_subdir_;
    nets_.resize(45);
    for (int i = 0; i < 45; ++i) {
      char name[64];
      snprintf(name, sizeof(name), "/acas_xu_%02d.nnet", i);
      const std::string path = net_dir + name;
      if (!nets_[static_cast<size_t>(i)].load(path)) {
        RCLCPP_ERROR(get_logger(), "Failed to load neural net: %s", path.c_str());
      }
    }

    timer_ = create_wall_timer(
      std::chrono::duration<double>(timer_period_s_),
      std::bind(&AcasNode::on_timer, this));

    RCLCPP_INFO(get_logger(), "acas_node: ACAS Xu .nnet stack (%zu nets), traffic=%s", nets_.size(),
      traffic_topic_.c_str());
  }

private:
  void on_ownship(const std_msgs::msg::Float64MultiArray::SharedPtr msg)
  {
    if (msg->data.size() < 6U) {
      return;
    }
    own_vn_ = static_cast<double>(msg->data[3]);
    own_ve_ = static_cast<double>(msg->data[4]);
    own_vd_ = static_cast<double>(msg->data[5]);
    if (!have_nav_) {
      own_yaw_ = std::atan2(own_ve_, own_vn_);
    }
    have_own_fallback_ = true;
  }

  void on_nav(const flightmind_msgs::msg::NavigationState::SharedPtr msg)
  {
    last_nav_ = msg;
    const auto & q = msg->orientation_quat;
    own_yaw_ = yaw_from_quat(q[0], q[1], q[2], q[3]);
    own_vn_ = msg->velocity_ned[0];
    own_ve_ = msg->velocity_ned[1];
    own_vd_ = msg->velocity_ned[2];
    have_nav_ = true;
  }

  void on_traffic(const flightmind_msgs::msg::TrafficReport::SharedPtr msg) { last_traffic_ = msg; }

  void on_timer()
  {
    if (!have_nav_ && !(use_ownship_fallback_ && have_own_fallback_)) {
      return;
    }
    if (!last_traffic_ || last_traffic_->intruders.empty()) {
      publish_coc(0, 0.0, 1e6, 0.0, 0.0, 0.0);
      return;
    }

    double own_vn = own_vn_;
    double own_ve = own_ve_;
    double own_vd = own_vd_;

    // Closest intruder in horizontal plane (NED relative positions).
    size_t best = 0U;
    double best_rho = 1e300;
    for (size_t i = 0; i < last_traffic_->intruders.size(); ++i) {
      const auto & intr = last_traffic_->intruders[i];
      const double rn = intr.position_ned[0];
      const double re = intr.position_ned[1];
      const double rho = horiz_hypot(rn, re);
      if (rho < best_rho) {
        best_rho = rho;
        best = i;
      }
    }
    const auto & intr = last_traffic_->intruders[best];
    const double rel_n = intr.position_ned[0];
    const double rel_e = intr.position_ned[1];
    const double int_vn = intr.velocity_ned[0];
    const double int_ve = intr.velocity_ned[1];
    const double int_vd = intr.velocity_ned[2];

    const double rho_m = horiz_hypot(rel_n, rel_e);
    const double bearing = std::atan2(rel_e, rel_n);
    const double theta = wrap_pi(bearing - own_yaw_);
    const double own_trk = std::atan2(own_ve, own_vn);
    const double int_trk = std::atan2(int_ve, int_vn);
    const double psi = wrap_pi(int_trk - own_trk);

    const double rvn = int_vn - own_vn;
    const double rve = int_ve - own_ve;
    double tau_s = tcpa_horiz_s(rel_n, rel_e, rvn, rve);
    if (!std::isfinite(tau_s) || tau_s > 1e6) {
      tau_s = 8.0;
    }
    tau_s = std::max(0.0, std::min(8.0, tau_s));

    const int tau_idx = static_cast<int>(std::lround(tau_s));
    const int net_i = std::max(0, std::min(44, tau_idx * 5 + prev_adv_));
    if (!nets_[static_cast<size_t>(net_i)].loaded()) {
      publish_coc(0, rho_m, tau_s, theta, psi, rho_m);
      return;
    }

    const float rho_n = static_cast<float>(std::min(1.0, std::max(0.0, rho_m / rho_norm_m_)));
    const float th_n = static_cast<float>(theta / kPi);
    const float ps_n = static_cast<float>(psi / kPi);
    const double v_own = horiz_hypot(own_vn, own_ve);
    const double v_int = horiz_hypot(int_vn, int_ve);
    const float vo_n = static_cast<float>(std::min(1.0, std::max(0.0, v_own / v_norm_mps_)));
    const float vi_n = static_cast<float>(std::min(1.0, std::max(0.0, v_int / v_norm_mps_)));

    std::array<float, 5> in = {rho_n, th_n, ps_n, vo_n, vi_n};
    const auto scores = nets_[static_cast<size_t>(net_i)].evaluate(in);
    int best_adv = 0;
    float best_s = scores[0];
    for (int a = 1; a < 5; ++a) {
      if (scores[static_cast<size_t>(a)] > best_s) {
        best_s = scores[static_cast<size_t>(a)];
        best_adv = a;
      }
    }
    prev_adv_ = best_adv;

    const int tclass = threat_class_from_geometry(rel_n, rel_e, own_vn, own_ve, int_vn, int_ve);
    double turn_degps = 0.0;
    switch (best_adv) {
      case 0:
        turn_degps = 0.0;
        break;
      case 1:
        turn_degps = -1.5;
        break;
      case 2:
        turn_degps = 1.5;
        break;
      case 3:
        turn_degps = -3.0;
        break;
      case 4:
        turn_degps = 3.0;
        break;
      default:
        turn_degps = 0.0;
        break;
    }

    flightmind_msgs::msg::ACASAdvisory out;
    out.header.stamp = now();
    out.header.frame_id = "base_link";
    out.ra_active = (best_adv != 0);
    out.threat_class = tclass;
    out.climb_rate_mps = 0.0;
    out.heading_delta_deg = turn_degps * tau_s;
    out.time_to_cpa_s = tau_s;
    out.horizontal_miss_dist_m = rho_m;
    pub_->publish(out);
  }

  void publish_coc(
    int threat_class, double rho_m, double tau_s, double theta, double psi, double miss_m)
  {
    prev_adv_ = 0;
    flightmind_msgs::msg::ACASAdvisory out;
    out.header.stamp = now();
    out.header.frame_id = "base_link";
    out.ra_active = false;
    out.threat_class = threat_class;
    out.climb_rate_mps = 0.0;
    out.heading_delta_deg = 0.0;
    out.time_to_cpa_s = tau_s;
    out.horizontal_miss_dist_m = miss_m;
    (void)theta;
    (void)psi;
    (void)rho_m;
    pub_->publish(out);
  }

  rclcpp::Publisher<flightmind_msgs::msg::ACASAdvisory>::SharedPtr pub_;
  rclcpp::Subscription<flightmind_msgs::msg::NavigationState>::SharedPtr sub_nav_;
  rclcpp::Subscription<flightmind_msgs::msg::TrafficReport>::SharedPtr sub_traffic_;
  rclcpp::Subscription<std_msgs::msg::Float64MultiArray>::SharedPtr sub_own_;
  rclcpp::TimerBase::SharedPtr timer_;

  std::string traffic_topic_;
  std::string navigation_topic_;
  std::string ownship_topic_;
  std::string nnet_subdir_;
  double rho_norm_m_{185200.0};
  double v_norm_mps_{250.0};
  double timer_period_s_{0.05};
  bool use_ownship_fallback_{true};

  flightmind_msgs::msg::NavigationState::SharedPtr last_nav_;
  flightmind_msgs::msg::TrafficReport::SharedPtr last_traffic_;

  bool have_nav_{false};
  bool have_own_fallback_{false};
  double own_yaw_{0.0};
  double own_vn_{0.0};
  double own_ve_{0.0};
  double own_vd_{0.0};

  int prev_adv_{0};
  std::vector<NNetLoader> nets_;
};

}  // namespace acas_node

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<acas_node::AcasNode>());
  rclcpp::shutdown();
  return 0;
}
