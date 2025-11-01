"""
Enhanced Xbox controller discovery with HID setup steps.

This script tries different HID initialization sequences to get the controller
to send input data.
"""

import asyncio
import aioble
import bluetooth


async def test_xbox_hid_setup():
    """Test different HID setup sequences."""

    print("=" * 60)
    print("Xbox Controller HID Setup Testing")
    print("=" * 60)

    # Scan for controller
    print("\nScanning for Xbox controller...")
    device = None
    async with aioble.scan(duration_ms=10000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            if result.name() and "xbox" in result.name().lower():
                print(f"Found: {result.name()}")
                device = result.device
                break

    if not device:
        print("Controller not found!")
        return

    # Connect
    print("Connecting...")
    connection = await device.connect(timeout_ms=10000)
    print("Connected!")

    # Pair
    print("Pairing...")
    await connection.pair(bond=True)
    print("Paired!")

    # Get HID service and characteristics
    print("\nGetting HID service...")
    service = await connection.service(bluetooth.UUID(0x1812))

    hid_report = await service.characteristic(bluetooth.UUID(0x2A4D))
    protocol_mode = None
    hid_control = None

    try:
        protocol_mode = await service.characteristic(bluetooth.UUID(0x2A4E))
        print("✓ Protocol Mode characteristic found")
    except:
        print("✗ Protocol Mode not found")

    try:
        hid_control = await service.characteristic(bluetooth.UUID(0x2A4C))
        print("✓ HID Control Point found")
    except:
        print("✗ HID Control Point not found")

    # Test 1: Just subscribe (what we've been doing)
    print("\n" + "=" * 60)
    print("Test 1: Direct subscription (current approach)")
    print("=" * 60)
    success = await try_receive_data(hid_report, "No setup")
    if success:
        await connection.disconnect()
        return

    # Test 2: Set protocol mode to Report Protocol then subscribe
    if protocol_mode:
        print("\n" + "=" * 60)
        print("Test 2: Set Protocol Mode = Report Protocol (0x01)")
        print("=" * 60)
        try:
            await protocol_mode.write(b'\x01', response=True)
            print("✓ Wrote Report Protocol mode")
            success = await try_receive_data(hid_report, "After setting protocol mode")
            if success:
                await connection.disconnect()
                return
        except Exception as e:
            print(f"✗ Failed to write protocol mode: {e}")

    # Test 3: Write to HID Control Point (Exit Suspend = 0x00)
    if hid_control:
        print("\n" + "=" * 60)
        print("Test 3: Write to HID Control Point (Exit Suspend = 0x00)")
        print("=" * 60)
        try:
            await hid_control.write(b'\x00', response=False)
            print("✓ Wrote to HID Control Point")
            success = await try_receive_data(hid_report, "After HID control write")
            if success:
                await connection.disconnect()
                return
        except Exception as e:
            print(f"✗ Failed to write HID control: {e}")

    # Test 4: Both - protocol mode + control point
    if protocol_mode and hid_control:
        print("\n" + "=" * 60)
        print("Test 4: Protocol Mode + HID Control Point")
        print("=" * 60)
        try:
            await protocol_mode.write(b'\x01', response=True)
            await asyncio.sleep_ms(100)
            await hid_control.write(b'\x00', response=False)
            print("✓ Both writes successful")
            success = await try_receive_data(hid_report, "After both setup steps")
            if success:
                await connection.disconnect()
                return
        except Exception as e:
            print(f"✗ Setup failed: {e}")

    # Test 5: Try reading Report Map to trigger something
    print("\n" + "=" * 60)
    print("Test 5: Read Report Map first")
    print("=" * 60)
    try:
        report_map_char = await service.characteristic(bluetooth.UUID(0x2A4B))
        report_map = await report_map_char.read()
        print(f"✓ Read Report Map: {len(report_map)} bytes")
        success = await try_receive_data(hid_report, "After reading report map")
        if success:
            await connection.disconnect()
            return
    except Exception as e:
        print(f"✗ Failed: {e}")

    print("\n" + "=" * 60)
    print("All tests failed - controller not sending data")
    print("=" * 60)
    print("\nPossible issues:")
    print("1. ESP32 BLE stack may not fully support HID over GATT")
    print("2. Xbox controller may require Windows-specific setup")
    print("3. Controller may need USB connection first to configure")
    print("4. May need to unpair from other devices completely")

    await connection.disconnect()


async def try_receive_data(characteristic, description):
    """Try to receive data from a characteristic."""
    print(f"\n{description}:")
    print("Subscribing to notifications...")

    try:
        await characteristic.subscribe(notify=True)
        print("Subscribed! Press buttons...")

        # Try for 5 seconds
        received_count = 0
        for i in range(5):
            try:
                report = await asyncio.wait_for(characteristic.notified(), timeout=1.0)
                received_count += 1
                print(f"\n✓ Report {received_count}: {len(report)} bytes")
                hex_data = ' '.join(['{:02X}'.format(byte_val) for byte_val in report])
                print(f"  Hex: {hex_data}")
            except asyncio.TimeoutError:
                print(".", end="")

        if received_count > 0:
            print(f"\n✓✓✓ SUCCESS! Received {received_count} reports total ✓✓✓")
            return True
        else:
            print("\n✗ No data received")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def run():
    """Convenience function for REPL."""
    asyncio.run(test_xbox_hid_setup())


if __name__ == "__main__":
    run()
