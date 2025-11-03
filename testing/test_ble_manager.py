"""
Test script for BLE Manager - Dual Simultaneous Connections

Tests the BLE manager's ability to maintain simultaneous connections
to both Xbox controller and LEGO hub.

Usage:
1. Turn on Xbox controller (hold Xbox button + pairing button until rapid flashing)
2. Turn on LEGO Technic Move Hub (should blink)
3. Run: import test_ble_manager; test_ble_manager.run()
"""

import asyncio
import sys
import time
from utils.constants import LIGHTS_OFF, LIGHTS_ON, LIGHTS_BRAKE

# Add src to path for imports
sys.path.append('/src')

from ble_manager import BLEManager


async def test_scan_both_devices():
    """Test 1: Scan for both devices."""
    print("\n" + "=" * 60)
    print("Test 1: Scanning for both devices")
    print("=" * 60)

    manager = BLEManager()

    results = await manager.scan_devices(timeout_ms=10000)

    print(f"\nScan results:")
    print(f"  Xbox found: {results['xbox_found']}")
    print(f"  LEGO found: {results['lego_found']}")

    if results['xbox_found'] and results['lego_found']:
        print("✓ Both devices found!")
        return manager
    else:
        if not results['xbox_found']:
            print("✗ Xbox controller not found")
            print("  Troubleshooting:")
            print("  - Make sure controller is in pairing mode (rapid flashing)")
            print("  - Hold Xbox button + pairing button")
        if not results['lego_found']:
            print("✗ LEGO hub not found")
            print("  Troubleshooting:")
            print("  - Make sure hub is powered on and blinking")
        return None


async def test_connect_both_devices(manager):
    """Test 2: Connect to both devices simultaneously."""
    print("\n" + "=" * 60)
    print("Test 2: Connecting to both devices")
    print("=" * 60)

    results = await manager.connect_all()

    print(f"\nConnection results:")
    print(f"  Xbox connected: {results['xbox_connected']}")
    print(f"  LEGO connected: {results['lego_connected']}")
    print(f"  Both connected: {results['both_connected']}")

    if results['errors']:
        print(f"  Errors: {results['errors']}")

    if results['both_connected']:
        print("✓ Both devices connected successfully!")
        return True
    else:
        print("✗ Failed to connect to both devices")
        return False


async def test_connection_status(manager):
    """Test 3: Check connection status."""
    print("\n" + "=" * 60)
    print("Test 3: Connection status check")
    print("=" * 60)

    status = manager.get_status()

    print(f"\nStatus:")
    print(f"  Xbox state: {status['xbox_state']}")
    print(f"  LEGO state: {status['lego_state']}")
    print(f"  Ready: {status['ready']}")

    if status['ready']:
        print("✓ System ready for operation")
        return True
    else:
        print("✗ System not ready")
        return False


async def test_xbox_input_while_connected(manager):
    """Test 4: Read Xbox input while maintaining both connections."""
    print("\n" + "=" * 60)
    print("Test 4: Xbox input with dual connections active")
    print("=" * 60)
    print("Press buttons and move sticks on Xbox controller...")
    print("Monitoring for 5 seconds...")
    print()

    xbox_client = manager.get_xbox_client()
    input_count = [0]

    def input_callback(state):
        input_count[0] += 1
        if input_count[0] <= 3:  # Show first 3 inputs
            print(f"Input {input_count[0]}: LS({state.left_stick_x:+.2f},{state.left_stick_y:+.2f}) "
                  f"RS({state.right_stick_x:+.2f},{state.right_stick_y:+.2f}) "
                  f"LT:{state.left_trigger:.2f} RT:{state.right_trigger:.2f}")

    xbox_client.input_callback = input_callback

    # Subscribe to notifications
    await xbox_client.report_characteristic.subscribe(notify=True)

    # Read inputs for 5 seconds
    try:
        start_time = time.ticks_ms()
        duration_ms = 5000

        while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
            try:
                report = await asyncio.wait_for(
                    xbox_client.report_characteristic.notified(),
                    timeout=0.5
                )
                if report:
                    xbox_client.parse_hid_report(report)
            except asyncio.TimeoutError:
                print(".", end="")

        print(f"\n✓ Received {input_count[0]} input reports")
        return input_count[0] > 0

    except Exception as e:
        print(f"\n✗ Error reading input: {e}")
        return False


async def test_lego_commands_while_connected(manager):
    """Test 5: Send LEGO commands while maintaining both connections."""
    print("\n" + "=" * 60)
    print("Test 5: LEGO commands with dual connections active")
    print("=" * 60)
    print("Sending test commands to LEGO hub...")

    lego_client = manager.get_lego_client()

    try:
        # Test drive command
        print("  Testing drive command (slow forward)...")
        await lego_client.drive(speed=20, angle=0, lights=LIGHTS_OFF)
        await asyncio.sleep(1)

        print("  Stopping...")
        await lego_client.drive(speed=0, angle=0, lights=LIGHTS_OFF)

        print("✓ LEGO commands executed successfully")
        return True

    except Exception as e:
        print(f"✗ Error sending LEGO commands: {e}")
        return False


