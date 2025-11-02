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
HID_REPORT_MAP_UUID = bluetooth.UUID(0x2A4B)  # HID Report Map

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

            # Pair with the controller (required for it to send input data!)
            # Without pairing, the controller stays in pairing mode and won't send HID reports
            try:
                print("Pairing with Xbox controller...")
                await self.connection.pair(bond=True)
                print("Paired successfully!")
            except Exception as e:
                print(f"Pairing failed: {e}")
                print("Warning: Controller may not send input data without pairing")
                # Don't fail here - try to continue anyway

            # CRITICAL: Read the Report Map characteristic
            # This is required to initialize the controller and enable HID notifications!
            # Without this, the controller won't send any input data.
            try:
                print("Reading HID Report Map (required for initialization)...")
                report_map_char = await self.hid_service.characteristic(HID_REPORT_MAP_UUID)
                report_map = await report_map_char.read()
                print(f"Report Map read: {len(report_map)} bytes")
            except Exception as e:
                print(f"Warning: Could not read Report Map: {e}")
                print("Controller may not send input data without this!")
                # Continue anyway, but it probably won't work

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
        - Bytes 2-3:   Left stick Y (uint16 little-endian, 0-65535, inverted: low=up)
        - Bytes 4-5:   Right stick X (uint16 little-endian, 0-65535)
        - Bytes 6-7:   Right stick Y (uint16 little-endian, 0-65535, inverted: low=up)
        - Bytes 8-9:   Left trigger (uint16 little-endian, 0-1023)
        - Bytes 10-11: Right trigger (uint16 little-endian, 0-1023)
        - Byte 12:     D-pad (8-direction: 0/15=center, 1=up, 2=up-right, 3=right,
                       4=down-right, 5=down, 6=down-left, 7=left, 8=up-left)
        - Byte 13:     Buttons (A=0x01, B=0x02, X=0x08, Y=0x10, LB=0x40, RB=0x80)
        - Byte 14:     More buttons (View=0x04, Menu=0x08, LS=0x20, RS=0x40, Share=0x01*)
                       *Note: Share button detection may not work on all controller revisions

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
        # Note: Y-axis is inverted (up = negative raw value, so we negate after mapping)
        self.state.left_stick_x = apply_dead_zone(
            map_range(left_x_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )
        self.state.left_stick_y = apply_dead_zone(
            -map_range(left_y_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )
        self.state.right_stick_x = apply_dead_zone(
            map_range(right_x_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )
        self.state.right_stick_y = apply_dead_zone(
            -map_range(right_y_raw, 0, 65535, -1.0, 1.0), self.dead_zone
        )

        # Parse triggers (0-1023 → 0.0 to 1.0)
        left_trigger_raw = int.from_bytes(report[8:10], 'little')
        right_trigger_raw = int.from_bytes(report[10:12], 'little')

        self.state.left_trigger = left_trigger_raw / 1023.0
        self.state.right_trigger = right_trigger_raw / 1023.0

        # Parse D-pad (byte 12)
        # D-pad uses standard 8-direction encoding:
        # 0/15=center, 1=up, 2=up-right, 3=right, 4=down-right, 5=down, 6=down-left, 7=left, 8=up-left
        dpad = report[12]
        self.state.dpad_up = dpad in (1, 2, 8)       # up, up-right, up-left
        self.state.dpad_down = dpad in (4, 5, 6)     # down-right, down, down-left
        self.state.dpad_left = dpad in (6, 7, 8)     # down-left, left, up-left
        self.state.dpad_right = dpad in (2, 3, 4)    # up-right, right, down-right

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
        # Note: Share button detection may not work on all controller revisions
        # Some controllers don't report this button via BLE, or use different encoding
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
            # This enables the controller to send input data to us
            print("Subscribing to HID notifications...")
            await self.report_characteristic.subscribe(notify=True)
            print("Subscribed! Waiting for input data...")

            # Now read reports as they come in
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
    
    def format_bar(self, value, width=10, char="█"):
        """Create a visual bar for analog values."""
        if value >= 0:
            filled = int(value * width)
            return char * filled + "·" * (width - filled)
        else:
            filled = int(abs(value) * width)
            return "·" * (width - filled) + char * filled
    
    def format_state_compact(self, state):
        """Format complete controller state for display in as few lines as possible."""
        lines = []

        # Buttons
        a = "●" if state.button_a else "○"
        b = "●" if state.button_b else "○"
        x = "●" if state.button_x else "○"
        y = "●" if state.button_y else "○"
        lb = "●" if state.button_lb else "○"
        rb = "●" if state.button_rb else "○"
        lines.append(f"A:{a} B:{b} X:{x} Y:{y} LB:{lb} RB:{rb}")

        # Sticks/Triggers
        ls = "●" if state.button_ls else "○"
        lsx = f"{state.left_stick_x:+.2f}"
        lsy = f"{state.left_stick_y:+.2f}"
        rs = "●" if state.button_rs else "○"
        rsx = f"{state.right_stick_x:+.2f}"
        rsy = f"{state.right_stick_y:+.2f}"
        lt = f"{state.left_trigger:.2f}"
        rt = f"{state.right_trigger:.2f}"
        lines.append(f"LS: {ls} X/Y {lsx}/{lsy} | RS: {rs} X/Y {rsx}/{rsy} | LT: {lt} | RT: {rt}")

        # D-pad/Special Buttons
        up = "▲" if state.dpad_up else "△"
        down = "▼" if state.dpad_down else "▽"
        left = "◀" if state.dpad_left else "◁"
        right = "▶" if state.dpad_right else "▷"
        view = "●" if state.button_view else "○"
        menu = "●" if state.button_menu else "○"
        share = "●" if state.button_share else "○"
        lines.append(f"D-PAD: {up} {down} {left} {right} | View:{view} Menu:{menu} Share:{share}")

        return "\n".join(lines)
    
    def format_state(self, state):
        """Format complete controller state for display."""
        lines = []
        lines.append("┌" + "─" * 58 + "┐")
        lines.append("│" + " " * 18 + "CONTROLLER STATE" + " " * 24 + "│")
        lines.append("├" + "─" * 58 + "┤")

        # Face Buttons
        lines.append("│ FACE BUTTONS:                                           │")
        a = "●" if state.button_a else "○"
        b = "●" if state.button_b else "○"
        x = "●" if state.button_x else "○"
        y = "●" if state.button_y else "○"
        lines.append(f"│   A:{a}  B:{b}  X:{x}  Y:{y}" + " " * 31 + "│")

        # Shoulder Buttons
        lines.append("│                                                          │")
        lines.append("│ SHOULDER BUTTONS:                                        │")
        lb = "●" if state.button_lb else "○"
        rb = "●" if state.button_rb else "○"
        lines.append(f"│   LB:{lb}  RB:{rb}" + " " * 39 + "│")

        # Special Buttons
        lines.append("│                                                          │")
        lines.append("│ SPECIAL BUTTONS:                                         │")
        view = "●" if state.button_view else "○"
        menu = "●" if state.button_menu else "○"
        share = "●" if state.button_share else "○"
        lines.append(f"│   View:{view}  Menu:{menu}  Share:{share}" + " " * 23 + "│")

        # Stick Clicks
        lines.append("│                                                          │")
        lines.append("│ STICK CLICKS:                                            │")
        ls = "●" if state.button_ls else "○"
        rs = "●" if state.button_rs else "○"
        lines.append(f"│   LS:{ls}  RS:{rs}" + " " * 39 + "│")

        # D-pad
        lines.append("│                                                          │")
        lines.append("│ D-PAD:                                                   │")
        up = "▲" if state.dpad_up else "△"
        down = "▼" if state.dpad_down else "▽"
        left = "◀" if state.dpad_left else "◁"
        right = "▶" if state.dpad_right else "▷"
        lines.append(f"│   Up:{up}  Down:{down}  Left:{left}  Right:{right}" + " " * 19 + "│")

        # Left Stick
        lines.append("│                                                          │")
        lines.append("│ LEFT STICK:                                              │")
        lines.append(f"│   X: {state.left_stick_x:+.2f} [{self.format_bar(state.left_stick_x)}]" + " " * 13 + "│")
        lines.append(f"│   Y: {state.left_stick_y:+.2f} [{self.format_bar(state.left_stick_y)}]" + " " * 13 + "│")

        # Right Stick
        lines.append("│                                                          │")
        lines.append("│ RIGHT STICK:                                             │")
        lines.append(f"│   X: {state.right_stick_x:+.2f} [{self.format_bar(state.right_stick_x)}]" + " " * 13 + "│")
        lines.append(f"│   Y: {state.right_stick_y:+.2f} [{self.format_bar(state.right_stick_y)}]" + " " * 13 + "│")

        # Triggers
        lines.append("│                                                          │")
        lines.append("│ TRIGGERS:                                                │")
        lines.append(f"│   LT: {state.left_trigger:.2f} [{self.format_bar(state.left_trigger)}]" + " " * 14 + "│")
        lines.append(f"│   RT: {state.right_trigger:.2f} [{self.format_bar(state.right_trigger)}]" + " " * 14 + "│")

        lines.append("└" + "─" * 58 + "┘")

        return "\n".join(lines)

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
