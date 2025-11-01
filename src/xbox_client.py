"""
Xbox One Wireless Controller BLE Client for MicroPython

Based on working implementations from:
- AndyHegemann/Micropython-ESP32-BLE-Xbox-Controller
- alejandro7896/ESP32_Xbox_Wireless_Controller

Uses standard HID over GATT protocol for Xbox Wireless Controllers.
"""

import asyncio
import aioble
import bluetooth
from utils.constants import DEFAULT_DEAD_ZONE
from utils.ble_utils import format_mac_address
from utils.math_utils import apply_dead_zone, clamp, map_range


# Standard BLE HID UUIDs for Xbox Controller
HID_SERVICE_UUID = bluetooth.UUID(0x1812)  # Human Interface Device
HID_REPORT_CHAR_UUID = bluetooth.UUID(0x2A4D)  # HID Input Report

# Xbox controller device name
XBOX_DEVICE_NAME = "Xbox Wireless Controller"


class ControllerState:
    """
    Represents the current state of the Xbox controller.

    All stick values are normalized to -1.0 to 1.0
    All trigger values are normalized to 0.0 to 1.0
    Buttons are boolean (True = pressed, False = released)
    """

    def __init__(self):
        # Analog sticks (-1.0 to 1.0)
        self.left_stick_x = 0.0
        self.left_stick_y = 0.0
        self.right_stick_x = 0.0
        self.right_stick_y = 0.0

        # Triggers (0.0 to 1.0)
        self.left_trigger = 0.0
        self.right_trigger = 0.0

        # Face buttons
        self.button_a = False
        self.button_b = False
        self.button_x = False
        self.button_y = False

        # Shoulder buttons
        self.button_lb = False  # Left bumper
        self.button_rb = False  # Right bumper

        # Special buttons
        self.button_view = False  # View button (back)
        self.button_menu = False  # Menu button (start)
        self.button_share = False  # Share button (newer controllers)

        # Stick buttons
        self.button_ls = False  # Left stick click
        self.button_rs = False  # Right stick click

        # D-pad
        self.dpad_up = False
        self.dpad_down = False
        self.dpad_left = False
        self.dpad_right = False

    def to_dict(self) -> dict:
        """Convert state to dictionary."""
        return {
            "left_stick_x": self.left_stick_x,
            "left_stick_y": self.left_stick_y,
            "right_stick_x": self.right_stick_x,
            "right_stick_y": self.right_stick_y,
            "left_trigger": self.left_trigger,
            "right_trigger": self.right_trigger,
            "button_a": self.button_a,
            "button_b": self.button_b,
            "button_x": self.button_x,
            "button_y": self.button_y,
            "button_lb": self.button_lb,
            "button_rb": self.button_rb,
            "button_view": self.button_view,
            "button_menu": self.button_menu,
            "button_share": self.button_share,
            "button_ls": self.button_ls,
            "button_rs": self.button_rs,
            "dpad_up": self.dpad_up,
            "dpad_down": self.dpad_down,
            "dpad_left": self.dpad_left,
            "dpad_right": self.dpad_right,
        }

    def __str__(self):
        """String representation for debugging."""
        return (
            f"LS:({self.left_stick_x:.2f},{self.left_stick_y:.2f}) "
            f"RS:({self.right_stick_x:.2f},{self.right_stick_y:.2f}) "
            f"LT:{self.left_trigger:.2f} RT:{self.right_trigger:.2f} "
            f"A:{self.button_a} B:{self.button_b} X:{self.button_x} Y:{self.button_y}"
        )