async def test_connection_health(manager):
    """Test 6: Check connection health."""
    print("\n" + "=" * 60)
    print("Test 6: Connection health check")
    print("=" * 60)

    health = await manager.check_connections()

    print(f"\nConnection health:")
    print(f"  Xbox OK: {health['xbox_ok']}")
    print(f"  LEGO OK: {health['lego_ok']}")
    print(f"  All OK: {health['all_ok']}")

    if health['all_ok']:
        print("✓ All connections healthy")
        return True
    else:
        print("✗ Some connections unhealthy")
        return False


async def test_simultaneous_operations(manager):
    """Test 7: Simultaneous Xbox input reading and LEGO control."""
    print("\n" + "=" * 60)
    print("Test 7: Simultaneous operations")
    print("=" * 60)
    print("Reading Xbox input AND controlling LEGO simultaneously...")
    print("Move sticks while watching the LED change colors...")
    print()

    xbox_client = manager.get_xbox_client()
    lego_client = manager.get_lego_client()

    input_count = [0]
    command_count = [0]

    def input_callback(state):
        input_count[0] += 1

    xbox_client.input_callback = input_callback

    # Subscribe to Xbox notifications (if not already)
    try:
        await xbox_client.report_characteristic.subscribe(notify=True)
    except:
        pass  # Already subscribed

    # LED colors to cycle through
    colors = [9, 6, 3, 5]  # Red, Green, Blue, Yellow
    color_index = [0]

    try:
        # Run for 8 seconds
        start_time = time.ticks_ms()
        duration_ms = 8000
        last_cmd_time = start_time
        steer = 100  # Initial steering angle
        cmd_interval = 2000  # Send command every 2 seconds

        while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
            # Read Xbox input with short timeout
            try:
                report = await asyncio.wait_for(
                    xbox_client.report_characteristic.notified(),
                    timeout=0.5
                )
                if report:
                    xbox_client.parse_hid_report(report)
            except asyncio.TimeoutError:
                pass

            # Turn wheels 2 seconds based on elapsed time
            current_time = time.ticks_ms()
            if time.ticks_diff(current_time, last_cmd_time) >= cmd_interval:
                await lego_client.drive(0, steer, lights=LIGHTS_OFF)  # Turn wheels
                steer = -steer  # Alternate direction
                command_count[0] += 1
                last_cmd_time = current_time
                print(f"  Turned to angle {steer}")

        print(f"\n✓ Processed {input_count[0]} Xbox inputs and {command_count[0]} LEGO commands simultaneously")
        print(f"  Duration: 8 seconds (actual time-based)")
        return True

    except Exception as e:
        print(f"\n✗ Error during simultaneous operations: {e}")
        return False


async def run_all_tests():
    """Run all BLE manager tests."""
    print("=" * 60)
    print("BLE Manager Test Suite - Dual Connections")
    print("=" * 60)

    manager = None

    try:
        # Test 1: Scan
        manager = await test_scan_both_devices()
        if not manager:
            print("\n✗ Cannot continue - devices not found")
            return

        await asyncio.sleep(1)

        # Test 2: Connect
        connected = await test_connect_both_devices(manager)
        if not connected:
            print("\n✗ Cannot continue - connection failed")
            await manager.disconnect_all()
            return

        await asyncio.sleep(1)

        # Test 3: Status
        await test_connection_status(manager)
        await asyncio.sleep(1)

        # Test 4: Xbox input
        await test_xbox_input_while_connected(manager)
        await asyncio.sleep(1)

        # Test 5: LEGO commands
        await test_lego_commands_while_connected(manager)
        await asyncio.sleep(1)

        # Test 6: Health check
        await test_connection_health(manager)
        await asyncio.sleep(1)

        # Test 7: Simultaneous operations
        await test_simultaneous_operations(manager)

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import sys
        sys.print_exception(e)

    finally:
        # Always disconnect
        if manager:
            await manager.disconnect_all()


# Convenience functions for REPL use
def run():
    """Run all tests (convenience function for REPL)."""
    asyncio.run(run_all_tests())


def quick_test():
    """Quick test - scan, connect, verify both work."""
    async def quick():
        manager = BLEManager()

        print("Quick BLE Manager Test")
        print("=" * 40)

        # Scan and connect
        results = await manager.scan_and_connect_all(scan_timeout_ms=10000)

        if results["both_connected"]:
            print("\n✓ Both devices connected!")

            # Quick verification
            print("\nQuick verification...")

            # Test Xbox input for 3 seconds
            print("  Xbox: Move sticks...")
            xbox = manager.get_xbox_client()
            await xbox.report_characteristic.subscribe(notify=True)

            for _ in range(3):
                try:
                    report = await asyncio.wait_for(
                        xbox.report_characteristic.notified(),
                        timeout=1.0
                    )
                    if report:
                        print("  ✓ Xbox input received")
                        break
                except asyncio.TimeoutError:
                    pass

            # Test LEGO command
            print("  LEGO: Turning wheels...")
            lego = manager.get_lego_client()
            await lego.drive(speed=0, angle=100, lights=LIGHTS_OFF)
            await asyncio.sleep(1)
            await lego.drive(speed=0, angle=0, lights=LIGHTS_OFF)
            print("  ✓ LEGO commands sent")

            await asyncio.sleep(1)

            print("\n✓ Quick test passed!")
            await manager.disconnect_all()
            return manager

        else:
            print("\n✗ Quick test failed - could not connect to both devices")
            await manager.disconnect_all()
            return None

    return asyncio.run(quick())


if __name__ == "__main__":
    # Run tests if executed directly
    run()
