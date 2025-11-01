"""
Test script for Xbox Wireless Controller BLE connection and input reading.

This script tests:
1. Scanning for the Xbox controller
2. Connecting to the controller
3. Reading controller inputs (buttons, sticks, triggers)
4. Displaying input state in real-time

Usage:
1. Upload the src/ directory to your ESP32
2. Upload this test script
3. Turn on your Xbox controller (hold Xbox button until it flashes)
4. Run: import test_xbox_controller; test_xbox_controller.run()
"""

import asyncio
import sys

# Add src to path for imports
sys.path.append('/src')

from xbox_client import XboxClient, XBOX_DEVICE_NAME
from utils.ble_utils import scan_for_device


async def test_scan():
    """Test scanning for Xbox controller."""
    print("\n=== Test 1: Scanning for Xbox controller ===")
    print(f"Looking for device: '{XBOX_DEVICE_NAME}'")
    print("Make sure your controller is in pairing mode (hold Xbox button)")

    device = await scan_for_device("Xbox", timeout_ms=10000)

    if device:
        print(f"✓ Found Xbox controller!")
        return device
    else:
        print("✗ Xbox controller not found")
        print("Troubleshooting:")
        print("  - Make sure controller is powered on")
        print("  - Hold Xbox button until it starts flashing rapidly")
        print("  - Controller should be in pairing mode (not connected to anything)")
        return None


async def test_connection(device):
    """Test connecting to the Xbox controller."""
    print("\n=== Test 2: Connecting to Xbox controller ===")

    client = XboxClient(dead_zone=0.05)  # 5% dead zone
    success = await client.connect(device)

    if success:
        print("✓ Connected successfully!")
        return client
    else:
        print("✗ Connection failed")
        return None


async def test_read_single_report(client):
    """Test reading a single input report."""
    print("\n=== Test 3: Single input report read ===")
    print("Press any button on the controller...")

    try:
        # Try to read a single report with timeout
        report = await asyncio.wait_for(
            client.report_characteristic.notified(),
            timeout=5.0
        )

        if report:
            print(f"✓ Received report: {len(report)} bytes")
            print(f"Raw data: {' '.join(f'{b:02X}' for b in report)}")
            client.parse_hid_report(report)
            print(f"Parsed state: {client.state}")
        else:
            print("✗ No report received")

    except asyncio.TimeoutError:
        print("✗ Timeout waiting for input")
    except Exception as e:
        print(f"✗ Error: {e}")


async def test_button_mapping(client):
    """Test button mapping - ask user to press each button."""
    print("\n=== Test 4: Button mapping verification ===")
    print("This test will ask you to press each button to verify mapping.")
    print("Press each button when prompted (5 second timeout per button).")
    print()

    buttons_to_test = [
        ("button_a", "A button (bottom)"),
        ("button_b", "B button (right)"),
        ("button_x", "X button (left)"),
        ("button_y", "Y button (top)"),
        ("button_lb", "Left bumper"),
        ("button_rb", "Right bumper"),
        ("button_view", "View button (left of Xbox button)"),
        ("button_menu", "Menu button (right of Xbox button)"),
        ("button_ls", "Left stick click"),
        ("button_rs", "Right stick click"),
    ]

    # Input callback to monitor button presses
    button_pressed = asyncio.Event()
    current_button = [None]

    def input_callback(state):
        for attr_name, _ in buttons_to_test:
            if hasattr(state, attr_name) and getattr(state, attr_name):
                if attr_name == current_button[0]:
                    button_pressed.set()

    client.input_callback = input_callback

    # Start input loop as background task
    input_task = asyncio.create_task(client.start_input_loop())

    try:
        for button_attr, button_desc in buttons_to_test:
            print(f"Press {button_desc}...", end="")
            current_button[0] = button_attr
            button_pressed.clear()

            try:
                await asyncio.wait_for(button_pressed.wait(), timeout=5.0)
                print(" ✓")
            except asyncio.TimeoutError:
                print(" ✗ (timeout)")

            await asyncio.sleep(0.5)  # Debounce

        print("\n✓ Button mapping test complete")

    finally:
        # Cancel input task
        input_task.cancel()
        try:
            await input_task
        except asyncio.CancelledError:
            pass


async def test_analog_inputs(client):
    """Test analog inputs (sticks and triggers)."""
    print("\n=== Test 5: Analog inputs test ===")
    print("Move the left stick, right stick, and pull the triggers")
    print("Monitoring for 10 seconds...")
    print()

    input_count = [0]
    last_state = [""]

    def input_callback(state):
        input_count[0] += 1

        # Only print if values changed significantly
        current = (
            f"LS:({state.left_stick_x:+.2f},{state.left_stick_y:+.2f}) "
            f"RS:({state.right_stick_x:+.2f},{state.right_stick_y:+.2f}) "
            f"LT:{state.left_trigger:.2f} RT:{state.right_trigger:.2f}"
        )

        if current != last_state[0]:
            print(current)
            last_state[0] = current

    client.input_callback = input_callback

    # Start input loop as background task
    input_task = asyncio.create_task(client.start_input_loop())

    try:
        await asyncio.sleep(10)
        print(f"\n✓ Received {input_count[0]} input updates")

    finally:
        # Cancel input task
        input_task.cancel()
        try:
            await input_task
        except asyncio.CancelledError:
            pass


