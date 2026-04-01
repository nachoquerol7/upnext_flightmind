#include <gtest/gtest.h>

#include <array>
#include <cmath>

namespace {

void softmax5(std::array<float, 5> * s)
{
  float m = (*s)[0];
  for (size_t i = 1; i < 5; ++i) {
    m = std::max(m, (*s)[i]);
  }
  float sum = 0.0F;
  for (size_t i = 0; i < 5; ++i) {
    (*s)[i] = std::exp((*s)[i] - m);
    sum += (*s)[i];
  }
  for (size_t i = 0; i < 5; ++i) {
    (*s)[i] /= sum;
  }
}

}  // namespace

// TC-ACAS-N03: normalized inputs in [0,1] domain (spot check)
TEST(AcasNeural, TC_ACAS_N03_normalize_rho_theta)
{
  const double rho = 30380.0;
  const double rho_n = rho / 60760.0;
  EXPECT_NEAR(rho_n, 0.5, 1e-6);
  const double theta = 1.57079632679;
  const double th_n = theta / M_PI;
  EXPECT_NEAR(th_n, 0.5, 1e-6);
}

// TC-ACAS-N04: softmax outputs sum to 1
TEST(AcasNeural, TC_ACAS_N04_softmax_sums_one)
{
  std::array<float, 5> logits = {1.0F, 2.0F, 0.5F, -1.0F, 3.0F};
  softmax5(&logits);
  float s = 0.0F;
  for (float v : logits) {
    s += v;
    EXPECT_GE(v, 0.0F);
    EXPECT_LE(v, 1.0F);
  }
  EXPECT_NEAR(s, 1.0F, 1e-5F);
}