class XboxClient:
    """
    BLE client for Xbox Wireless Controller.

    Handles connection and input reading from the controller using
    HID over GATT protocol.
    """

    def __init__(self, dead_zone: float = DEFAULT_DEAD_ZONE):
        """
        Initialize the Xbox client.

        Args:
            dead_zone: Dead zone threshold for analog sticks (0.0 to 1.0)
        """
        self.device = None
        self.connection = None
        self.hid_service = None
        self.report_characteristic = None
        self.connected = False
        self.dead_zone = dead_zone

        # Current controller state
        self.state = ControllerState()

        # Callback for input updates
        self.input_callback = None

    async def connect(self, device):
        """
        Connect to an Xbox controller.

        Args:
            device: BLE device object from scan

        Returns:
            True if connection successful, False otherwise
        """
        try:
            print(f"Connecting to Xbox controller: {format_mac_address(device)}...")
            self.device = device

            # Connect to the device
            self.connection = await device.connect(timeout_ms=10000)
            print("Connected! Discovering services...")

            # Discover HID service
            try:
                self.hid_service = await self.connection.service(HID_SERVICE_UUID)
                print(f"Found HID service: {HID_SERVICE_UUID}")
            except Exception as e:
                print(f"HID service discovery failed: {e}")
                await self.disconnect()
                return False

            # Get HID Report characteristic
            try:
                self.report_characteristic = await self.hid_service.characteristic(
                    HID_REPORT_CHAR_UUID
                )
                print(f"Found HID Report characteristic: {HID_REPORT_CHAR_UUID}")
            except Exception as e:
                print(f"Report characteristic discovery failed: {e}")
                await self.disconnect()
                return False

            # Pair without authentication (Xbox controllers typically don't require PIN)
            # This happens automatically in aioble when subscribing to notifications

            self.connected = True
            print("Xbox controller connected successfully!")
            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from the Xbox controller."""
        if self.connection:
            try:
                await self.connection.disconnect()
                print("Disconnected from Xbox controller")
            except Exception as e:
                print(f"Disconnect error: {e}")

        self.connection = None
        self.hid_service = None
        self.report_characteristic = None
        self.connected = False

    def is_connected(self) -> bool:
        """Check if currently connected to the controller."""
        return self.connected and self.connection is not None

    def parse_hid_report(self, report: bytes):
        """
        Parse HID input report data and update controller state.

        Xbox Wireless Controller HID Report Format (via BLE):
        - Bytes 0-1:   Left stick X (uint16 little-endian, 0-65535)
        - Bytes 2-3:   Left stick Y (uint16 little-endian, 0-65535)
        - Bytes 4-5:   Right stick X (uint16 little-endian, 0-65535)
        - Bytes 6-7:   Right stick Y (uint16 little-endian, 0-65535)
        - Bytes 8-9:   Left trigger (uint16 little-endian, 0-1023)
        - Bytes 10-11: Right trigger (uint16 little-endian, 0-1023)
        - Byte 12:     D-pad (bit pattern: 0b1=up, 0b11=up-right, 0b101=down, 0b111=down-right)
        - Byte 13:     Buttons (A=0x01, B=0x02, X=0x08, Y=0x10, LB=0x40, RB=0x80)
        - Byte 14:     More buttons (View=0x04, Menu=0x08, LS=0x20, RS=0x40)

        Args:
            report: Raw HID report bytes (minimum 15 bytes)
        """
        if not report or len(report) < 15:
            return

        # Parse analog sticks (0-65535 → -1.0 to 1.0)
        left_x_raw = int.from_bytes(report[0:2], 'little')
        left_y_raw = int.from_bytes(report[2:4], 'little')
        right_x_raw = int.from_bytes(report[4:6], 'little')
        right_y_raw = int.from_bytes(report[6:8], 'little')

        # Map to -1.0 to 1.0 and apply dead zone
        self.state.left_stick_x = apply_dead_zone(
            map_range(left_x_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )
        self.state.left_stick_y = apply_dead_zone(
            map_range(left_y_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )
        self.state.right_stick_x = apply_dead_zone(
            map_range(right_x_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )
        self.state.right_stick_y = apply_dead_zone(
            map_range(right_y_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )

        # Parse triggers (0-1023 → 0.0 to 1.0)
        left_trigger_raw = int.from_bytes(report[8:10], 'little')
        right_trigger_raw = int.from_bytes(report[10:12], 'little')

        self.state.left_trigger = left_trigger_raw / 1023.0
        self.state.right_trigger = right_trigger_raw / 1023.0

        # Parse D-pad (byte 12)
        # D-pad uses bit patterns: 1=up, 3=up-right, 5=down, 7=down-right, etc.
        dpad = report[12]
        self.state.dpad_up = (dpad == 0b1) or (dpad == 0b11)
        self.state.dpad_down = (dpad == 0b101) or (dpad == 0b111)
        self.state.dpad_left = (dpad == 0b1001) or (dpad == 0b1011)
        self.state.dpad_right = (dpad == 0b11) or (dpad == 0b111)

        # Parse face buttons and bumpers (byte 13)
        buttons = report[13]
        self.state.button_a = bool(buttons & 0x01)
        self.state.button_b = bool(buttons & 0x02)
        self.state.button_x = bool(buttons & 0x08)
        self.state.button_y = bool(buttons & 0x10)
        self.state.button_lb = bool(buttons & 0x40)
        self.state.button_rb = bool(buttons & 0x80)

        # Parse special buttons (byte 14)
        more_buttons = report[14]
        self.state.button_view = bool(more_buttons & 0x04)
        self.state.button_menu = bool(more_buttons & 0x08)
        self.state.button_ls = bool(more_buttons & 0x20)  # Left stick click
        self.state.button_rs = bool(more_buttons & 0x40)  # Right stick click
        self.state.button_share = bool(more_buttons & 0x01)  # Share button (if present)

        # Call callback if registered
        if self.input_callback:
            try:
                self.input_callback(self.state)
            except Exception as e:
                print(f"Input callback error: {e}")

    async def start_input_loop(self, callback=None):
        """
        Start the input reading loop.

        This subscribes to HID notifications and continuously processes
        controller inputs.

        Args:
            callback: Optional callback function(state: ControllerState)
                     Called whenever input state changes

        Note: This function runs indefinitely. Run it as an asyncio task.
        """
        if not self.is_connected():
            print("Not connected to controller")
            return False

        if self.report_characteristic is None:
            print("Report characteristic not available")
            return False

        self.input_callback = callback

        try:
            print("Starting input loop...")

            # Subscribe to notifications from the HID report characteristic
            # This will receive controller input data
            while self.is_connected():
                try:
                    # Read the report (this blocks until data is available)
                    report = await self.report_characteristic.notified()

                    # Parse and update state
                    if report:
                        self.parse_hid_report(report)

                except Exception as e:
                    print(f"Input read error: {e}")
                    # Small delay before retry
                    await asyncio.sleep_ms(100)

        except Exception as e:
            print(f"Input loop error: {e}")
            return False

    def get_state(self) -> ControllerState:
        """
        Get the current controller state.

        Returns:
            Current ControllerState object
        """
        return self.state

    def get_connection_info(self) -> dict:
        """
        Get information about the current connection.

        Returns:
            Dictionary with connection details
        """
        return {
            "connected": self.connected,
            "device": format_mac_address(self.device) if self.device else None,
            "hid_service": str(HID_SERVICE_UUID),
            "device_name": XBOX_DEVICE_NAME,
        }

    def set_dead_zone(self, dead_zone: float):
        """
        Set the dead zone for analog sticks.

        Args:
            dead_zone: Dead zone threshold (0.0 to 1.0)
        """
        self.dead_zone = clamp(dead_zone, 0.0, 1.0)

    async def wait_for_button(self, button_name: str, timeout_ms: int = 10000) -> bool:
        """
        Wait for a specific button to be pressed.

        Args:
            button_name: Name of button attribute (e.g., "button_a", "button_start")
            timeout_ms: Timeout in milliseconds

        Returns:
            True if button was pressed, False on timeout
        """
        if not self.is_connected():
            return False

        start_time = asyncio.ticks_ms()

        while (asyncio.ticks_ms() - start_time) < timeout_ms:
            if hasattr(self.state, button_name) and getattr(self.state, button_name):
                return True
            await asyncio.sleep_ms(10)

        return False
