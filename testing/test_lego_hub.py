"""
Test script for LEGO Technic Move Hub BLE connection and control.

This script tests:
1. Scanning for the LEGO hub
2. Connecting to the hub
3. Basic motor control commands
4. LED control
5. Drive command with speed/steering

Usage:
1. Upload the src/ directory to your ESP32
2. Upload this test script
3. Run: import test_lego_hub; test_lego_hub.run()
"""

import asyncio
import sys
import time

# Add src to path for imports
sys.path.append('/src')

from lego_client import LegoClient
from utils.ble_utils import scan_for_device
from utils.constants import LEGO_NAME_PATTERN


async def test_scan():
    """Test scanning for LEGO hub."""
    print("\n=== Test 1: Scanning for LEGO hub ===")
    device = await scan_for_device(LEGO_NAME_PATTERN, timeout_ms=10000)

    if device:
        print(f"✓ Found LEGO hub!")
        return device
    else:
        print("✗ LEGO hub not found")
        return None


async def test_connection(device):
    """Test connecting to the LEGO hub."""
    print("\n=== Test 2: Connecting to LEGO hub ===")

    client = LegoClient()
    success = await client.connect(device)

    if success:
        print("✓ Connected successfully!")
        return client
    else:
        print("✗ Connection failed")
        return None


async def test_calibration(client):
    """Test steering calibration."""
    print("\n=== Test 3: Steering calibration ===")

    success = await client.calibrate_steering()

    if success:
        print("✓ Calibration successful!")
    else:
        print("✗ Calibration failed")

    await asyncio.sleep(1)


async def test_led_colors(client):
    """Test LED color changes."""
    print("\n=== Test 4: LED color test ===")

    colors = [
        (0, "Off"),
        (9, "Red"),
        (6, "Green"),
        (3, "Blue"),
        (10, "White"),
    ]

    for color_id, color_name in colors:
        print(f"Setting LED to {color_name}...")
        await client.change_led_color(color_id)
        await asyncio.sleep(0.5)

    print("✓ LED test complete")


async def test_led_rgb(client):
    """Test custom RGB LED colors."""
    print("\n=== Test 5: RGB LED test ===")

    rgb_colors = [
        (255, 0, 0, "Red"),
        (0, 255, 0, "Green"),
        (0, 0, 255, "Blue"),
        (255, 255, 0, "Yellow"),
        (255, 0, 255, "Magenta"),
        (0, 255, 255, "Cyan"),
        (255, 255, 255, "White"),
    ]

    for r, g, b, name in rgb_colors:
        print(f"Setting LED to {name} ({r},{g},{b})...")
        await client.set_led_rgb(r, g, b)
        await asyncio.sleep(0.5)

    # Turn off
    await client.set_led_rgb(0, 0, 0)
    print("✓ RGB LED test complete")


async def test_motor_control(client):
    """Test individual motor control."""
    print("\n=== Test 6: Motor control test ===")

    # Test motor start/stop
    print("Starting motor at 50% power...")
    await client.motor_start_power(0x36, 50)
    await asyncio.sleep(1)

    print("Stopping motor with brake...")
    await client.motor_stop(0x36, brake=True)
    await asyncio.sleep(0.5)

    print("✓ Motor control test complete")


async def test_drive_commands(client):
    """Test drive commands with speed and steering."""
    print("\n=== Test 7: Drive command test ===")

    test_sequences = [
        (30, 0, "Forward slow"),
        (0, 0, "Stop"),
        (-30, 0, "Reverse slow"),
        (0, 0, "Stop"),
        (0, 50, "Steer right (no throttle)"),
        (0, -50, "Steer left (no throttle)"),
        (0, 0, "Center steering"),
        (50, 30, "Forward + right turn"),
        (0, 0, "Stop"),
    ]

    for speed, angle, description in test_sequences:
        print(f"{description}: speed={speed}, angle={angle}")
        await client.drive(speed=speed, angle=angle, lights=client.LIGHTS_OFF_OFF)
        await asyncio.sleep(1.5)

    print("✓ Drive command test complete")


async def test_lights(client):
    """Test light control during driving."""
    print("\n=== Test 8: Lights test ===")

    light_states = [
        (client.LIGHTS_OFF_OFF, "Lights OFF/OFF"),
        (client.LIGHTS_OFF_ON, "Lights OFF/ON"),
        (client.LIGHTS_ON_ON, "Lights ON/ON"),
        (client.LIGHTS_OFF_OFF, "Lights OFF/OFF"),
    ]

    for lights, description in light_states:
        print(f"{description}")
        await client.drive(speed=0, angle=0, lights=lights)
        await asyncio.sleep(1)

    print("✓ Lights test complete")


async def interactive_mode(client):
    """
    Interactive mode for manual testing.

    Note: This requires user input, which may not work well in MicroPython REPL.
    For actual testing, use the automated tests above.
    """
    print("\n=== Interactive Mode ===")
    print("This mode is for demonstration only.")
    print("In a real implementation, you would read user input here.")
    print("For now, we'll just do a simple drive demo...")

    # Simple demo: drive in a pattern
    print("Driving in a square pattern...")

    for _ in range(4):
        # Drive forward
        print("Forward...")
        await client.drive(speed=40, angle=0, lights=client.LIGHTS_ON_ON)
        await asyncio.sleep(2)

        # Stop
        await client.drive(speed=0, angle=0, lights=client.LIGHTS_ON_ON)
        await asyncio.sleep(0.5)

        # Turn 90 degrees (approximate)
        print("Turning...")
        await client.drive(speed=0, angle=80, lights=client.LIGHTS_OFF_ON)
        await asyncio.sleep(1)

        # Stop
        await client.drive(speed=0, angle=0, lights=client.LIGHTS_ON_ON)
        await asyncio.sleep(0.5)

    # Final stop
    await client.drive(speed=0, angle=0, lights=client.LIGHTS_OFF_OFF)
    print("Pattern complete!")


async def run_all_tests():
    """Run all LEGO hub tests."""
    print("=" * 60)
    print("LEGO Technic Move Hub Test Suite")
    print("=" * 60)

    client = None

    try:
        # Test 1: Scan
        device = await test_scan()
        if not device:
            print("\n✗ Cannot continue without device")
            return

        # Test 2: Connect
        client = await test_connection(device)
        if not client:
            print("\n✗ Cannot continue without connection")
            return

        # Test 3: Calibration
        await test_calibration(client)

        # Test 4-5: LEDs
        await test_led_colors(client)
        await test_led_rgb(client)

        # Test 6: Motor control
        await test_motor_control(client)

        # Test 7: Drive commands
        await test_drive_commands(client)

        # Test 8: Lights
        await test_lights(client)

        # Interactive demo
        await interactive_mode(client)

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")

    finally:
        # Always disconnect
        if client and client.is_connected():
            print("\nDisconnecting...")
            await client.disconnect()


# Convenience functions for REPL use
def run():
    """Run all tests (convenience function for REPL)."""
    asyncio.run(run_all_tests())


def quick_test():
    """Quick test - just scan, connect, and calibrate."""
    async def quick():
        device = await scan_for_device(LEGO_NAME_PATTERN, timeout_ms=10000)
        if device:
            client = LegoClient()
            if await client.connect(device):
                await client.calibrate_steering()
                print("Quick test complete - hub ready!")
                return client
        print("Quick test failed")
        return None

    return asyncio.run(quick())


if __name__ == "__main__":
    # Run tests if executed directly
    run()
