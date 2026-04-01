#include "acas_node/nnet_loader.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <fstream>
#include <istream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace acas_node {

namespace {

std::string trim(std::string s)
{
  auto not_space = [](unsigned char c) { return !std::isspace(c); };
  s.erase(s.begin(), std::find_if(s.begin(), s.end(), not_space));
  s.erase(std::find_if(s.rbegin(), s.rend(), not_space).base(), s.end());
  return s;
}

bool is_comment_or_empty(const std::string & line)
{
  const auto t = trim(line);
  return t.empty() || t[0] == '#';
}

}  // namespace

std::vector<float> NNetLoader::read_float_block(std::istream & in, size_t count)
{
  std::vector<float> out;
  out.reserve(count);
  std::string line;
  while (out.size() < count && std::getline(in, line)) {
    if (is_comment_or_empty(line)) {
      continue;
    }
    std::istringstream iss(line);
    float v = 0.0F;
    while (iss >> v) {
      out.push_back(v);
      if (out.size() >= count) {
        break;
      }
    }
  }
  if (out.size() != count) {
    throw std::runtime_error("nnet: expected " + std::to_string(count) + " floats, got " +
      std::to_string(out.size()));
  }
  return out;
}

bool NNetLoader::load(const std::string & path)
{
  mode_ = Mode::Empty;
  layer_sizes_.clear();
  weights_.clear();
  biases_.clear();

  std::ifstream f(path);
  if (!f.is_open()) {
    return false;
  }

  std::string line;
  while (std::getline(f, line)) {
    if (is_comment_or_empty(line)) {
      continue;
    }
    line = trim(line);
    if (line.rfind("MODE", 0) == 0) {
      std::istringstream iss(line);
      std::string tag, mode;
      iss >> tag >> mode;
      if (mode == "HEURISTIC_SIL_V1") {
        mode_ = Mode::HeuristicSilV1;
        return true;
      }
      if (mode == "MLP_RELU") {
        mode_ = Mode::MlpRelu;
      } else {
        return false;
      }
      continue;
    }
    if (mode_ == Mode::MlpRelu && line.rfind("LAYERS", 0) == 0) {
      std::istringstream iss(line);
      std::string dummy;
      iss >> dummy;
      layer_sizes_.clear();
      int sz = 0;
      while (iss >> sz) {
        layer_sizes_.push_back(sz);
      }
      if (layer_sizes_.size() < 2U) {
        return false;
      }
      const size_t n_layers = layer_sizes_.size() - 1U;
      weights_.resize(n_layers);
      biases_.resize(n_layers);
      for (size_t L = 0; L < n_layers; ++L) {
        const int in_d = layer_sizes_[L];
        const int out_d = layer_sizes_[L + 1];
        const size_t wcount = static_cast<size_t>(in_d * out_d);
        weights_[L] = read_float_block(f, wcount);
        biases_[L] = read_float_block(f, static_cast<size_t>(out_d));
      }
      break;
    }
  }

  if (mode_ == Mode::MlpRelu && !weights_.empty()) {
    return true;
  }
  return false;
}

std::array<float, 5> NNetLoader::evaluate_heuristic(const std::array<float, 5> & in) const
{
  // Inputs are normalized roughly to [0,1] (rho) and [-1,1] (angles), per acas_node.cpp.
  const float rho_n = std::clamp(in[0], 0.0F, 1.0F);  // 1 = far, 0 = close
  const float th_n = std::clamp(in[1], -1.0F, 1.0F);  // body-frame bearing proxy

  std::array<float, 5> out{};
  if (rho_n > 0.92F) {
    out[static_cast<size_t>(Advisory::COC)] = 1.0F;
    return out;
  }
  // Left-front hemisphere proxy: negative relative bearing in normalized coords.
  if (th_n < -0.15F && th_n > -0.95F) {
    out[static_cast<size_t>(Advisory::WR)] = 1.0F;
    return out;
  }
  out[static_cast<size_t>(Advisory::COC)] = 0.6F;
  out[static_cast<size_t>(Advisory::WL)] = 0.2F;
  out[static_cast<size_t>(Advisory::WR)] = 0.2F;
  return out;
}

std::array<float, 5> NNetLoader::evaluate_mlp(const std::array<float, 5> & in) const
{
  std::vector<float> a(in.begin(), in.end());
  for (size_t L = 0; L < weights_.size(); ++L) {
    const int in_d = layer_sizes_[L];
    const int out_d = layer_sizes_[L + 1];
    std::vector<float> z(static_cast<size_t>(out_d), 0.0F);
    for (int o = 0; o < out_d; ++o) {
      float sum = biases_[L][static_cast<size_t>(o)];
      for (int i = 0; i < in_d; ++i) {
        const size_t idx = static_cast<size_t>(o * in_d + i);
        sum += weights_[L][idx] * a[static_cast<size_t>(i)];
      }
      z[static_cast<size_t>(o)] = (L + 1U < weights_.size()) ? relu(sum) : sum;
    }
    a = std::move(z);
  }
  std::array<float, 5> out{};
  for (size_t i = 0; i < 5U && i < a.size(); ++i) {
    out[i] = a[i];
  }
  return out;
}

std::array<float, 5> NNetLoader::evaluate(const std::array<float, 5> & inputs) const
{
  if (mode_ == Mode::HeuristicSilV1) {
    return evaluate_heuristic(inputs);
  }
  if (mode_ == Mode::MlpRelu) {
    return evaluate_mlp(inputs);
  }
  return {0.0F, 0.0F, 0.0F, 0.0F, 0.0F};
}

}  // namespace acas_node
