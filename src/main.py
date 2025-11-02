"""
Main Control Loop - ESP32 Xbox Controller to LEGO Hub Bridge

Integrates all components to create a complete RC car control system:
- Scans for Xbox controller and LEGO Technic Hub
- Establishes dual BLE connections
- Translates Xbox inputs to LEGO motor/LED commands
- Maintains connection health and handles errors

Usage from REPL:
>>> import src.main as main
>>> main.run()

Or deploy and run automatically on boot.
"""

import time
import asyncio
from src.ble_manager import BLEManager
from src.input_translator import InputTranslator, ControlMode
from src.utils.bonding_utils import clear_bonding_data
from src.utils.constants import LEGO_COLORS


class RCCarController:
    """
    Main RC car controller integrating BLE and input translation.
    """

    def __init__(self, dead_zone: float = 0.03):
        """
        Initialize RC car controller.

        Args:
            dead_zone: Dead zone for analog stick inputs (0.0 to 1.0)
        """
        self.ble_manager = BLEManager(dead_zone=dead_zone)
        self.translator = InputTranslator()
        self.running = False
        self.connection_check_interval_ms = 5000  # Check connections every 5 seconds
        self.last_connection_check = 0

    async def startup(self):
        """
        Perform startup sequence: clear bonding data, scan, and connect.

        Returns:
            True if startup successful, False otherwise
        """
        print("\n" + "="*60)
        print(" " * 15 + "ESP32 RC CAR CONTROLLER")
        print("="*60)
        print()

        # Clear old bonding data to ensure reliable connections
        print("[1/3] Clearing old bonding data...")
        clear_bonding_data()
        print()

        # Scan for devices
        print("[2/3] Scanning for devices...")
        devices = await self.ble_manager.scan_devices(timeout_ms=10000)

        if devices.get('xbox') is None:
            print("✗ Xbox controller not found!")
            return False

        if devices.get('lego') is None:
            print("✗ LEGO hub not found!")
            return False

        print("✓ Found both devices")
        print()

        # Connect to both devices
        print("[3/3] Connecting to devices...")
        connections = await self.ble_manager.connect_all(
            xbox_device=devices['xbox'],
            lego_device=devices['lego']
        )

        if not connections.get('xbox_connected'):
            print("✗ Failed to connect to Xbox controller")
            return False

        if not connections.get('lego_connected'):
            print("✗ Failed to connect to LEGO hub")
            return False

        print("✓ Connected to both devices")
        print()

        print("="*60)
        print("🚗 RC CAR READY!")
        print("="*60)
        print()
        self._print_controls()

        return True

    def _print_controls(self):
        """Print control scheme."""
        print("CONTROLS:")
        print("  Left Stick Y    : Forward/Backward")
        print("  Right Stick X   : Left/Right Steering")
        print("  Left Trigger    : Brake")
        print("  Right Trigger   : Boost")
        print("  A Button        : Toggle Headlights")
        print("  B Button        : Toggle Taillights")
        print("  X Button        : Emergency Stop")
        print("  LB Button       : Cycle Control Mode")
        print("  D-pad Up/Down   : Adjust Speed Limit")
        print()
        print("Current mode: NORMAL")
        print("Speed limit: 100%")
        print()

    async def check_connections(self):
        """
        Periodically check connection health.

        Returns:
            True if both connections healthy, False otherwise
        """
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, self.last_connection_check) >= self.connection_check_interval_ms:
            self.last_connection_check = current_time

            health = await self.ble_manager.check_connections()

            if not health.get('xbox_ok'):
                print("⚠ Xbox controller connection lost!")
                return False

            if not health.get('lego_ok'):
                print("⚠ LEGO hub connection lost!")
                return False

        return True

    async def control_loop(self):
        """
        Main control loop: read Xbox input -> translate -> send to LEGO.

        Runs until connection lost or error occurs.
        """
        print("Starting control loop...")
        print("Press Ctrl+C to stop")
        print("-" * 60)
        print()

        self.running = True
        xbox_client = self.ble_manager.get_xbox_client()
        lego_client = self.ble_manager.get_lego_client()

        # Track previous command to avoid spamming identical commands
        prev_motor_a = None
        prev_motor_b = None
        prev_led = None

        loop_count = 0

        try:
            while self.running:
                # Check connections periodically
                if not await self.check_connections():
                    print("Connection check failed - stopping")
                    break

                # Read Xbox controller input (with timeout)
                try:
                    report = await asyncio.wait_for_ms(
                        xbox_client.report_characteristic.notified(),
                        500  # 500ms timeout
                    )

                    if report:
                        # Parse controller input
                        xbox_client.parse_hid_report(report)

                        # Translate to vehicle command
                        cmd = self.translator.translate(xbox_client.state)

                        # Handle emergency stop
                        if cmd.emergency_stop:
                            print("\n🛑 EMERGENCY STOP ACTIVATED")
                            await lego_client.drive(0, 0, lego_client.LIGHTS_ON_ON)
                            prev_motor_a = 0
                            prev_motor_b = 0
                            prev_led = LEGO_COLORS.RED
                            print("Motors stopped. Press X again to resume.\n")
                            continue

                        # Send motor commands (only if changed)
                        if cmd.motor_a_speed != prev_motor_a or cmd.motor_b_speed != prev_motor_b or cmd.led_color != prev_led:
                            await lego_client.drive(speed=cmd.motor_a_speed, angle=cmd.motor_b_speed, lights=cmd.led_color)
                            prev_motor_a = cmd.motor_a_speed
                            prev_motor_b = cmd.motor_b_speed
                            prev_led = cmd.led_color

                        # Periodic status display (every 50 loops = ~5 seconds at 10Hz)
                        loop_count += 1
                        if loop_count % 50 == 0:
                            status = self.translator.get_status()
                            print(f"Status: Mode={status['mode']}, "
                                  f"Limit={status['max_speed_limit']}%, "
                                  f"Lights={'H' if status['headlights'] else '-'}"
                                  f"{'T' if status['taillights'] else '-'}")

                except asyncio.TimeoutError:
                    # No input received (controller idle) - this is normal
                    pass

        except KeyboardInterrupt:
            print("\n\nStopping (Ctrl+C pressed)...")
        except Exception as e:
            print(f"\n✗ Error in control loop: {e}")
        finally:
            self.running = False
            await self.shutdown()

    async def shutdown(self):
        """Clean shutdown: stop motors and disconnect."""
        print("\nShutting down...")

        try:
            lego_client = self.ble_manager.get_lego_client()

            # Stop all motors and turn off LEDs
            print("Stopping motors and turning off LEDs...")
            await lego_client.drive(0, 0, lego_client.LIGHTS_OFF_OFF)

        except Exception as e:
            print(f"Error during motor/LED shutdown: {e}")

        # Disconnect from devices
        print("Disconnecting...")
        await self.ble_manager.disconnect_all()

        print("Shutdown complete")
        print()

    async def run(self):
        """
        Run complete RC car control system.

        Performs startup, runs control loop, and handles shutdown.
        """
        # Startup
        if not await self.startup():
            print("\n✗ Startup failed!")
            print("Please check that:")
            print("  1. Xbox controller is powered on and in pairing mode")
            print("  2. LEGO Technic Hub is powered on")
            print("  3. Devices are in range")
            return

        # Run control loop
        await self.control_loop()


# Global controller instance
_controller = None


async def start(dead_zone: float = 0.03):
    """
    Start the RC car controller.

    Args:
        dead_zone: Dead zone for analog stick inputs

    Usage:
        >>> import asyncio
        >>> import src.main as main
        >>> asyncio.run(main.start())
    """
    global _controller
    _controller = RCCarController(dead_zone=dead_zone)
    await _controller.run()


def run(dead_zone: float = 0.03):
    """
    Convenience function to run the controller (handles asyncio setup).

    Args:
        dead_zone: Dead zone for analog stick inputs

    Usage from REPL:
        >>> import src.main as main
        >>> main.run()
    """
    asyncio.run(start(dead_zone=dead_zone))


async def quick_test():
    """
    Quick test function for development.

    Starts the controller and runs for 30 seconds, then stops.
    """
    global _controller
    _controller = RCCarController()

    if not await _controller.startup():
        print("Startup failed")
        return

    print("Running for 30 seconds...")

    # Run control loop with timeout
    try:
        await asyncio.wait_for_ms(_controller.control_loop(), 30000)
    except asyncio.TimeoutError:
        print("\nTime's up!")

    await _controller.shutdown()


# Allow running as module
if __name__ == "__main__":
    run()
