#!/usr/bin/env python3
"""
HIL smoke test — verifica que el stack arranca y el FSM responde.

Requiere `source install/setup.bash` y los mismos topics que mission_fsm (FSMState en /fsm/state).

Si el binario PX4 SITL no está en la ruta esperada, el script continúa en modo SIL y lo indica en consola.
"""

from __future__ import annotations

import os
import sys
import time

import rclpy
from flightmind_msgs.msg import FSMState
from std_msgs.msg import Bool


def _px4_available() -> bool:
    p = os.path.expanduser("~/PX4-Autopilot/build/px4_sitl_default/bin/px4")
    return os.path.isfile(p)


def main() -> int:
    px4_ok = _px4_available()
    if not px4_ok:
        print("[SIL MODE — PX4 SITL not available] Continuando comprobación ROS2 / FSM solamente.")

    rclpy.init()
    node = rclpy.create_node("hil_smoke_test")

    state: dict[str, str | None] = {"mode": None}

    def on_fsm(msg: FSMState) -> None:
        state["mode"] = msg.current_mode

    node.create_subscription(FSMState, "/fsm/state", on_fsm, 10)

    pub_preflight = node.create_publisher(Bool, "/fsm/in/preflight_ok", 10)
    pub_taxi = node.create_publisher(Bool, "/fsm/in/taxi_clear", 10)
    pub_takeoff_done = node.create_publisher(Bool, "/fsm/in/takeoff_complete", 10)
    pub_land = node.create_publisher(Bool, "/fsm/in/land_command", 10)

    def spin_until(pred, timeout_sec: float) -> bool:
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_sec:
            rclpy.spin_once(node, timeout_sec=0.05)
            if pred():
                return True
        return False

    t_start = time.monotonic()

    # 1. PREFLIGHT
    if not spin_until(lambda: state["mode"] == "PREFLIGHT", 30.0):
        print(f"FAIL: timeout esperando PREFLIGHT (último modo={state['mode']!r})")
        node.destroy_node()
        rclpy.shutdown()
        return 1

    # 2. Nominal path to CRUISE (preflight_ok → AUTOTAXI → TAKEOFF → CRUISE)
    pub_preflight.publish(Bool(data=True))
    if not spin_until(lambda: state["mode"] == "AUTOTAXI", 10.0):
        print(f"FAIL: no se alcanzó AUTOTAXI (modo={state['mode']!r})")
        node.destroy_node()
        rclpy.shutdown()
        return 1

    pub_taxi.publish(Bool(data=True))
    if not spin_until(lambda: state["mode"] == "TAKEOFF", 10.0):
        print(f"FAIL: no se alcanzó TAKEOFF (modo={state['mode']!r})")
        node.destroy_node()
        rclpy.shutdown()
        return 1

    pub_takeoff_done.publish(Bool(data=True))
    if not spin_until(lambda: state["mode"] == "CRUISE", 10.0):
        print(f"FAIL: no se alcanzó CRUISE tras takeoff_complete (modo={state['mode']!r})")
        node.destroy_node()
        rclpy.shutdown()
        return 1

    # 3. Aterrizaje (sustituye a «mission_complete» del enunciado genérico: en este FSM es land_command)
    pub_land.publish(Bool(data=True))
    if not spin_until(lambda: state["mode"] == "LANDING", 10.0):
        print(f"FAIL: no se alcanzó LANDING (modo={state['mode']!r})")
        node.destroy_node()
        rclpy.shutdown()
        return 1

    elapsed = time.monotonic() - t_start
    print(f"PASS — FSM alcanzó PREFLIGHT→…→CRUISE→LANDING en {elapsed:.2f}s")
    node.destroy_node()
    rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
