"""
BLE Connection Manager for ESP32 Xbox LEGO RC Controller

Manages dual simultaneous BLE connections to:
- Xbox Wireless Controller (input source)
- LEGO Technic Move Hub (output target)

Handles connection state, scanning, pairing, and reconnection logic.
"""

import asyncio
from xbox_client import XboxClient, XBOX_DEVICE_NAME
from lego_client import LegoClient, LEGO_DEVICE_NAME
from utils.ble_utils import scan_for_device


class ConnectionState:
    """Connection state enumeration."""
    DISCONNECTED = "disconnected"
    SCANNING = "scanning"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class BLEManager:
    """
    Manages dual BLE connections for Xbox controller and LEGO hub.

    Provides high-level API for:
    - Scanning and connecting to both devices
    - Monitoring connection health
    - Coordinating state between devices
    - Handling disconnections
    """

    def __init__(self, dead_zone: float = 0.03):
        """
        Initialize BLE manager.

        Args:
            dead_zone: Dead zone for Xbox controller analog sticks (0.0-1.0)
        """
        # Client instances
        self.xbox_client = XboxClient(dead_zone=dead_zone)
        self.lego_client = LegoClient()

        # Connection state
        self.xbox_state = ConnectionState.DISCONNECTED
        self.lego_state = ConnectionState.DISCONNECTED

        # Device references
        self.xbox_device = None
        self.lego_device = None

        # Status callback
        self.status_callback = None

    async def scan_xbox(self, timeout_ms: int = 10000) -> dict:
        """
        Scan for Xbox controller.

        Args:
            timeout_ms: Scan timeout in milliseconds

        Returns:
            Dictionary with scan results:
            {
                "xbox": device or None,
                "xbox_found": bool,
            }
        """
        results = {
            "xbox": None,
            "xbox_found": False,
        }

        print("\nScanning for Xbox controller...")
        self.xbox_state = ConnectionState.SCANNING
        self._notify_status()

        self.xbox_device = await scan_for_device("xbox", timeout_ms=timeout_ms)
        if self.xbox_device:
            print(f"✓ Found Xbox controller")
            results["xbox"] = self.xbox_device
            results["xbox_found"] = True
        else:
            print("✗ Xbox controller not found")
            self.xbox_state = ConnectionState.DISCONNECTED

        self._notify_status()
        return results
    
    async def scan_lego(self, timeout_ms: int = 10000) -> dict:
        """
        Scan for LEGO hub.

        Args:
            timeout_ms: Scan timeout in milliseconds

        Returns:
            Dictionary with scan results:
            {
                "lego": device or None,
                "lego_found": bool
            }
        """
        results = {
            "lego": None,
            "lego_found": False
        }

        print("\nScanning for LEGO hub...")
        self.lego_state = ConnectionState.SCANNING
        self._notify_status()

        self.lego_device = await scan_for_device("technic move", timeout_ms=timeout_ms)
        if self.lego_device:
            print(f"✓ Found LEGO hub")
            results["lego"] = self.lego_device
            results["lego_found"] = True
        else:
            print("✗ LEGO hub not found")
            self.lego_state = ConnectionState.DISCONNECTED

        self._notify_status()
        return results

    async def scan_devices(self, timeout_ms: int = 10000) -> dict:
        """
        Scan for both Xbox controller and LEGO hub.

        Args:
            timeout_ms: Scan timeout in milliseconds

        Returns:
            Dictionary with scan results:
            {
                "xbox": device or None,
                "lego": device or None,
                "xbox_found": bool,
                "lego_found": bool
            }
        """
        print("\n=== Scanning for devices ===")

        results = {
            "xbox": None,
            "lego": None,
            "xbox_found": False,
            "lego_found": False
        }

        # Scan for Xbox controller
        xbox_results = await self.scan_xbox(timeout_ms=timeout_ms)

        # Scan for LEGO hub
        lego_results = await self.scan_lego(timeout_ms=timeout_ms)

        results.update(xbox_results)
        results.update(lego_results)
        return results
    
    async def connect_xbox(self, device) -> bool:
        """
        Connect to Xbox controller.

        Args:
            device: BLE device object from scan

        Returns:
            True if connection successful, False otherwise
        """
        if not device:
            print("✗ No Xbox device provided for connection")
            return False
        
        print("\n=== Connecting to Xbox controller ===")
        self.xbox_state = ConnectionState.CONNECTING
        self._notify_status()

        try:
            success = await self.xbox_client.connect(device)
            if success:
                self.xbox_state = ConnectionState.CONNECTED
                print("✓ Xbox controller connected")
            else:
                self.xbox_state = ConnectionState.ERROR
                print("✗ Xbox connection failed")
            self._notify_status()
            return success
        except Exception as e:
            self.xbox_state = ConnectionState.ERROR
            print(f"✗ Xbox connection error: {e}")
            self._notify_status()
            return False
        
    async def connect_lego(self, device) -> bool:
        """
        Connect to LEGO hub.

        Args:
            device: BLE device object from scan

        Returns:
            True if connection successful, False otherwise
        """
        if not device:
            print("✗ No LEGO device provided for connection")
            return False
        
        print("\n=== Connecting to LEGO hub ===")
        self.lego_state = ConnectionState.CONNECTING
        self._notify_status()

        try:
            success = await self.lego_client.connect(device)
            if success:
                self.lego_state = ConnectionState.CONNECTED
                print("✓ LEGO hub connected")
            else:
                self.lego_state = ConnectionState.ERROR
                print("✗ LEGO connection failed")
            self._notify_status()
            return success
        except Exception as e:
            self.lego_state = ConnectionState.ERROR
            print(f"✗ LEGO connection error: {e}")
            self._notify_status()
            return False

    async def connect_all(self, xbox_device=None, lego_device=None) -> dict:
        """
        Connect to both devices.

        Args:
            xbox_device: Optional Xbox device from previous scan
            lego_device: Optional LEGO device from previous scan

        Returns:
            Dictionary with connection results:
            {
                "xbox_connected": bool,
                "lego_connected": bool,
                "both_connected": bool,
                "errors": list of error messages
            }
        """
        # Use provided devices or stored devices from scan
        xbox_dev = xbox_device or self.xbox_device
        lego_dev = lego_device or self.lego_device

        results = {
            "xbox_connected": False,
            "lego_connected": False,
            "both_connected": False,
            "errors": []
        }

        if not xbox_dev:
            results["errors"].append("No Xbox device available for connection")
            print("✗ No Xbox device available for connection")
        elif not lego_dev:
            results["errors"].append("No LEGO device available for connection")
            print("✗ No LEGO device available for connection")
        else:
            print("\n=== Connecting to devices ===")
             # Connect to Xbox controller
            results["xbox_connected"] = await self.connect_xbox(xbox_dev)
            # Connect to LEGO hub
            results["lego_connected"] = await self.connect_lego(lego_dev)

        # Check if both connected
        results["both_connected"] = results["xbox_connected"] and results["lego_connected"]

        if results["both_connected"]:
            print("\n✓✓✓ Both devices connected successfully! ✓✓✓")
        else:
            print(f"\n⚠ Partial connection: Xbox={results['xbox_connected']}, LEGO={results['lego_connected']}")

        self._notify_status()
        return results

    async def scan_and_connect_all(self, scan_timeout_ms: int = 10000) -> dict:
        """
        Convenience method to scan and connect to both devices.

        Args:
            scan_timeout_ms: Scan timeout in milliseconds

        Returns:
            Dictionary with connection results (same as connect_all)
        """
        # Scan for devices
        scan_results = await self.scan_devices(timeout_ms=scan_timeout_ms)

        if not scan_results["xbox_found"] and not scan_results["lego_found"]:
            print("\n✗ No devices found")
            return {
                "xbox_connected": False,
                "lego_connected": False,
                "both_connected": False,
                "errors": ["No devices found during scan"]
            }

        # Connect to found devices
        return await self.connect_all()

    async def disconnect_all(self):
        """Disconnect from both devices."""
        print("\n=== Disconnecting from devices ===")

        # Disconnect Xbox
        if self.xbox_client.is_connected():
            await self.xbox_client.disconnect()
            print("✓ Xbox controller disconnected")
        self.xbox_state = ConnectionState.DISCONNECTED

        # Disconnect LEGO
        if self.lego_client.is_connected():
            await self.lego_client.disconnect()
            print("✓ LEGO hub disconnected")
        self.lego_state = ConnectionState.DISCONNECTED

        self._notify_status()

    def is_ready(self) -> bool:
        """
        Check if both devices are connected and ready.

        Returns:
            True if both Xbox and LEGO are connected
        """
        return (
            self.xbox_state == ConnectionState.CONNECTED and
            self.lego_state == ConnectionState.CONNECTED and
            self.xbox_client.is_connected() and
            self.lego_client.is_connected()
        )

    def get_status(self) -> dict:
        """
        Get current connection status.

        Returns:
            Dictionary with status information:
            {
                "xbox_state": str,
                "lego_state": str,
                "xbox_connected": bool,
                "lego_connected": bool,
                "ready": bool,
                "xbox_info": dict,
                "lego_info": dict
            }
        """
        return {
            "xbox_state": self.xbox_state,
            "lego_state": self.lego_state,
            "xbox_connected": self.xbox_client.is_connected(),
            "lego_connected": self.lego_client.is_connected(),
            "ready": self.is_ready(),
            "xbox_info": self.xbox_client.get_connection_info(),
            "lego_info": self.lego_client.get_connection_info()
        }

    def set_status_callback(self, callback):
        """
        Set callback for status updates.

        Args:
            callback: Function to call when status changes
                     Signature: callback(status: dict)
        """
        self.status_callback = callback

    def _notify_status(self):
        """Notify status callback if set."""
        if self.status_callback:
            try:
                self.status_callback(self.get_status())
            except Exception as e:
                print(f"Status callback error: {e}")

    async def check_connections(self) -> dict:
        """
        Check connection health for both devices.

        Returns:
            Dictionary with health check results:
            {
                "xbox_ok": bool,
                "lego_ok": bool,
                "all_ok": bool
            }
        """
        xbox_ok = self.xbox_client.is_connected()
        lego_ok = self.lego_client.is_connected()

        # Update states based on actual connection status
        if not xbox_ok and self.xbox_state == ConnectionState.CONNECTED:
            self.xbox_state = ConnectionState.DISCONNECTED
            print("⚠ Xbox controller disconnected")

        if not lego_ok and self.lego_state == ConnectionState.CONNECTED:
            self.lego_state = ConnectionState.DISCONNECTED
            print("⚠ LEGO hub disconnected")

        return {
            "xbox_ok": xbox_ok,
            "lego_ok": lego_ok,
            "all_ok": xbox_ok and lego_ok
        }

    def get_xbox_client(self) -> XboxClient:
        """Get Xbox client instance."""
        return self.xbox_client

    def get_lego_client(self) -> LegoClient:
        """Get LEGO client instance."""
        return self.lego_client
