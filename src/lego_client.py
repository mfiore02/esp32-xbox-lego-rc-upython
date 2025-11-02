"""
LEGO Technic Move Hub BLE Client for MicroPython
Ported from reference implementation by Daniele Benedettelli (@profbricks)
"""

import asyncio
import aioble
import bluetooth
from utils.constants import (
    LEGO_SERVICE_UUID,
    LEGO_CHARACTERISTIC_UUID,
    MOTOR_PORT_ALL,
    LIGHTS_OFF,
    LIGHTS_ON,
    LIGHTS_BOTH_ON,
)
from utils.ble_utils import format_mac_address, bytes_to_hex

# Lego hub device name
LEGO_DEVICE_NAME = "Technic Move"


class LegoClient:
    """
    BLE client for LEGO Technic Move Hub (from set 42176).

    Handles connection, motor control, LED control, and calibration.
    """

    # Motor control constants (from reference implementation)
    SC_BUFFER_NO_FEEDBACK = 0x00
    MOTOR_MODE_POWER = 0x00
    END_STATE_BRAKE = 0x7F
    END_STATE_FLOAT = 0x00

    # LED control constants
    ID_LED = 0x32  # LED port ID
    IO_TYPE_RGB_LED = 0x00
    LED_MODE_COLOR = 0x00
    LED_MODE_RGB = 0x01

    # Light states (bit patterns from reference)
    LIGHTS_OFF_OFF = 0b100
    LIGHTS_OFF_ON = 0b101
    LIGHTS_ON_ON = 0b000

    def __init__(self):
        """Initialize the LEGO client."""
        self.device = None
        self.connection = None
        self.service = None
        self.characteristic = None
        self.connected = False

        # Convert UUID strings to bluetooth.UUID objects
        self.service_uuid = bluetooth.UUID(LEGO_SERVICE_UUID)
        self.char_uuid = bluetooth.UUID(LEGO_CHARACTERISTIC_UUID)

    async def connect(self, device):
        """
        Connect to a LEGO Technic Move Hub device.

        Args:
            device: BLE device object from scan

        Returns:
            True if connection successful, False otherwise
        """
        try:
            print(f"Connecting to LEGO hub: {format_mac_address(device)}...")
            self.device = device

            # Connect to the device with timeout
            self.connection = await device.connect(timeout_ms=10000)
            print("Connected! Discovering services...")

            # Discover the LEGO hub service
            try:
                self.service = await self.connection.service(self.service_uuid)
                print(f"Found LEGO service: {self.service_uuid}")
            except Exception as e:
                print(f"Service discovery failed: {e}")
                await self.disconnect()
                return False

            # Get the characteristic for sending commands
            try:
                self.characteristic = await self.service.characteristic(self.char_uuid)
                print(f"Found characteristic: {self.char_uuid}")
            except Exception as e:
                print(f"Characteristic discovery failed: {e}")
                await self.disconnect()
                return False

            # Pair with the device (CRUCIAL for LEGO hub!)
            # This is equivalent to Bleak's pair(protection_level=2)
            # The hub requires an authenticated encrypted link
            try:
                print("Pairing with LEGO hub...")
                await self.connection.pair(bond=True)
                print("Paired successfully!")
            except Exception as e:
                print(f"Pairing failed: {e}")
                print("Warning: Commands may not work without pairing")
                # Don't fail here - some devices work without explicit pairing
                # But LEGO hub won't accept commands without it

            self.connected = True
            print("LEGO hub connected successfully!")

            print("Calibrating steering...")
            if not await self.calibrate_steering():
                print("LEGO hub calibration failed! Cannot continue.")
                await self.disconnect()
                return False
            return True

        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from the LEGO hub."""
        if self.connection:
            try:
                await self.connection.disconnect()
                print("Disconnected from LEGO hub")
            except Exception as e:
                print(f"Disconnect error: {e}")

        self.connection = None
        self.service = None
        self.characteristic = None
        self.connected = False

    def is_connected(self) -> bool:
        """Check if currently connected to the hub."""
        return self.connected and self.connection is not None

    async def send_command(self, data: bytes):
        """
        Send a command to the LEGO hub.

        Args:
            data: Command bytes to send

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            print("Not connected to LEGO hub")
            return False

        if self.characteristic is None:
            print("Characteristic not available")
            return False

        try:
            # Write command to characteristic
            await self.characteristic.write(data, response=False)
            # Uncomment for debugging:
            # print(f"Sent: {bytes_to_hex(data)}")
            return True

        except Exception as e:
            print(f"Failed to send command: {e}")
            return False

    async def motor_start_power(self, motor: int, power: int):
        """
        Start a motor with specified power.

        Args:
            motor: Motor port ID (use MOTOR_PORT_* constants)
            power: Power level (-100 to 100, negative = reverse)

        Returns:
            True if command sent successfully
        """
        # Clamp power to valid range
        power = max(-100, min(100, power))

        # Build command: [0x08, 0x00, 0x81, motor, 0x00, 0x51, 0x00, power]
        command = bytearray([
            0x08,  # Length
            0x00,  # Hub ID
            0x81,  # Command type
            motor & 0xFF,  # Motor port
            self.SC_BUFFER_NO_FEEDBACK,
            0x51,  # Execute immediately
            self.MOTOR_MODE_POWER,
            power & 0xFF  # Power (as signed byte)
        ])

        return await self.send_command(command)

    async def motor_stop(self, motor: int, brake: bool = True):
        """
        Stop a motor.

        Args:
            motor: Motor port ID (use MOTOR_PORT_* constants)
            brake: If True, brake motor; if False, let it coast

        Returns:
            True if command sent successfully
        """
        # Build command: [0x08, 0x00, 0x81, motor, 0x00, 0x51, 0x00, brake_state]
        command = bytearray([
            0x08,
            0x00,
            0x81,
            motor & 0xFF,
            self.SC_BUFFER_NO_FEEDBACK,
            0x51,
            self.MOTOR_MODE_POWER,
            self.END_STATE_BRAKE if brake else self.END_STATE_FLOAT
        ])

        return await self.send_command(command)

    async def drive(self, speed: int = 0, angle: int = 0, lights: int = LIGHTS_OFF):
        """
        Send drive command to control speed, steering, and lights.

        This is the main control command for the LEGO vehicle.

        Args:
            speed: Throttle speed (-100 to 100, negative = reverse)
            angle: Steering angle (-100 to 100, negative = left, positive = right)
            lights: Light state (use LIGHTS_* constants or class light constants)

        Returns:
            True if command sent successfully
        """
        # Clamp values to valid ranges
        speed = max(-100, min(100, speed))
        angle = max(-100, min(100, angle))

        # Build drive command (from reference implementation)
        # Format: [0x0d, 0x00, 0x81, 0x36, 0x11, 0x51, 0x00, 0x03, 0x00, speed, angle, lights, 0x00]
        command = bytearray([
            0x0d,  # Length (13 bytes)
            0x00,  # Hub ID
            0x81,  # Command type
            0x36,  # Motor port (all/combined)
            0x11,  # Sub-command
            0x51,  # Execute immediately
            0x00,  # Start condition
            0x03,  # Completion information
            0x00,  # Reserved
            speed & 0xFF,   # Speed (signed byte)
            angle & 0xFF,   # Steering angle (signed byte)
            lights & 0xFF,  # Light state
            0x00   # Reserved
        ])

        return await self.send_command(command)

    async def calibrate_steering(self):
        """
        Calibrate the steering mechanism.

        Sends calibration sequence to center the steering.
        Should be called once after connection.

        Returns:
            True if calibration commands sent successfully
        """
        print("Calibrating steering...")

        # First calibration command
        cmd1 = bytes.fromhex("0d008136115100030000001000")
        success1 = await self.send_command(cmd1)

        # Small delay between commands
        await asyncio.sleep_ms(100)

        # Second calibration command
        cmd2 = bytes.fromhex("0d008136115100030000000800")
        success2 = await self.send_command(cmd2)

        if success1 and success2:
            print("Steering calibration complete")
            return True
        else:
            print("Steering calibration failed")
            return False

    async def change_led_color(self, color_id: int):
        """
        Change the hub LED color.

        Args:
            color_id: Color ID (0-10, standard LEGO color palette)
                     0=black/off, 1=pink, 2=purple, 3=blue, 4=light blue,
                     5=cyan, 6=green, 7=yellow, 8=orange, 9=red, 10=white

        Returns:
            True if command sent successfully
        """
        command = bytearray([
            0x08,
            0x00,
            0x81,
            self.ID_LED,
            self.IO_TYPE_RGB_LED,
            0x51,
            self.LED_MODE_COLOR,
            color_id & 0xFF
        ])

        return await self.send_command(command)

    async def set_led_rgb(self, r: int, g: int, b: int):
        """
        Set the hub LED to a custom RGB color.

        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)

        Returns:
            True if command sent successfully
        """
        # Clamp RGB values
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))

        command = bytearray([
            0x0A,  # Length (10 bytes)
            0x00,
            0x81,
            self.ID_LED,
            self.IO_TYPE_RGB_LED,
            0x51,
            self.LED_MODE_RGB,
            r & 0xFF,
            g & 0xFF,
            b & 0xFF
        ])

        return await self.send_command(command)

    async def set_led_color(self, color_id: int):
        """
        Alias for change_led_color() for consistency with main.py API.

        Args:
            color_id: Color ID (0-10, use LEGO_COLORS constants)

        Returns:
            True if command sent successfully
        """
        return await self.change_led_color(color_id)

    def get_connection_info(self) -> dict:
        """
        Get information about the current connection.

        Returns:
            Dictionary with connection details
        """
        return {
            "connected": self.connected,
            "device": format_mac_address(self.device) if self.device else None,
            "service_uuid": str(self.service_uuid),
            "char_uuid": str(self.char_uuid),
        }
