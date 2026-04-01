#include "acas_node/nnet_loader.hpp"

#include <gtest/gtest.h>

#include <filesystem>
#include <string>

TEST(NNetLoader, heuristic_far_clear)
{
  acas_node::NNetLoader L;
  const std::string path = std::filesystem::path(__FILE__).parent_path() / ".." / "nnets" / "acas_xu_00.nnet";
  ASSERT_TRUE(L.load(path));
  std::array<float, 5> in{};
  in[0] = 0.98F;  // far
  in[1] = 0.0F;
  in[2] = 0.0F;
  in[3] = 0.5F;
  in[4] = 0.5F;
  const auto o = L.evaluate(in);
  EXPECT_GT(o[0], 0.99F);
}

TEST(NNetLoader, heuristic_left_front_wr)
{
  acas_node::NNetLoader L;
  const std::string path = std::filesystem::path(__FILE__).parent_path() / ".." / "nnets" / "acas_xu_00.nnet";
  ASSERT_TRUE(L.load(path));
  std::array<float, 5> in{};
  in[0] = 0.2F;   // close
  in[1] = -0.5F;  // left-front proxy
  in[2] = 0.0F;
  in[3] = 0.5F;
  in[4] = 0.5F;
  const auto o = L.evaluate(in);
  EXPECT_GT(o[2], 0.99F);
}
