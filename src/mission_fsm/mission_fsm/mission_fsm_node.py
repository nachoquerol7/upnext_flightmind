"""Mission FSM node: inputs on /fsm/in/*, state on /fsm/current_mode, /fsm/active_trigger."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Tuple

import rclpy
from flightmind_msgs.msg import FSMState
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, Float64, Int32, String

from mission_fsm.fsm import MissionFsm, default_inputs, load_fsm_yaml_dict

try:
    from ament_index_python.packages import get_package_share_directory
except ImportError:  # pragma: no cover
    get_package_share_directory = None  # type: ignore[misc, assignment]


_BOOL_TOPICS: Tuple[str, ...] = (
    "preflight_ok",
    "taxi_clear",
    "takeoff_complete",
    "land_command",
    "rtb_command",
    "abort_command",
    "event_cleared",
    "rtb_during_event",
    "touchdown",
    "go_around_complete",
    "missed_approach_climb",
    "rtb_landing",
    "rtb_cancel",
    "fdir_emergency",
    "approach_not_stabilized",
)


class MissionFsmNode(Node):
    def __init__(self) -> None:
        super().__init__("mission_fsm_node")

        self.declare_parameter("config_file", "")
        self.declare_parameter("initial_state", "PREFLIGHT")
        self.declare_parameter("quality_flag_threshold", 0.5)
        self.declare_parameter("daidalus_alert_amber", 1)
        self.declare_parameter("tick_hz", 20.0)

        cfg = self.get_parameter("config_file").get_parameter_value().string_value.strip()
        if cfg and os.path.isfile(cfg):
            path = cfg
        else:
            if get_package_share_directory is None:
                raise RuntimeError("ament_index_python required to resolve default config")
            path = os.path.join(get_package_share_directory("mission_fsm"), "config", "mission_fsm.yaml")
            if not os.path.isfile(path):
                raise FileNotFoundError(f"default mission FSM config not found: {path}")

        root = load_fsm_yaml_dict(path)
        ros_params = root.setdefault("mission_fsm_node", {}).setdefault("ros__parameters", {})
        ros_params["initial_state"] = self.get_parameter("initial_state").get_parameter_value().string_value
        ros_params["quality_flag_threshold"] = float(
            self.get_parameter("quality_flag_threshold").get_parameter_value().double_value
        )
        ros_params["daidalus_alert_amber"] = int(
            self.get_parameter("daidalus_alert_amber").get_parameter_value().integer_value
        )

        self._fsm = MissionFsm.from_fsm_yaml(root)
        self._inputs: Dict[str, Any] = default_inputs()

        fsm_state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._fsm_state_pub = self.create_publisher(FSMState, "/fsm/state", fsm_state_qos)
        # Legacy publishers kept for SIL compatibility while subscribers migrate to FSMState.
        self._pub_mode = self.create_publisher(String, "/fsm/current_mode", 10)
        self._pub_trig = self.create_publisher(String, "/fsm/active_trigger", 10)

        self.create_subscription(Float64, "/fsm/in/quality_flag", self._mk_float("quality_flag"), 10)
        self.create_subscription(Int32, "/fsm/in/daidalus_alert", self._mk_int("daidalus_alert"), 10)
        for name in _BOOL_TOPICS:
            self.create_subscription(Bool, f"/fsm/in/{name}", self._mk_bool(name), 10)

        hz = float(self.get_parameter("tick_hz").get_parameter_value().double_value)
        period = 1.0 / hz if hz > 1e-3 else 0.05
        self.create_timer(period, self._on_tick)

        self.get_logger().info(f"mission_fsm: loaded {path}, initial={self._fsm.state}")

    def _mk_float(self, key: str) -> Callable[[Float64], None]:
        def cb(msg: Float64) -> None:
            self._inputs[key] = float(msg.data)

        return cb

    def _mk_int(self, key: str) -> Callable[[Int32], None]:
        def cb(msg: Int32) -> None:
            self._inputs[key] = int(msg.data)

        return cb

    def _mk_bool(self, key: str) -> Callable[[Bool], None]:
        def cb(msg: Bool) -> None:
            self._inputs[key] = bool(msg.data)

        return cb

    def _on_tick(self) -> None:
        state, trig = self._fsm.step(self._inputs)
        msg = FSMState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.current_mode = state
        msg.active_trigger = trig or ""
        msg.event_substate = ""
        msg.go_around_count = 0
        self._fsm_state_pub.publish(msg)
        self._pub_mode.publish(String(data=state))
        self._pub_trig.publish(String(data=trig if trig else ""))


def main(args: Any = None) -> None:
    rclpy.init(args=args)
    node = MissionFsmNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
