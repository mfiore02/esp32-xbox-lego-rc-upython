"""
Input Translator - Maps Xbox Controller inputs to LEGO vehicle commands

Converts Xbox controller state (buttons, sticks, triggers) into motor speed
and lighting commands for LEGO Technic Hub.

Control Scheme:
- Right Trigger: Gas pedal (accelerator)
- Left Trigger: Brake pedal
- Right Stick X-axis: Left/right steering (motor B)
- Left Stick: (Reserved)
- Right Bumper: Increase speed limit
- Left Bumper: Decrease speed limit
- A button: Toggle lights
- B button: Toggle direction (forward/reverse)
- X button: (Reserved)
- Y button: (Reserved)
- D-pad Up: Increase drive ramping (slower acceleration)
- D-pad Down: Decrease drive ramping (faster acceleration)
- D-pad Left: Increase steering ramping (slower steering)
- D-pad Right: Decrease steering ramping (faster steering)
- Menu: (Reserved)
- View: (Reserved)

Control Modes:
- Normal: Standard responsiveness and speed limits
- Turbo: Higher max speed, more aggressive response
- Slow: Lower max speed, gentler response (for precision)
"""

from src.xbox_client import ControllerState
from src.utils.constants import LIGHTS_OFF, LIGHTS_ON, LIGHTS_BRAKE


class ControlMode:
    """Control mode presets for different driving styles."""
    NORMAL = "normal"
    TURBO = "turbo"
    SLOW = "slow"


class VehicleCommand:
    """
    Represents a complete set of commands for the LEGO vehicle.

    Attributes:
        motor_a_speed: Motor A speed (-100 to 100)
        motor_b_speed: Motor B speed (-100 to 100)
        lights: State of vehicle lights (one of LIGHTS_* constants)
        emergency_stop: True to immediately stop all motors
    """
    def __init__(self):
        self.motor_a_speed = 0
        self.motor_b_speed = 0
        self.lights = LIGHTS_OFF
        self.brake = False
        self.emergency_stop = False

    def __repr__(self):
        return (f"VehicleCommand(motor_a={self.motor_a_speed}, "
                f"motor_b={self.motor_b_speed}, "
                f"lights={self.lights}, "
                f"e_stop={self.emergency_stop})")


