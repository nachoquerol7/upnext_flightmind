"""Publishes latched `/vehicle_model/state` as Float64MultiArray."""

from __future__ import annotations

import os
from typing import Any, List

import rclpy
from example_interfaces.srv import SetBool
from flightmind_msgs.msg import VehicleModelState
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile
from std_msgs.msg import Float64MultiArray, MultiArrayDimension

from vehicle_model.model import VehicleModel, TrajectorySegment, load_yaml_dict, model_params_from_ros_dict


# Layout of data[] in /vehicle_model/state (document for consumers)
STATE_LABELS: List[str] = [
    "v_min_dynamic_ms",
    "v_max_ms",
    "turn_radius_min_m",
    "climb_rate_max_ms",
    "descent_rate_max_ms",
    "glide_ratio",
    "mass_kg",
    "fuel_remaining_kg",
]


class VehicleModelNode(Node):
    def __init__(self) -> None:
        super().__init__("vehicle_model_node")

        self.declare_parameter("config_file", "")
        self.declare_parameter("publish_rate_hz", 1.0)
        self.declare_parameter("mission_elapsed_time_h", 0.0)

        # Defaults (overridden by YAML or explicit params)
        for key, val in (
            ("v_min_ms", 30.0),
            ("v_max_ms", 57.0),
            ("turn_radius_min_m", 600.0),
            ("climb_rate_max_ms", 8.0),
            ("descent_rate_max_ms", 5.0),
            ("glide_ratio", 18.0),
            ("mtow_kg", 750.0),
            ("fuel_mass_initial_kg", 120.0),
            ("fuel_burn_kgh", 50.0),
            ("v_min_reserve_gain_ms", 5.0),
        ):
            self.declare_parameter(key, val)

        cfg_path = self.get_parameter("config_file").get_parameter_value().string_value.strip()
        merged: dict[str, Any] = {}
        if cfg_path:
            if not os.path.isfile(cfg_path):
                raise FileNotFoundError(f"vehicle_model config_file not found: {cfg_path}")
            merged.update(model_params_from_ros_dict(load_yaml_dict(cfg_path)))

        for key in (
            "v_min_ms",
            "v_max_ms",
            "turn_radius_min_m",
            "climb_rate_max_ms",
            "descent_rate_max_ms",
            "glide_ratio",
            "mtow_kg",
            "fuel_mass_initial_kg",
            "fuel_burn_kgh",
            "v_min_reserve_gain_ms",
        ):
            p = self.get_parameter(key)
            merged[key] = p.value

        self._model = VehicleModel.from_mapping(merged)
        elapsed = float(self.get_parameter("mission_elapsed_time_h").value)
        self._model.update_weight(elapsed)

        latched = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
        )
        self._pub = self.create_publisher(Float64MultiArray, "/vehicle_model/state", latched)

        hz = float(self.get_parameter("publish_rate_hz").value)
        period = 1.0 / hz if hz > 0.1 else 10.0
        self._timer = self.create_timer(period, self._on_timer)

        self._publish_once()
        self.get_logger().info(
            f"vehicle_model: publishing latched /vehicle_model/state ({len(STATE_LABELS)} fields)"
        )

    def _layout_msg(self) -> Float64MultiArray:
        msg = Float64MultiArray()
        msg.layout.dim.append(
            MultiArrayDimension(label="vehicle_model_state", size=len(STATE_LABELS), stride=len(STATE_LABELS))
        )
        msg.data = [float(x) for x in self._model.state_vector()]
        return msg

    def _publish_once(self) -> None:
        self._pub.publish(self._layout_msg())
        vec = self._model.state_vector()
        vm = VehicleModelState()
        vm.header.stamp = self.get_clock().now().to_msg()
        vm.header.frame_id = "vehicle"
        vm.v_min_ms = float(vec[0])
        vm.v_max_ms = float(vec[1])
        vm.turn_radius_min_m = float(vec[2])
        vm.climb_rate_max_mps = float(vec[3])
        vm.descent_rate_max_mps = float(vec[4])
        vm.glide_ratio = float(vec[5])
        vm.current_weight_kg = float(vec[6])
        vm.elapsed_mission_h = float(self.get_parameter("mission_elapsed_time_h").value)
        self._pub_vm.publish(vm)

    def _is_feasible_cb(self, request: SetBool.Request, response: SetBool.Response) -> SetBool.Response:
        """VM-004: simplified SIL — nominal manoeuvre accepted."""
        spd = 0.5 * (float(self._model.v_min_ms) + float(self._model.v_max_ms))
        seg = TrajectorySegment(speed_mps=spd, climb_rate_mps=0.0)
        ok = self._model.is_feasible([seg])
        response.success = ok and bool(request.data)
        response.message = "feasible" if response.success else "infeasible"
        return response

    def _on_timer(self) -> None:
        elapsed = float(self.get_parameter("mission_elapsed_time_h").value)
        self._model.update_weight(elapsed)
        self._publish_once()


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = VehicleModelNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
