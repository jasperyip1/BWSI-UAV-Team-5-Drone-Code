"""
Copyright MIT
GNU General Public License v3.0

MIT BWSI Autonomous Drone Racing Course - UAV Neo

File Name: flight_sim.py
File Description: Flight simulation module — sends flight commands to the UAVNeo Simulator via UDP.
"""

import math
import struct

from flight import Flight


# PD position controller for goto_position (same structure as the velocity-labs'
# waypoint solution): P on horizontal position error, D on velocity for damping,
# P on altitude. Tilting to move sheds vertical lift, so the altitude gain must be
# stiff enough to hold height while translating.
_GOTO_KP_POS = 0.25         # tilt per meter of horizontal position error
_GOTO_KD_POS = 0.5          # tilt per (m/s) of body velocity (damping)
_GOTO_ALT_KP = 0.45         # throttle per meter of altitude error
_GOTO_TILT_LIMIT = 0.3      # horizontal tilt cap
_GOTO_THROTTLE_LIMIT = 0.5

# Inner loop for send_body_velocity: the sim's send_pcmd is a TILT command, so a body
# velocity setpoint is turned into tilt (and vertical velocity into throttle) here -- the
# job the real flight controller does in hardware. Mirrors neo_lab's send_velocity mapping.
_VEL_KP = 0.3              # tilt per (m/s) of horizontal velocity error
_VZ_MPS = 12.0            # throttle scale: ~12 m/s of vertical velocity per unit throttle
_VEL_TILT_LIMIT = 0.5    # keep tilt gentle: sim attitude response is fast and high-authority
_VEL_THROTTLE_LIMIT = 0.5
_VEL_MAX_YAW_RATE = 2.0   # rad/s mapped to a full normalized yaw command


def _clamp(value, limit):
    return max(-limit, min(limit, value))


class FlightSim(Flight):
    def __init__(self, drone) -> None:
        self.__drone = drone

    def send_pcmd(
        self, pitch: float, roll: float, yaw: float, throttle: float
    ) -> None:
        assert -1.0 <= pitch <= 1.0, f"pitch [{pitch}] must be between -1.0 and 1.0 inclusive."
        assert -1.0 <= roll <= 1.0, f"roll [{roll}] must be between -1.0 and 1.0 inclusive."
        assert -1.0 <= yaw <= 1.0, f"yaw [{yaw}] must be between -1.0 and 1.0 inclusive."
        assert -1.0 <= throttle <= 1.0, f"throttle [{throttle}] must be between -1.0 and 1.0 inclusive."

        self.__drone._DroneSim__send_data(
            struct.pack(
                "Bffff",
                self.__drone.Header.flight_send_pcmd.value,
                pitch, roll, yaw, throttle,
            )
        )

    def send_body_velocity(self, v_forward: float, v_right: float, v_up: float,
                           yaw_rate: float = 0.0) -> None:
        """Body-frame velocity setpoint in SI units (m/s, rad/s). The sim's send_pcmd is a
        tilt command, so an inner P loop converts the velocity error to tilt and the vertical
        velocity to throttle -- matching what the real flight controller does, so the same
        call drives the same motion on sim and real."""
        vx, vy, vz = (float(v) for v in self.__drone.physics.get_linear_velocity())  # right, up, fwd
        pitch = _clamp(_VEL_KP * (v_forward - vz), _VEL_TILT_LIMIT)
        roll = _clamp(_VEL_KP * (v_right - vx), _VEL_TILT_LIMIT)
        throttle = _clamp(v_up / _VZ_MPS, _VEL_THROTTLE_LIMIT)
        yaw = _clamp(yaw_rate / _VEL_MAX_YAW_RATE, 1.0)
        self.send_pcmd(pitch, roll, yaw, throttle)

    def set_max_speed(self, max_speed: float = 0.25) -> None:
        assert (
            0.0 <= max_speed <= 1.0
        ), f"max_speed [{max_speed}] must be between 0.0 and 1.0 inclusive."

        self.__drone._DroneSim__send_data(
            struct.pack(
                "Bf",
                self.__drone.Header.flight_set_max_speed.value,
                max_speed,
            )
        )

    def goto_position(self, east: float, up: float, north: float) -> None:
        pos = self.__drone.physics.get_position()      # (east, up, north)
        vel = self.__drone.physics.get_linear_velocity()  # (right, up, forward)
        yaw = self.__drone.physics.get_attitude()[2]   # clockwise from north, deg

        err_east = east - float(pos[0])
        err_up = up - float(pos[1])
        err_north = north - float(pos[2])

        # Rotate the world horizontal error into the body frame. Heading is
        # clockwise from north: forward = (sin, cos) in (east, north), right is
        # 90 deg clockwise of forward.
        psi = math.radians(yaw)
        err_forward = err_east * math.sin(psi) + err_north * math.cos(psi)
        err_right = err_east * math.cos(psi) - err_north * math.sin(psi)

        pitch = _clamp(_GOTO_KP_POS * err_forward - _GOTO_KD_POS * float(vel[2]),
                       _GOTO_TILT_LIMIT)
        roll = _clamp(_GOTO_KP_POS * err_right - _GOTO_KD_POS * float(vel[0]),
                      _GOTO_TILT_LIMIT)
        throttle = _clamp(_GOTO_ALT_KP * err_up, _GOTO_THROTTLE_LIMIT)
        self.send_pcmd(pitch, roll, 0, throttle)

    def takeoff(self) -> bool:
        self.__drone._DroneSim__send_header(
            self.__drone.Header.flight_takeoff
        )
        data = self.__drone._DroneSim__receive_data(1)
        return bool(data[0])

    def land(self) -> bool:
        self.__drone._DroneSim__send_header(
            self.__drone.Header.flight_land
        )
        data = self.__drone._DroneSim__receive_data(1)
        return bool(data[0])
