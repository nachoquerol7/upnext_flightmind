"""Nodo mínimo: comprueba ICAROUS_HOME y librerías; base para futuro MAVLink/TrafficMonitor."""

import os

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from upnext_icarous_bridge.paths import default_icarous_home


class IcarousBridgeNode(Node):
    def __init__(self) -> None:
        super().__init__('icarous_bridge')

        self.declare_parameter('icarous_home', '')
        self.declare_parameter('publish_hz', 0.2)

        home = self.get_parameter('icarous_home').get_parameter_value().string_value
        if not home.strip():
            home = os.environ.get('ICAROUS_HOME', default_icarous_home())
        home = os.path.abspath(os.path.expanduser(home))

        lib_dir = os.path.join(home, 'Modules', 'lib')
        modules_ok = os.path.isdir(lib_dir)

        self.get_logger().info(f'ICAROUS_HOME={home}')
        self.get_logger().info(f'Modules/lib present: {modules_ok} ({lib_dir})')

        self._pub = self.create_publisher(String, 'icarous_status', 10)
        hz = float(self.get_parameter('publish_hz').value)
        if hz > 0.0:
            self._timer = self.create_timer(1.0 / hz, self._tick)
        else:
            self._timer = None

        self._status = String()
        self._status.data = 'ready' if modules_ok else 'missing_modules_build'

    def _tick(self) -> None:
        self._pub.publish(self._status)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = IcarousBridgeNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