async def test_dpad(client):
    """Test D-pad inputs."""
    print("\n=== Test 6: D-pad test ===")
    print("Press each D-pad direction")
    print("Monitoring for 10 seconds...")
    print()

    dpad_presses = {
        "up": 0,
        "down": 0,
        "left": 0,
        "right": 0,
    }

    def input_callback(state):
        if state.dpad_up:
            dpad_presses["up"] += 1
            print("D-pad: UP")
        if state.dpad_down:
            dpad_presses["down"] += 1
            print("D-pad: DOWN")
        if state.dpad_left:
            dpad_presses["left"] += 1
            print("D-pad: LEFT")
        if state.dpad_right:
            dpad_presses["right"] += 1
            print("D-pad: RIGHT")

    client.input_callback = input_callback

    # Start input loop as background task
    input_task = asyncio.create_task(client.start_input_loop())

    try:
        await asyncio.sleep(10)
        print(f"\n✓ D-pad presses: {dpad_presses}")

    finally:
        # Cancel input task
        input_task.cancel()
        try:
            await input_task
        except asyncio.CancelledError:
            pass


async def test_continuous_input(client, duration=15):
    """Display continuous input for debugging."""
    print(f"\n=== Test 7: Continuous input display ({duration}s) ===")
    print("Use the controller normally and watch the output")
    print("Format: Sticks | Triggers | Buttons")
    print()

    def input_callback(state):
        # Format compact display
        sticks = f"LS({state.left_stick_x:+.2f},{state.left_stick_y:+.2f}) RS({state.right_stick_x:+.2f},{state.right_stick_y:+.2f})"
        triggers = f"LT:{state.left_trigger:.2f} RT:{state.right_trigger:.2f}"

        buttons = []
        if state.button_a: buttons.append("A")
        if state.button_b: buttons.append("B")
        if state.button_x: buttons.append("X")
        if state.button_y: buttons.append("Y")
        if state.button_lb: buttons.append("LB")
        if state.button_rb: buttons.append("RB")
        if state.button_view: buttons.append("VIEW")
        if state.button_menu: buttons.append("MENU")
        if state.dpad_up: buttons.append("UP")
        if state.dpad_down: buttons.append("DOWN")
        if state.dpad_left: buttons.append("LEFT")
        if state.dpad_right: buttons.append("RIGHT")

        buttons_str = ",".join(buttons) if buttons else "-"

        print(f"{sticks} | {triggers} | {buttons_str}")

    client.input_callback = input_callback

    # Start input loop as background task
    input_task = asyncio.create_task(client.start_input_loop())

    try:
        await asyncio.sleep(duration)
        print("\n✓ Continuous input test complete")

    finally:
        # Cancel input task
        input_task.cancel()
        try:
            await input_task
        except asyncio.CancelledError:
            pass


async def run_all_tests():
    """Run all Xbox controller tests."""
    print("=" * 60)
    print("Xbox Wireless Controller Test Suite")
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

        # Test 3: Single report read
        await test_read_single_report(client)

        # Test 4: Button mapping
        # Commented out by default as it's interactive
        # Uncomment if you want to verify button mapping
        # await test_button_mapping(client)

        # Test 5: Analog inputs
        await test_analog_inputs(client)

        # Test 6: D-pad
        await test_dpad(client)

        # Test 7: Continuous display
        await test_continuous_input(client, duration=15)

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
        if client and client.is_connected():
            print("\nDisconnecting...")
            await client.disconnect()


# Convenience functions for REPL use
def run():
    """Run all tests (convenience function for REPL)."""
    asyncio.run(run_all_tests())


def quick_test():
    """Quick test - just scan, connect, and show inputs for 10 seconds."""
    async def quick():
        device = await scan_for_device("Xbox", timeout_ms=10000)
        if device:
            client = XboxClient()
            if await client.connect(device):
                print("Controller connected! Showing inputs for 10 seconds...")

                def callback(state):
                    print(state)

                client.input_callback = callback
                task = asyncio.create_task(client.start_input_loop())

                try:
                    await asyncio.sleep(10)
                finally:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                    await client.disconnect()

                return client
        print("Quick test failed")
        return None

    return asyncio.run(quick())


if __name__ == "__main__":
    # Run tests if executed directly
    run()
