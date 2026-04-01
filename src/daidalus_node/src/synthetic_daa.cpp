#include "daidalus_node/synthetic_daa.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace daidalus_node
{

static double hypot2(double a, double b) { return std::sqrt(a * a + b * b); }

static double track_deg_from_ne(double vn, double ve)
{
  return std::atan2(ve, vn) * 180.0 / M_PI;
}

SyntheticDaaOutput run_synthetic_daa(
  const OwnshipState &own,
  const std::vector<IntruderState> &intruders,
  const SyntheticDaaParams &p)
{
  SyntheticDaaOutput out;
  out.min_h = std::numeric_limits<double>::max();
  out.min_v = std::numeric_limits<double>::max();
  int conflicts = 0;
  int worst_level = 0;
  double suggest_hdg = track_deg_from_ne(own.vn, own.ve);
  const double own_gs = hypot2(own.vn, own.ve);

  const double dt = 0.5;
  const int max_steps = static_cast<int>(std::ceil(p.lookahead_time_s / dt));

  for (const auto &intr : intruders) {
    const double rn = intr.n - own.n;
    const double re = intr.e - own.e;
    const double rz = intr.z - own.z;
    const double rvn = intr.vn - own.vn;
    const double rve = intr.ve - own.ve;
    const double rvd = intr.vd - own.vd;

    auto horiz_at = [&](double t) {
      return hypot2(rn + rvn * t, re + rve * t);
    };
    auto vert_at = [&](double t) {
      return std::abs(rz + rvd * t);
    };

    double best_h = std::numeric_limits<double>::max();
    double best_v = std::numeric_limits<double>::max();
    for (int i = 0; i <= max_steps; ++i) {
      const double t = std::min(p.lookahead_time_s, static_cast<double>(i) * dt);
      best_h = std::min(best_h, horiz_at(t));
      best_v = std::min(best_v, vert_at(t));
    }

    out.min_h = std::min(out.min_h, best_h);
    out.min_v = std::min(out.min_v, best_v);

    double t_hit = std::numeric_limits<double>::infinity();
    for (int i = 1; i <= max_steps; ++i) {
      const double t = std::min(p.lookahead_time_s, static_cast<double>(i) * dt);
      if (horiz_at(t) < p.dmod_m && vert_at(t) < p.zthr_m) {
        t_hit = t;
        break;
      }
    }

    if (std::isfinite(t_hit)) {
      ++conflicts;
      int lvl = 0;
      if (t_hit <= p.red_time_s) {
        lvl = 2;
      } else if (t_hit <= p.alerting_time_s) {
        lvl = 1;
      }
      worst_level = std::max(worst_level, lvl);
      suggest_hdg = track_deg_from_ne(own.vn, own.ve) + 30.0;
      if (suggest_hdg > 180.0) {
        suggest_hdg -= 360.0;
      }
      if (suggest_hdg < -180.0) {
        suggest_hdg += 360.0;
      }
    }
  }

  out.num_conflict = static_cast<double>(conflicts);
  if (out.min_h > 1e8) {
    out.min_h = p.dmod_m;
  }
  if (out.min_v > 1e8) {
    out.min_v = p.zthr_m;
  }
  out.alert_level = worst_level;
  out.ra_hdg_deg = suggest_hdg;
  out.ra_gs_mps = std::max(own_gs * 0.95, 1.0);
  out.ra_vs_mps = 0.0;

  return out;
}

}  // namespace daidalus_node