class InputTranslator:
    """
    Translates Xbox controller state to LEGO vehicle commands.

    Handles control modes, speed limiting, button actions, and smooth control curves.
    """

    # Control mode parameters
    MODE_PARAMS = {
        ControlMode.NORMAL: {
            'max_speed': 100,
            'curve_power': 2.0,  # Quadratic curve for smooth control
            'dead_zone': 0.03
        },
        ControlMode.TURBO: {
            'max_speed': 100,
            'curve_power': 1.5,  # More linear/aggressive
            'dead_zone': 0.05
        },
        ControlMode.SLOW: {
            'max_speed': 50,
            'curve_power': 2.5,  # More gradual
            'dead_zone': 0.02
        }
    }

    def __init__(self, max_drive_speed_change_per_update: float | None = None,
                 max_steer_speed_change_per_update: float | None = None):
        """
        Initialize translator with default settings.

        Args:
            max_drive_speed_change_per_update: Maximum change in drive motor speed (0-100 scale) per call to translate().
                                               Controls how quickly drive motor ramps to target speeds.
                                               Set to None for instant response (no ramping).
                                               Adjustable via D-pad Up/Down during runtime.
            max_steer_speed_change_per_update: Maximum change in steering motor speed (0-100 scale) per call to translate().
                                               Controls how quickly steering motor ramps to target speeds.
                                               Set to None for instant response (no ramping).
                                               Adjustable via D-pad Left/Right during runtime.
        """
        self.mode = ControlMode.NORMAL
        self.max_speed_limit = 100  # User-adjustable limit (0-100)
        self.speed_limit_step = 10  # Amount to change per bumper press

        # Speed ramping configuration (separate for drive and steering)
        self.max_drive_speed_change_per_update = max_drive_speed_change_per_update
        self.max_steer_speed_change_per_update = max_steer_speed_change_per_update
        self.ramping_adjustment_step = 1.0  # Amount to change ramping by per D-pad press

        # State tracking for button presses (to detect edges)
        self._prev_button_a = False
        self._prev_button_b = False
        self._prev_button_rb = False
        self._prev_button_lb = False
        self._prev_dpad_up = False
        self._prev_dpad_down = False
        self._prev_dpad_left = False
        self._prev_dpad_right = False

        # LED state tracking
        self.lights_on = False
        self.brake_lights_on = False

        # Direction state (forward = 1, reverse = -1)
        self.direction = 1

        # Current motor speeds (for ramping) - track actual values being output
        self._current_motor_a_speed = 0
        self._current_motor_b_speed = 0

    def set_mode(self, mode: str):
        """
        Set control mode.

        Args:
            mode: One of ControlMode.NORMAL, TURBO, or SLOW
        """
        if mode in self.MODE_PARAMS:
            self.mode = mode
            print(f"Control mode: {mode}")
        else:
            print(f"Warning: Unknown mode '{mode}', staying in {self.mode}")

    def cycle_mode(self):
        """Cycle to next control mode."""
        modes = [ControlMode.NORMAL, ControlMode.TURBO, ControlMode.SLOW]
        current_idx = modes.index(self.mode)
        next_idx = (current_idx + 1) % len(modes)
        self.set_mode(modes[next_idx])

    def adjust_speed_limit(self, delta: int):
        """
        Adjust max speed limit.

        Args:
            delta: Amount to change limit by (positive or negative)
        """
        self.max_speed_limit = max(0, min(100, self.max_speed_limit + delta))
        print(f"Speed limit: {self.max_speed_limit}%")

    def _adjust_drive_ramping(self, delta: float):
        """
        Adjust drive motor ramping rate.

        Args:
            delta: Amount to change ramping by (positive = slower, negative = faster)
        """
        if self.max_drive_speed_change_per_update is None:
            # Initialize from None to a starting value
            self.max_drive_speed_change_per_update = 10.0 + delta
        else:
            self.max_drive_speed_change_per_update += delta

        # Clamp to reasonable values (0.5 to 100 for instant)
        if self.max_drive_speed_change_per_update < 0.5:
            self.max_drive_speed_change_per_update = None  # Disable (instant)
            print("Drive ramping: INSTANT")
        elif self.max_drive_speed_change_per_update >= 100:
            self.max_drive_speed_change_per_update = None  # Disable (instant)
            print("Drive ramping: INSTANT")
        else:
            # Calculate approximate time to reach full speed
            time_ms = int((100 / self.max_drive_speed_change_per_update) * 10)
            print(f"Drive ramping: {self.max_drive_speed_change_per_update:.1f} (~{time_ms}ms to full)")

    def _adjust_steer_ramping(self, delta: float):
        """
        Adjust steering motor ramping rate.

        Args:
            delta: Amount to change ramping by (positive = slower, negative = faster)
        """
        if self.max_steer_speed_change_per_update is None:
            # Initialize from None to a starting value
            self.max_steer_speed_change_per_update = 10.0 + delta
        else:
            self.max_steer_speed_change_per_update += delta

        # Clamp to reasonable values (0.5 to 100 for instant)
        if self.max_steer_speed_change_per_update < 0.5:
            self.max_steer_speed_change_per_update = None  # Disable (instant)
            print("Steering ramping: INSTANT")
        elif self.max_steer_speed_change_per_update >= 100:
            self.max_steer_speed_change_per_update = None  # Disable (instant)
            print("Steering ramping: INSTANT")
        else:
            # Calculate approximate time to reach full steering
            time_ms = int((100 / self.max_steer_speed_change_per_update) * 10)
            print(f"Steering ramping: {self.max_steer_speed_change_per_update:.1f} (~{time_ms}ms to full)")

    def _apply_control_curve(self, value: float, power: float) -> float:
        """
        Apply exponential control curve for smoother control.

        Args:
            value: Input value (-1.0 to 1.0)
            power: Curve exponent (higher = more gradual near center)

        Returns:
            Curved value maintaining sign
        """
        if value == 0:
            return 0.0

        sign = 1 if value > 0 else -1
        abs_value = abs(value)
        curved = pow(abs_value, power)
        return sign * curved

    def _scale_to_motor_speed(self, value: float, max_speed: int) -> int:
        """
        Scale normalized value to motor speed.

        Args:
            value: Normalized value (-1.0 to 1.0)
            max_speed: Maximum allowed speed

        Returns:
            Motor speed (-100 to 100)
        """
        speed = round(value * max_speed)
        return max(-100, min(100, speed))

    def _ramp_speed(self, current_speed: int, target_speed: int, max_speed_change: float | None) -> int:
        """
        Apply ramping to smoothly transition from current to target speed.

        Args:
            current_speed: Current motor speed (-100 to 100)
            target_speed: Desired target speed (-100 to 100)
            max_speed_change: Maximum speed change allowed per update (None = instant)

        Returns:
            New motor speed, ramped toward target by at most max_speed_change
        """
        # If ramping is disabled, return target immediately
        if max_speed_change is None:
            return target_speed

        # Calculate the difference between target and current
        speed_diff = target_speed - current_speed

        # If we're already at target, return it
        if speed_diff == 0:
            return target_speed

        # Limit the change to max_speed_change
        if abs(speed_diff) <= max_speed_change:
            # We can reach the target in this update
            return target_speed
        else:
            # Ramp toward target by max allowed amount
            if speed_diff > 0:
                return current_speed + int(max_speed_change)
            else:
                return current_speed - int(max_speed_change)

    def _handle_button_press(self, current: bool, previous: bool) -> bool:
        """
        Detect rising edge of button press.

        Args:
            current: Current button state
            previous: Previous button state

        Returns:
            True if button was just pressed (rising edge)
        """
        return current and not previous

    def translate(self, state: ControllerState) -> VehicleCommand:
        """
        Translate controller state to vehicle command.

        Args:
            state: Current Xbox controller state

        Returns:
            VehicleCommand with motor speeds and LED state
        """
        cmd = VehicleCommand()

        # Handle direction toggle (B button)
        if self._handle_button_press(state.button_b, self._prev_button_b):
            self.direction *= -1  # Toggle between 1 and -1
            direction_text = "FORWARD" if self.direction == 1 else "REVERSE"
            print(f"Direction: {direction_text}")

        # Handle speed limit adjustment (bumpers)
        if self._handle_button_press(state.button_rb, self._prev_button_rb):
            self.adjust_speed_limit(self.speed_limit_step)
        if self._handle_button_press(state.button_lb, self._prev_button_lb):
            self.adjust_speed_limit(-self.speed_limit_step)

        # Handle lights (A button)
        if self._handle_button_press(state.button_a, self._prev_button_a):
            self.lights_on = not self.lights_on

        # Handle ramping adjustments (D-pad)
        # D-pad Up: Increase drive ramping (slower acceleration)
        if self._handle_button_press(state.dpad_up, self._prev_dpad_up):
            self._adjust_drive_ramping(self.ramping_adjustment_step)
        # D-pad Down: Decrease drive ramping (faster acceleration)
        if self._handle_button_press(state.dpad_down, self._prev_dpad_down):
            self._adjust_drive_ramping(-self.ramping_adjustment_step)
        # D-pad Left: Increase steering ramping (slower steering)
        if self._handle_button_press(state.dpad_left, self._prev_dpad_left):
            self._adjust_steer_ramping(self.ramping_adjustment_step)
        # D-pad Right: Decrease steering ramping (faster steering)
        if self._handle_button_press(state.dpad_right, self._prev_dpad_right):
            self._adjust_steer_ramping(-self.ramping_adjustment_step)

        # Get mode parameters
        params = self.MODE_PARAMS[self.mode]
        curve_power = params['curve_power']
        mode_max_speed = params['max_speed']

        # Calculate effective max speed (mode limit AND user limit)
        effective_max_speed = min(mode_max_speed, self.max_speed_limit)

        # Get trigger inputs (gas and brake pedals)
        gas_pedal = state.right_trigger  # 0.0 to 1.0
        brake_pedal = state.left_trigger  # 0.0 to 1.0

        # Get steering from right stick X-axis
        steer_input = state.right_stick_x  # -1.0 to 1.0

        # Calculate drive input from gas and brake
        # Gas pedal = positive drive, brake = negative drive
        # When both pressed, brake takes priority
        if brake_pedal > 0.0:
            # Braking - apply brake amount as negative drive
            drive_input = -brake_pedal
        else:
            # Accelerating - apply gas amount as positive drive
            drive_input = gas_pedal

        # Special case: if both triggers are released, immediately stop drive motor
        # This prevents unwanted coasting after braking and releasing
        if gas_pedal == 0.0 and brake_pedal == 0.0:
            self._current_motor_a_speed = 0

        # Apply control curves for smooth response
        drive_curved = self._apply_control_curve(drive_input, curve_power)
        steer_curved = self._apply_control_curve(steer_input, curve_power)

        # Apply direction multiplier (forward = 1, reverse = -1)
        drive_with_direction = drive_curved * self.direction

        # Calculate target motor speeds (what the controller is requesting)
        target_motor_a_speed = self._scale_to_motor_speed(drive_with_direction, effective_max_speed)
        target_motor_b_speed = self._scale_to_motor_speed(steer_curved, 100)  # Steering not limited by speed limit

        # Apply ramping to smoothly transition to target speeds (only if not already stopped)
        if not (gas_pedal == 0.0 and brake_pedal == 0.0):
            self._current_motor_a_speed = self._ramp_speed(
                self._current_motor_a_speed,
                target_motor_a_speed,
                self.max_drive_speed_change_per_update
            )
        self._current_motor_b_speed = self._ramp_speed(
            self._current_motor_b_speed,
            target_motor_b_speed,
            self.max_steer_speed_change_per_update
        )

        # Use the ramped speeds as the final output
        cmd.motor_a_speed = self._current_motor_a_speed
        cmd.motor_b_speed = self._current_motor_b_speed

        # Update LED state
        # Show brake lights when brake pedal is pressed
        if brake_pedal > 0.1:  # Small threshold to avoid noise
            cmd.lights = LIGHTS_BRAKE if self.lights_on else LIGHTS_BRAKE
        else:
            cmd.lights = LIGHTS_ON if self.lights_on else LIGHTS_OFF

        # Update button state tracking
        self._update_button_state(state)

        return cmd

    def _update_button_state(self, state: ControllerState):
        """Update previous button states for edge detection."""
        self._prev_button_a = state.button_a
        self._prev_button_b = state.button_b
        self._prev_button_rb = state.button_rb
        self._prev_button_lb = state.button_lb
        self._prev_dpad_up = state.dpad_up
        self._prev_dpad_down = state.dpad_down
        self._prev_dpad_left = state.dpad_left
        self._prev_dpad_right = state.dpad_right

    def get_status(self) -> dict:
        """
        Get current translator status.

        Returns:
            Dictionary with mode, limits, and light status
        """
        return {
            'mode': self.mode,
            'max_speed_limit': self.max_speed_limit,
            'lights_on': self.lights_on,
            'brake_lights_on': self.brake_lights_on,
            'direction': 'forward' if self.direction == 1 else 'reverse',
        }
