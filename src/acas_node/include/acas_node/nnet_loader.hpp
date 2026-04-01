#ifndef ACAS_NODE_NNET_LOADER_HPP_
#define ACAS_NODE_NNET_LOADER_HPP_

#include <array>
#include <string>
#include <vector>

namespace acas_node {

/// ACAS Xu discrete advisories (network output classes).
enum class Advisory : int { COC = 0, WL = 1, WR = 2, SL = 3, SR = 4 };

/// Loads plain-text neural network definitions and runs a forward pass (5 → … → 5).
/// Supports:
/// - `MODE HEURISTIC_SIL_V1` synthetic SIL policy (see third_party README).
/// - `MODE MLP_RELU` small fully-connected ReLU nets (weights/biases listed line-by-line).
class NNetLoader {
public:
  bool load(const std::string & path);
  [[nodiscard]] std::array<float, 5> evaluate(const std::array<float, 5> & inputs) const;

  [[nodiscard]] bool loaded() const { return mode_ != Mode::Empty; }

private:
  enum class Mode { Empty, HeuristicSilV1, MlpRelu };

  static std::vector<float> read_float_block(std::istream & in, size_t count);
  static float relu(float x) { return x > 0.0F ? x : 0.0F; }
  [[nodiscard]] std::array<float, 5> evaluate_heuristic(const std::array<float, 5> & in) const;
  [[nodiscard]] std::array<float, 5> evaluate_mlp(const std::array<float, 5> & in) const;

  Mode mode_{Mode::Empty};
  std::vector<int> layer_sizes_;
  std::vector<std::vector<float>> weights_;
  std::vector<std::vector<float>> biases_;
};

}  // namespace acas_node

#endif  // ACAS_NODE_NNET_LOADER_HPP_
