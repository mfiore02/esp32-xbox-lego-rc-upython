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
import time

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
        # Subscribe to notifications first
        await client.report_characteristic.subscribe(notify=True)
        print("Subscribed to notifications, waiting for input...")

        # Try to read a single report with timeout
        report = await asyncio.wait_for(
            client.report_characteristic.notified(),
            timeout=5.0
        )

        if report:
            print(f"✓ Received report: {len(report)} bytes")
            hex_data = ' '.join(['{:02X}'.format(byte_val) for byte_val in report])
            print(f"Raw data: {hex_data}")
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

    # Read reports directly for 10 seconds (don't start a new input loop)
    try:
        start_time = time.ticks_ms()
        duration_ms = 10000

        while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
            try:
                report = await asyncio.wait_for(
                    client.report_characteristic.notified(),
                    timeout=0.5
                )
                if report:
                    input_count[0] += 1
                    client.parse_hid_report(report)
            except asyncio.TimeoutError:
                print(".", end="")

        print(f"\n✓ Received {input_count[0]} input updates")

    except Exception as e:
        print(f"\n✗ Error: {e}")


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

    # Read reports directly for 10 seconds
    try:
        start_time = time.ticks_ms()
        duration_ms = 10000

        while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
            try:
                report = await asyncio.wait_for(
                    client.report_characteristic.notified(),
                    timeout=0.5
                )
                if report:
                    client.parse_hid_report(report)
            except asyncio.TimeoutError:
                print(".", end="")

        print(f"\n✓ D-pad presses: {dpad_presses}")

    except Exception as e:
        print(f"\n✗ Error: {e}")


async def test_continuous_input(client, duration=15):
    """Display continuous input for debugging."""
    print(f"\n=== Test 7: Continuous input display ({duration}s) ===")
    print("Use the controller normally and watch the output")
    print("Format: Sticks | Triggers | Buttons")
    print()

    report_count = [0]

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

    # Read reports directly for the duration
    try:
        start_time = time.ticks_ms()
        duration_ms = duration * 1000

        while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
            try:
                report = await asyncio.wait_for(
                    client.report_characteristic.notified(),
                    timeout=0.5
                )
                if report:
                    report_count[0] += 1
                    client.parse_hid_report(report)
            except asyncio.TimeoutError:
                print(".", end="")

        print(f"\n✓ Continuous input test complete ({report_count[0]} reports)")

    except Exception as e:
        print(f"\n✗ Error: {e}")


async def test_full_state_display(client, duration=30):
    """
    Display complete controller state in organized format.

    This test shows ALL inputs in real-time:
    - All buttons
    - D-pad
    - Analog sticks
    - Triggers

    Useful for verifying input mappings are correct.

    Args:
        client: Connected XboxClient instance
        duration: How long to run the test in seconds

    Returns:
        True if test completes successfully, False otherwise
    """
    print("\n" + "=" * 60)
    print(f"Full Controller State Display ({duration}s)")
    print("=" * 60)
    print("Press ALL buttons, move ALL sticks, and pull ALL triggers")
    print("to verify mappings are correct.")
    print()

    # Validate client state
    if not client.is_connected():
        print("✗ Error: Client is not connected")
        print("  Make sure the client is connected before calling this test")
        return False

    if client.report_characteristic is None:
        print("✗ Error: Report characteristic is not initialized")
        print("  Make sure the client was properly connected before calling this test")
        return False

    def input_callback(state):
        """Update display with new state."""
        state_str = state.__str__()
        # Clear previous output (print new state)
        print("\n")  # Some spacing
        print(state_str)

    client.input_callback = input_callback

    # Subscribe to notifications (if not already)
    try:
        await client.report_characteristic.subscribe(notify=True)
    except:
        pass  # Already subscribed

    print("Waiting for input...")
    print()

    # Display initial state
    input_callback(client.state)

    # Read reports for the duration
    try:
        start_time = time.ticks_ms()
        duration_ms = duration * 1000
        report_count = [0]

        while time.ticks_diff(time.ticks_ms(), start_time) < duration_ms:
            try:
                report = await asyncio.wait_for(
                    client.report_characteristic.notified(),
                    timeout=0.5
                )
                if report:
                    report_count[0] += 1
                    client.parse_hid_report(report)
            except asyncio.TimeoutError:
                pass

        print(f"\n✓ Full state display complete ({report_count[0]} reports received)")
        print("All input mappings can be verified from the display above.")
        return True

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import sys
        sys.print_exception(e)
        return False


def full_state_test(duration=30):
    """
    Standalone full state display test - can be called directly from REPL.

    This function handles scanning, connecting, and displaying the full controller
    state for the specified duration.

    Usage:
        >>> import test_xbox_controller
        >>> test_xbox_controller.full_state_test(duration=60)

    Args:
        duration: How long to display controller state in seconds

    Returns:
        The connected client (already disconnected at end) or None on failure
    """
    async def run_test():
        print("=" * 60)
        print(f"Full State Display Test ({duration}s)")
        print("=" * 60)
        print()

        # Scan for controller
        print("Scanning for Xbox controller...")
        device = await scan_for_device("Xbox", timeout_ms=10000)

        if not device:
            print("✗ Xbox controller not found")
            print("  Make sure controller is in pairing mode (hold Xbox + pairing button)")
            return None

        # Connect
        client = XboxClient()
        if not await client.connect(device):
            print("✗ Failed to connect to controller")
            return None

        try:
            # Run full state display test
            await test_full_state_display(client, duration=duration)
        finally:
            # Disconnect
            if client.is_connected():
                await client.disconnect()

        return client

    return asyncio.run(run_test())


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
    """
    Quick test - just scan, connect, and show inputs for 10 seconds.

    Usage:
        >>> import test_xbox_controller
        >>> test_xbox_controller.quick_test()
    """
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
