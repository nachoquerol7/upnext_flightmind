#include <gtest/gtest.h>

#include "daidalus_node/synthetic_daa.hpp"

using daidalus_node::IntruderState;
using daidalus_node::OwnshipState;
using daidalus_node::SyntheticDaaParams;
using daidalus_node::run_synthetic_daa;

TEST(SyntheticDaa, HeadOnAlertWithin55s)
{
  SyntheticDaaParams p;
  p.lookahead_time_s = 180.0;
  p.alerting_time_s = 55.0;
  p.dmod_m = 2200.0;
  p.zthr_m = 450.0 * 0.3048;
  p.red_time_s = 25.0;

  OwnshipState own{};
  own.n = own.e = own.z = 0.0;
  own.vn = 50.0;
  own.ve = own.vd = 0.0;

  IntruderState intr{};
  intr.id = 1;
  intr.n = 5500.0;
  intr.e = intr.z = 0.0;
  intr.vn = -50.0;
  intr.ve = intr.vd = 0.0;

  auto out = run_synthetic_daa(own, {intr}, p);
  EXPECT_GE(out.alert_level, 1);
  EXPECT_GE(out.num_conflict, 1.0);
}

TEST(SyntheticDaa, OvertakeNoFalseAlert)
{
  SyntheticDaaParams p;
  p.lookahead_time_s = 180.0;
  p.alerting_time_s = 55.0;
  p.dmod_m = 2200.0;
  p.zthr_m = 450.0 * 0.3048;
  p.red_time_s = 25.0;

  OwnshipState own{};
  own.n = own.e = own.z = 0.0;
  own.vn = 50.0;
  own.ve = own.vd = 0.0;

  IntruderState intr{};
  intr.id = 2;
  intr.n = -8000.0;
  intr.e = intr.z = 0.0;
  intr.vn = 48.0;
  intr.ve = intr.vd = 0.0;

  auto out = run_synthetic_daa(own, {intr}, p);
  EXPECT_EQ(out.alert_level, 0);
  EXPECT_EQ(out.num_conflict, 0.0);
}

TEST(SyntheticDaa, CrossingResolutionAdvisory)
{
  SyntheticDaaParams p;
  p.lookahead_time_s = 180.0;
  p.alerting_time_s = 55.0;
  p.dmod_m = 2200.0;
  p.zthr_m = 450.0 * 0.3048;
  p.red_time_s = 25.0;

  OwnshipState own{};
  own.n = own.e = own.z = 0.0;
  own.vn = 40.0;
  own.ve = own.vd = 0.0;

  IntruderState intr{};
  intr.id = 3;
  intr.n = 0.0;
  intr.e = 800.0;
  intr.z = 0.0;
  intr.vn = 0.0;
  intr.ve = -40.0;
  intr.vd = 0.0;

  auto out = run_synthetic_daa(own, {intr}, p);
  EXPECT_GE(out.alert_level, 1);
  EXPECT_NEAR(out.ra_hdg_deg, 30.0, 1.0);
}
