"""
Copyright MIT
GNU General Public License v3.0

MIT BWSI Autonomous Drone Racing Course - UAV Neo

File Name: flight.py
File Description: Defines the interface of the Flight module of the drone_core library.
"""

import abc


class Flight(abc.ABC):
    """
    Controls the drone's flight via piloting commands (pitch, roll, yaw, throttle).

    Note:
        All flight commands are sent to the mux node, which decides whether to
        forward them to the flight controller based on the autonomy operator's
        bumper state. The safety pilot always has override authority via the
        RC transmitter.
    """

    @abc.abstractmethod
    def send_pcmd(
        self, pitch: float, roll: float, yaw: float, throttle: float
    ) -> None:
        """
        Sends a piloting command to the drone.

        Args:
            pitch: Forward/backward tilt from -1.0 (backward) to 1.0 (forward).
            roll: Left/right tilt from -1.0 (left) to 1.0 (right).
            yaw: Rotation from -1.0 (counter-clockwise) to 1.0 (clockwise).
            throttle: Vertical speed from -1.0 (descend) to 1.0 (ascend).

        Note:
            All arguments are unitless ratios clamped to [-1.0, 1.0].
            The actual speed scaling is controlled by the mux node configuration,
            not by the student code.

        Example::

            # Fly forward at half input
            uav.flight.send_pcmd(0.5, 0, 0, 0)

            # Ascend while yawing right
            uav.flight.send_pcmd(0, 0, 0.3, 0.5)
        """
        pass

    def stop(self) -> None:
        """
        Zeros all flight inputs, bringing the drone to a hover.

        Note:
            Equivalent to uav.flight.send_pcmd(0, 0, 0, 0).

        Example::

            if counter > 5:
                uav.flight.stop()
        """
        self.send_pcmd(0, 0, 0, 0)

    @abc.abstractmethod
    def send_body_velocity(
        self, v_forward: float, v_right: float, v_up: float, yaw_rate: float = 0.0
    ) -> None:
        """
        Commands a body-frame velocity setpoint in SI units.

        Args:
            v_forward: Forward speed in m/s (positive = ahead).
            v_right: Rightward speed in m/s (positive = drone's right).
            v_up: Vertical speed in m/s (positive = up).
            yaw_rate: Turn rate in rad/s (positive = clockwise / nose-right).

        Note:
            Unlike send_pcmd, these are true metric velocities, not normalized
            [-1, 1] stick values. On the real drone this publishes a body-frame
            velocity straight to the flight controller (which closes the velocity
            loop) and requires OFFBOARD; in simulation an inner loop converts the
            velocity error to tilt, so the same call behaves the same way in both.
            Each axis is clamped to a backend speed limit.

        Example::

            # Fly forward at 0.6 m/s while yawing right to follow a line
            uav.flight.send_body_velocity(0.6, 0.0, 0.0, 0.8)
        """
        pass

    @abc.abstractmethod
    def takeoff(self) -> None:
        """
        Commands the drone to take off and climb, letting the flight controller
        fly the climb.

        Note:
            The safety pilot must arm the motors first; this does not arm. On the
            real drone this commands PX4's AUTO.TAKEOFF mode (the flight controller
            climbs to its takeoff-altitude parameter); in simulation it arms the
            motors and imparts an upward impulse. Once airborne, call
            start_offboard() to hand control back to streamed setpoints.

        Example::

            uav.flight.takeoff()
        """
        pass

    def start_offboard(self) -> None:
        """
        Switches control back to streamed setpoints after a native takeoff or
        landing.

        Note:
            On the real drone this requests PX4 OFFBOARD mode; setpoints must
            already be streaming (send a few send_pcmd / goto_position commands
            first) or PX4 rejects the switch. Poll uav.state.is_offboard() to know
            when it has taken. The default is a no-op for backends (like the
            simulator) that have no separate offboard mode.

        Example::

            uav.flight.start_offboard()
        """
        pass

    @abc.abstractmethod
    def land(self) -> None:
        """
        Sends descending setpoints to the mux.

        Note:
            The safety pilot handles the actual landing mode switch on the
            RC transmitter. This function only sets a downward velocity command.

        Example::

            uav.flight.land()
        """
        pass

    @abc.abstractmethod
    def goto_position(self, east: float, up: float, north: float) -> None:
        """
        Commands the drone to fly to a world position and hold there.

        Args:
            east: Target east coordinate in meters.
            up: Target up coordinate (altitude) in meters.
            north: Target north coordinate in meters.

        Note:
            The argument order matches uav.physics.get_position(), which
            returns (east, up, north), so a captured position can be passed
            straight through:

                start = uav.physics.get_position()
                uav.flight.goto_position(start[0] + 1.0, start[1], start[2])

            Coordinates are absolute in the world frame. On the real drone the
            world origin is wherever the flight controller's EKF initialized, so
            build targets as an offset from a position captured at flight time,
            not as fixed numbers.

            Call this every frame while flying to the target; poll
            uav.physics.get_position() to decide when it has arrived. On the real
            drone the flight controller closes the position loop; in simulation an
            internal controller drives toward the target with velocity commands.

        Example::

            uav.flight.goto_position(target_east, target_up, target_north)
        """
        pass
