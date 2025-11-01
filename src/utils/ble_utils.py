"""
BLE utility functions for device discovery and connection management
"""

import asyncio
import aioble
import bluetooth


async def scan_for_device(name_pattern: str, timeout_ms: int = 5000):
    """
    Scan for a BLE device matching the given name pattern.

    Args:
        name_pattern: String pattern to match in device name (case-insensitive)
        timeout_ms: Scan timeout in milliseconds

    Returns:
        Device object if found, None otherwise
    """
    print(f"Scanning for device matching '{name_pattern}'...")

    async with aioble.scan(duration_ms=timeout_ms, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            if result.name():
                device_name = result.name().lower()
                if name_pattern.lower() in device_name:
                    print(f"Found device: {result.name()} ({result.device})")
                    return result.device

    print(f"No device matching '{name_pattern}' found")
    return None


async def scan_for_multiple_devices(patterns: dict, timeout_ms: int = 10000):
    """
    Scan for multiple BLE devices matching different patterns.

    Args:
        patterns: Dictionary mapping device type to name pattern
                  e.g., {"xbox": "xbox", "lego": "technic move"}
        timeout_ms: Total scan timeout in milliseconds

    Returns:
        Dictionary mapping device type to device object (or None if not found)
    """
    print(f"Scanning for multiple devices...")
    found_devices = {key: None for key in patterns.keys()}

    async with aioble.scan(duration_ms=timeout_ms, interval_us=30000, window_us=30000, active=True) as scanner:
        async for result in scanner:
            if result.name():
                device_name = result.name().lower()

                # Check against all patterns
                for device_type, pattern in patterns.items():
                    if found_devices[device_type] is None and pattern.lower() in device_name:
                        print(f"Found {device_type}: {result.name()} ({result.device})")
                        found_devices[device_type] = result.device

                # If all devices found, stop scanning early
                if all(dev is not None for dev in found_devices.values()):
                    print("All devices found!")
                    break

    # Report what was found
    for device_type, device in found_devices.items():
        if device is None:
            print(f"Warning: {device_type} not found")

    return found_devices


def format_mac_address(addr):
    """
    Format a Bluetooth address for display.

    Args:
        addr: Bluetooth address (bytes or device object)

    Returns:
        Formatted MAC address string (XX:XX:XX:XX:XX:XX)
    """
    if hasattr(addr, 'addr'):
        # It's a device object
        addr_bytes = addr.addr
    elif isinstance(addr, bytes):
        addr_bytes = addr
    else:
        return str(addr)

    return ':'.join([f'{b:02X}' for b in addr_bytes])


async def wait_for_connection(connection, timeout_ms: int = 10000):
    """
    Wait for a BLE connection to be established with timeout.

    Args:
        connection: Connection coroutine
        timeout_ms: Timeout in milliseconds

    Returns:
        Connection object if successful, None on timeout
    """
    try:
        result = await asyncio.wait_for_ms(connection, timeout_ms)
        return result
    except asyncio.TimeoutError:
        print(f"Connection timeout after {timeout_ms}ms")
        return None


def bytes_to_hex(data: bytes) -> str:
    """
    Convert bytes to hex string for debugging.

    Args:
        data: Bytes to convert

    Returns:
        Hex string representation
    """
    return ' '.join([f'{b:02X}' for b in data])
