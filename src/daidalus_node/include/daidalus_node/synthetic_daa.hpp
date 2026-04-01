#ifndef DAIDALUS_NODE__SYNTHETIC_DAA_HPP_
#define DAIDALUS_NODE__SYNTHETIC_DAA_HPP_

#include <cstdint>
#include <vector>

namespace daidalus_node
{

struct IntruderState
{
  uint32_t id{0};
  double n{0}, e{0}, z{0};
  double vn{0}, ve{0}, vd{0};
};

struct OwnshipState
{
  double n{0}, e{0}, z{0};
  double vn{0}, ve{0}, vd{0};
};

struct SyntheticDaaParams
{
  double lookahead_time_s{180.0};
  double alerting_time_s{55.0};
  double dmod_m{2200.0};
  double zthr_m{137.16};
  double turn_rate_degps{3.0};
  double red_time_s{25.0};
};

struct SyntheticDaaOutput
{
  double num_conflict{0.0};
  double min_h{1e9};
  double min_v{1e9};
  int32_t alert_level{0};
  double ra_hdg_deg{0.0};
  double ra_gs_mps{0.0};
  double ra_vs_mps{0.0};
};

SyntheticDaaOutput run_synthetic_daa(
  const OwnshipState &own,
  const std::vector<IntruderState> &intruders,
  const SyntheticDaaParams &p);

}  // namespace daidalus_node

#endif  // DAIDALUS_NODE__SYNTHETIC_DAA_HPP_
