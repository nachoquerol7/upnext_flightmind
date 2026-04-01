"""Mission FSM node: inputs on /fsm/in/*, state on /fsm/state and legacy topics."""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Optional, Tuple

import rclpy
from flightmind_msgs.msg import ACASAdvisory, FSMState
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Bool, Float64, Header, Int32, String

from mission_fsm.fsm import MissionFsm, default_inputs, load_fsm_yaml_dict

try:
    from flightmind_common.event_logger import EventLogger
except ImportError:  # pragma: no cover
    EventLogger = None  # type: ignore[misc, assignment]

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
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("mission_fsm_node", **kwargs)

        self.declare_parameter("config_file", "")
        self.declare_parameter("initial_state", "PREFLIGHT")
        self.declare_parameter("quality_flag_threshold", 0.5)
        self.declare_parameter("daidalus_alert_amber", 1)
        self.declare_parameter("tick_hz", 20.0)
        self.declare_parameter("hysteresis_ticks_on", 3)
        self.declare_parameter("hysteresis_ticks_off", 5)
        self.declare_parameter("hysteresis_margin", 0.05)
        self.declare_parameter("daidalus_escalate_ticks", 2)
        self.declare_parameter("acas_abort_from_advisory", False)
        self.declare_parameter("daidalus_feed_timeout_sec", 2.0)
        self.declare_parameter("gcs_heartbeat_timeout_sec", 2.0)
        self.declare_parameter("c2_link_loss_sec", 2.0)
        self.declare_parameter("battery_low_threshold", 0.15)
        self.declare_parameter("battery_low_sustain_sec", 1.0)
        self.declare_parameter("geofence_breach_sustain_sec", 0.5)
        self.declare_parameter("event_log_dir", "")

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
        if not isinstance(ros_params, dict):
            ros_params = {}
        ros_params["initial_state"] = self.get_parameter("initial_state").get_parameter_value().string_value
        ros_params["quality_flag_threshold"] = float(
            self.get_parameter("quality_flag_threshold").get_parameter_value().double_value
        )
        ros_params["daidalus_alert_amber"] = int(
            self.get_parameter("daidalus_alert_amber").get_parameter_value().integer_value
        )
        ros_params["tick_hz"] = float(self.get_parameter("tick_hz").get_parameter_value().double_value)
        ros_params["hysteresis_ticks_on"] = int(
            self.get_parameter("hysteresis_ticks_on").get_parameter_value().integer_value
        )
        ros_params["hysteresis_ticks_off"] = int(
            self.get_parameter("hysteresis_ticks_off").get_parameter_value().integer_value
        )
        ros_params["hysteresis_margin"] = float(
            self.get_parameter("hysteresis_margin").get_parameter_value().double_value
        )
        ros_params["daidalus_escalate_ticks"] = int(
            self.get_parameter("daidalus_escalate_ticks").get_parameter_value().integer_value
        )
        ros_params["daidalus_feed_timeout_sec"] = float(
            self.get_parameter("daidalus_feed_timeout_sec").get_parameter_value().double_value
        )
        ros_params["gcs_heartbeat_timeout_sec"] = float(
            self.get_parameter("gcs_heartbeat_timeout_sec").get_parameter_value().double_value
        )
        ros_params["c2_link_loss_sec"] = float(
            self.get_parameter("c2_link_loss_sec").get_parameter_value().double_value
        )
        ros_params["battery_low_threshold"] = float(
            self.get_parameter("battery_low_threshold").get_parameter_value().double_value
        )
        ros_params["battery_low_sustain_sec"] = float(
            self.get_parameter("battery_low_sustain_sec").get_parameter_value().double_value
        )
        ros_params["geofence_breach_sustain_sec"] = float(
            self.get_parameter("geofence_breach_sustain_sec").get_parameter_value().double_value
        )

        acas_yaml = ros_params.get("acas_abort_from_advisory", False)
        if isinstance(acas_yaml, str):
            acas_yaml = acas_yaml.lower() in ("true", "1", "yes")
        self.set_parameters(
            [Parameter("acas_abort_from_advisory", Parameter.Type.BOOL, bool(acas_yaml))]
        )

        self._fsm = MissionFsm.from_fsm_yaml(root)
        self._inputs: Dict[str, Any] = default_inputs()
        self._acas_ra_active = False
        self._last_daidalus_msg_time: Optional[float] = None
        self._last_gcs_time: Optional[float] = None
        self._c2_false_since: Optional[float] = None
        self._battery_low_since: Optional[float] = None
        self._geofence_bad_since: Optional[float] = None
        self._last_geofence_ok: bool = True
        self._go_around_count = 0
        self._event_substate = ""
        self._ext_atoms: Dict[str, bool] = {
            "battery_low": False,
            "battery_critical": False,
            "c2_lost": False,
            "geofence_breach": False,
        }
        self._ext_polycarp_geofence = False
        log_dir = self.get_parameter("event_log_dir").get_parameter_value().string_value.strip()
        self._evlog: Any = None
        if log_dir and EventLogger is not None:
            self._evlog = EventLogger(log_dir=log_dir, flush_interval_s=1.0)

        fsm_state_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._fsm_state_pub = self.create_publisher(FSMState, "/fsm/state", fsm_state_qos)
        self._pub_mode = self.create_publisher(String, "/fsm/current_mode", 10)
        self._pub_trig = self.create_publisher(String, "/fsm/active_trigger", 10)

        self.create_subscription(Float64, "/fsm/in/quality_flag", self._mk_float("quality_flag"), 10)
        self.create_subscription(Int32, "/fsm/in/daidalus_alert", self._on_daidalus_alert, 10)
        for name in _BOOL_TOPICS:
            self.create_subscription(Bool, f"/fsm/in/{name}", self._mk_bool(name), 10)

        for k in self._ext_atoms:
            self.create_subscription(Bool, f"/fsm/in/{k}", self._mk_ext_atom(k), 10)
        self.create_subscription(Bool, "/polycarp/violation_imminent", self._on_polycarp_geofence, 10)

        self.create_subscription(Header, "/gcs_heartbeat", self._on_gcs_heartbeat, 10)
        self.create_subscription(Bool, "/c2_link_status", self._on_c2_link, 10)
        self.create_subscription(BatteryState, "/battery_state", self._on_battery, 10)
        self.create_subscription(Bool, "/geofence_breach", self._on_geofence_breach, 10)

        self.create_subscription(ACASAdvisory, "/acas/advisory", self._on_acas_advisory, 10)

        self._fsm_heartbeat_pub = self.create_publisher(Bool, "/fsm/heartbeat", 10)
        self.create_timer(1.0, self._publish_fsm_heartbeat)

        hz = float(self.get_parameter("tick_hz").get_parameter_value().double_value)
        period = 1.0 / hz if hz > 1e-3 else 0.05
        self.create_timer(period, self._on_tick)

        self.get_logger().info(f"mission_fsm: loaded {path}, initial={self._fsm.state}")

    def _publish_fsm_heartbeat(self) -> None:
        self._fsm_heartbeat_pub.publish(Bool(data=True))

    def _mk_float(self, key: str) -> Callable[[Float64], None]:
        def cb(msg: Float64) -> None:
            self._inputs[key] = float(msg.data)

        return cb

    def _on_daidalus_alert(self, msg: Int32) -> None:
        self._last_daidalus_msg_time = time.monotonic()
        self._inputs["daidalus_alert"] = int(msg.data)
        self._inputs["daidalus_feed_lost"] = False

    def _mk_bool(self, key: str) -> Callable[[Bool], None]:
        def cb(msg: Bool) -> None:
            self._inputs[key] = bool(msg.data)

        return cb

    def _mk_ext_atom(self, key: str) -> Callable[[Bool], None]:
        def cb(msg: Bool) -> None:
            self._ext_atoms[key] = bool(msg.data)

        return cb

    def _on_polycarp_geofence(self, msg: Bool) -> None:
        self._ext_polycarp_geofence = bool(msg.data)

    def _on_gcs_heartbeat(self, _msg: Header) -> None:
        self._last_gcs_time = time.monotonic()

    def _on_c2_link(self, msg: Bool) -> None:
        now = time.monotonic()
        if bool(msg.data):
            self._c2_false_since = None
        else:
            if self._c2_false_since is None:
                self._c2_false_since = now

    def _on_battery(self, msg: BatteryState) -> None:
        now = time.monotonic()
        pct = float(msg.percentage) if msg.percentage >= 0.0 else 1.0
        th = float(self.get_parameter("battery_low_threshold").value)
        if pct < th:
            if self._battery_low_since is None:
                self._battery_low_since = now
        else:
            self._battery_low_since = None

    def _on_geofence_breach(self, msg: Bool) -> None:
        breach = bool(msg.data)
        now = time.monotonic()
        if breach:
            if self._geofence_bad_since is None:
                self._geofence_bad_since = now
        else:
            self._geofence_bad_since = None
        self._last_geofence_ok = not breach

    def _on_acas_advisory(self, msg: ACASAdvisory) -> None:
        self._acas_ra_active = bool(msg.ra_active)

    def _update_supervision_atoms(self, now: float) -> None:
        gcs_to = float(self.get_parameter("gcs_heartbeat_timeout_sec").value)
        if self._last_gcs_time is not None and gcs_to > 0.0:
            self._inputs["gcs_lost"] = (now - self._last_gcs_time) > gcs_to
        else:
            self._inputs["gcs_lost"] = False

        c2_to = float(self.get_parameter("c2_link_loss_sec").value)
        if self._c2_false_since is not None and c2_to > 0.0:
            sup_c2 = (now - self._c2_false_since) > c2_to
        else:
            sup_c2 = False
        self._inputs["c2_lost"] = bool(self._ext_atoms["c2_lost"]) or sup_c2

        bat_to = float(self.get_parameter("battery_low_sustain_sec").value)
        if self._battery_low_since is not None and bat_to > 0.0:
            sup_bl = (now - self._battery_low_since) > bat_to
        else:
            sup_bl = False
        self._inputs["battery_low"] = bool(self._ext_atoms["battery_low"]) or sup_bl
        self._inputs["battery_critical"] = bool(self._ext_atoms["battery_critical"])

        gf_to = float(self.get_parameter("geofence_breach_sustain_sec").value)
        if self._geofence_bad_since is not None and gf_to > 0.0:
            self._inputs["geofence_violation"] = (now - self._geofence_bad_since) > gf_to
        else:
            self._inputs["geofence_violation"] = False

        self._inputs["geofence_breach"] = (
            bool(self._ext_atoms["geofence_breach"])
            or self._ext_polycarp_geofence
            or bool(self._inputs["geofence_violation"])
        )

        feed_to = float(self.get_parameter("daidalus_feed_timeout_sec").value)
        st = self._fsm.state
        if st in ("CRUISE", "EVENT", "LANDING", "GO_AROUND", "RTB") and feed_to > 0.0:
            if self._last_daidalus_msg_time is None:
                self._inputs["daidalus_feed_lost"] = False
            else:
                self._inputs["daidalus_feed_lost"] = (now - self._last_daidalus_msg_time) > feed_to
        else:
            self._inputs["daidalus_feed_lost"] = False

    def _infer_event_substate(self, trig: Optional[str]) -> str:
        if self._fsm.state != "EVENT":
            return ""
        traffic_triggers = (
            "to_event_near_fastpath",
            "to_recovery",
            "daidalus_feed_timeout",
            "geofence_rtb",
        )
        if trig in traffic_triggers:
            return "TRAFFIC_CONFLICT"
        th = float(self.get_parameter("quality_flag_threshold").value)
        if float(self._inputs.get("quality_flag", 1.0)) < th:
            return "SENSOR_DEGRADED"
        return "TRAFFIC_CONFLICT"

    def _on_tick(self) -> None:
        now = time.monotonic()
        self._update_supervision_atoms(now)

        merged: Dict[str, Any] = dict(self._inputs)
        use_acas_abort = bool(self.get_parameter("acas_abort_from_advisory").value)
        if use_acas_abort and self._acas_ra_active and self._fsm.state == "CRUISE":
            merged["abort_command"] = True

        prev = self._fsm.state
        state, trig = self._fsm.step(merged)

        if self._evlog is not None and state != prev:
            self._evlog.log_transition(prev, state, trig or "", merged)

        if state == "GO_AROUND" and prev == "LANDING":
            self._go_around_count += 1
        if state == "PREFLIGHT":
            self._go_around_count = 0

        sub = self._infer_event_substate(trig) if state == "EVENT" else ""
        self._event_substate = sub

        if state == "EVENT" and sub:
            mode_str = f"EVENT:{sub}"
        else:
            mode_str = state

        msg = FSMState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.current_mode = mode_str
        msg.active_trigger = trig or ""
        msg.event_substate = sub
        msg.go_around_count = int(self._go_around_count)
        self._fsm_state_pub.publish(msg)
        self._pub_mode.publish(String(data=mode_str))
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
