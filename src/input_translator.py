"""
Input Translator - Maps Xbox Controller inputs to LEGO vehicle commands

Converts Xbox controller state (buttons, sticks, triggers) into motor speed
and lighting commands for LEGO Technic Hub.

Control Scheme:
- Left Stick Y-axis: Forward/backward speed (Steering motor A)
- Right Stick X-axis: Left/right steering (Steering motor B)
- Left Trigger: Brake (reduces all motor speeds)
- Right Trigger: Boost (increases motor speeds)
- A button: Toggle headlights
- B button: Toggle taillights
- X button: Emergency stop (all motors to 0)
- Y button: Horn/flash (future feature)
- D-pad Up: Increase max speed limit
- D-pad Down: Decrease max speed limit
- LB: Cycle control mode (normal -> turbo -> slow)
- RB: (Reserved for future use)
- Menu: (Reserved for future use)
- View: (Reserved for future use)

Control Modes:
- Normal: Standard responsiveness and speed limits
- Turbo: Higher max speed, more aggressive response
- Slow: Lower max speed, gentler response (for precision)
"""

from src.xbox_client import ControllerState
from src.utils.constants import LEGO_COLORS


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
        led_color: LED color (LEGO_COLORS constant)
        emergency_stop: True to immediately stop all motors
    """
    def __init__(self):
        self.motor_a_speed = 0
        self.motor_b_speed = 0
        self.led_color = LEGO_COLORS.BLACK  # Off by default
        self.emergency_stop = False

    def __repr__(self):
        return (f"VehicleCommand(motor_a={self.motor_a_speed}, "
                f"motor_b={self.motor_b_speed}, "
                f"led={self.led_color}, "
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

    def __init__(self):
        """Initialize translator with default settings."""
        self.mode = ControlMode.NORMAL
        self.max_speed_limit = 100  # User-adjustable limit (0-100)
        self.speed_limit_step = 10  # Amount to change per D-pad press

        # State tracking for button presses (to detect edges)
        self._prev_button_a = False
        self._prev_button_b = False
        self._prev_button_x = False
        self._prev_button_lb = False
        self._prev_dpad_up = False
        self._prev_dpad_down = False

        # LED state tracking
        self.headlights_on = False
        self.taillights_on = False

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

    def _update_led_state(self, state: ControllerState) -> int:
        """
        Update LED state based on button presses.

        Args:
            state: Current controller state

        Returns:
            LED color value
        """
        # A button toggles headlights (white)
        if self._handle_button_press(state.button_a, self._prev_button_a):
            self.headlights_on = not self.headlights_on
            print(f"Headlights: {'ON' if self.headlights_on else 'OFF'}")

        # B button toggles taillights (red)
        if self._handle_button_press(state.button_b, self._prev_button_b):
            self.taillights_on = not self.taillights_on
            print(f"Taillights: {'ON' if self.taillights_on else 'OFF'}")

        # Determine color based on state
        if self.headlights_on and self.taillights_on:
            return LEGO_COLORS.YELLOW  # Both on = yellow (compromise)
        elif self.headlights_on:
            return LEGO_COLORS.WHITE
        elif self.taillights_on:
            return LEGO_COLORS.RED
        else:
            return LEGO_COLORS.BLACK  # Off

    def translate(self, state: ControllerState) -> VehicleCommand:
        """
        Translate controller state to vehicle command.

        Args:
            state: Current Xbox controller state

        Returns:
            VehicleCommand with motor speeds and LED state
        """
        cmd = VehicleCommand()

        # Handle emergency stop (X button)
        if self._handle_button_press(state.button_x, self._prev_button_x):
            print("EMERGENCY STOP")
            cmd.emergency_stop = True
            self._update_button_state(state)
            return cmd

        # Handle mode cycling (LB button)
        if self._handle_button_press(state.button_lb, self._prev_button_lb):
            self.cycle_mode()

        # Handle speed limit adjustment (D-pad up/down)
        if self._handle_button_press(state.dpad_up, self._prev_dpad_up):
            self.adjust_speed_limit(self.speed_limit_step)
        if self._handle_button_press(state.dpad_down, self._prev_dpad_down):
            self.adjust_speed_limit(-self.speed_limit_step)

        # Get mode parameters
        params = self.MODE_PARAMS[self.mode]
        curve_power = params['curve_power']
        mode_max_speed = params['max_speed']

        # Calculate effective max speed (mode limit AND user limit)
        effective_max_speed = min(mode_max_speed, self.max_speed_limit)

        # Get stick inputs
        drive_input = state.left_stick_y  # Forward/backward
        steer_input = state.right_stick_x  # Left/right

        # Apply control curves
        drive_curved = self._apply_control_curve(drive_input, curve_power)
        steer_curved = self._apply_control_curve(steer_input, curve_power)

        # Apply trigger modifiers
        brake_amount = state.left_trigger  # 0.0 to 1.0
        boost_amount = state.right_trigger  # 0.0 to 1.0

        # Brake reduces speed (0.0 = no brake, 1.0 = full brake)
        # When fully braking, reduce to 20% of intended speed
        brake_multiplier = 1.0 - (brake_amount * 0.8)

        # Boost increases speed (0.0 = no boost, 1.0 = +50% speed)
        # But can't exceed 100% motor speed
        boost_multiplier = 1.0 + (boost_amount * 0.5)

        # Combine modifiers (brake takes priority)
        speed_multiplier = brake_multiplier * boost_multiplier

        # Calculate final motor speeds
        drive_scaled = drive_curved * speed_multiplier
        steer_scaled = steer_curved

        cmd.motor_a_speed = self._scale_to_motor_speed(drive_scaled, effective_max_speed)
        cmd.motor_b_speed = self._scale_to_motor_speed(steer_scaled, effective_max_speed)

        # Update LED state
        cmd.led_color = self._update_led_state(state)

        # Update button state tracking
        self._update_button_state(state)

        return cmd

    def _update_button_state(self, state: ControllerState):
        """Update previous button states for edge detection."""
        self._prev_button_a = state.button_a
        self._prev_button_b = state.button_b
        self._prev_button_x = state.button_x
        self._prev_button_lb = state.button_lb
        self._prev_dpad_up = state.dpad_up
        self._prev_dpad_down = state.dpad_down

    def get_status(self) -> dict:
        """
        Get current translator status.

        Returns:
            Dictionary with mode, limits, and LED states
        """
        return {
            'mode': self.mode,
            'max_speed_limit': self.max_speed_limit,
            'headlights': self.headlights_on,
            'taillights': self.taillights_on
        }
