"""
Discovery script to inspect all characteristics of the Xbox controller.

This will help us find the correct characteristic to subscribe to for input data.
"""

import asyncio
import aioble
import bluetooth


async def discover_xbox_controller():
    """Discover and display all services and characteristics of Xbox controller."""

    print("=" * 60)
    print("Xbox Controller BLE Discovery Tool")
    print("=" * 60)
    print("\nScanning for Xbox controller...")

    # Scan for controller
    device = None
    async with aioble.scan(duration_ms=10000, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            if result.name() and "xbox" in result.name().lower():
                print(f"Found: {result.name()} ({result.device.addr_hex()})")
                device = result.device
                break

    if not device:
        print("Xbox controller not found!")
        return

    # Connect
    print("\nConnecting...")
    connection = await device.connect(timeout_ms=10000)
    print("Connected!")

    # Pair
    print("\nPairing...")
    try:
        await connection.pair(bond=True)
        print("Paired successfully!")
    except Exception as e:
        print(f"Pairing error: {e}")

    print("\n" + "=" * 60)
    print("Discovering all services and characteristics...")
    print("=" * 60)

    # Standard service UUIDs to check
    services_to_check = [
        (bluetooth.UUID(0x1812), "HID Service"),
        (bluetooth.UUID(0x180F), "Battery Service"),
        (bluetooth.UUID(0x180A), "Device Information Service"),
    ]

    for service_uuid, service_name in services_to_check:
        print(f"\n--- {service_name} ({service_uuid}) ---")
        try:
            service = await connection.service(service_uuid)
            print(f"✓ Service found!")

            # Try to discover characteristics
            # Note: aioble doesn't have a direct "list all characteristics" method
            # So we'll try common HID characteristic UUIDs

            if service_uuid == bluetooth.UUID(0x1812):  # HID Service
                char_uuids = [
                    (bluetooth.UUID(0x2A4D), "HID Report"),
                    (bluetooth.UUID(0x2A4A), "HID Information"),
                    (bluetooth.UUID(0x2A4B), "Report Map"),
                    (bluetooth.UUID(0x2A4C), "HID Control Point"),
                    (bluetooth.UUID(0x2A4E), "Protocol Mode"),
                ]

                for char_uuid, char_name in char_uuids:
                    try:
                        char = await service.characteristic(char_uuid)
                        print(f"  ✓ {char_name} ({char_uuid})")
                        print(f"    Characteristic object: {char}")

                        # Try to read characteristic properties if available
                        # Note: aioble characteristics don't expose properties directly
                        # but we can try reading/subscribing to see what works

                    except Exception as e:
                        print(f"  ✗ {char_name} ({char_uuid}) - {e}")

            elif service_uuid == bluetooth.UUID(0x180F):  # Battery Service
                try:
                    char = await service.characteristic(bluetooth.UUID(0x2A19))
                    print(f"  ✓ Battery Level ({bluetooth.UUID(0x2A19)})")
                    # Try reading battery level
                    try:
                        level = await char.read()
                        print(f"    Battery: {level[0]}%")
                    except:
                        pass
                except Exception as e:
                    print(f"  ✗ Battery Level - {e}")

        except Exception as e:
            print(f"✗ Service not found or error: {e}")

    print("\n" + "=" * 60)
    print("Testing HID Report characteristic subscription...")
    print("=" * 60)

    # Try the HID Report characteristic
    try:
        service = await connection.service(bluetooth.UUID(0x1812))
        char = await service.characteristic(bluetooth.UUID(0x2A4D))

        print("\nSubscribing to HID Report notifications...")
        await char.subscribe(notify=True)
        print("Subscribed! Press buttons on controller...")
        print("Waiting 10 seconds for data...\n")

        # Try to receive notifications (10 attempts with 1 second timeout each)
        received_count = 0
        attempts = 10

        for i in range(attempts):
            try:
                report = await asyncio.wait_for(char.notified(), timeout=1.0)
                received_count += 1
                print(f"Report {received_count}: {len(report)} bytes")
                print(f"  Hex: {' '.join(f'{b:02X}' for b in report)}")
                print(f"  Dec: {list(report)}")
            except asyncio.TimeoutError:
                print(".", end="")

        print(f"\n\nTotal reports received: {received_count}")

        if received_count == 0:
            print("\n⚠ WARNING: No data received!")
            print("This suggests:")
            print("1. Wrong characteristic UUID")
            print("2. Controller not sending notifications")
            print("3. Additional setup required")

    except Exception as e:
        print(f"Error testing HID Report: {e}")
        import sys
        sys.print_exception(e)

    # Disconnect
    print("\nDisconnecting...")
    await connection.disconnect()
    print("Done!")


def run():
    """Convenience function for REPL."""
    asyncio.run(discover_xbox_controller())


if __name__ == "__main__":
    run()
