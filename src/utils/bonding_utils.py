"""
BLE Bonding Management Utilities

Handles bonding data cleanup to ensure reliable BLE connections.

Critical Discovery (Phase 2):
After bonding with `pair(bond=True)`, BLE devices may use Random Resolvable
Private Addresses (RPA) for privacy. The bonding data stored in ble_secrets.json
can become stale due to:
- Device IRK rotation
- Device power cycles resetting bonding keys
- Multiple device pairings overwriting bond data
- Limited bond storage slots on devices

For session-based applications (like RC cars), clearing bonding data on startup
ensures reliable connections by forcing fresh pairing each session.
"""

import os


def clear_bonding_data():
    """
    Clear BLE bonding data to ensure reliable connections.

    aioble stores bonding data (IRK, LTK keys) in 'ble_secrets.json'.
    This file can become stale, causing address resolution failures
    (devices show as 00:00:00:00:00:00 and connections fail).

    For session-based applications, clearing this on startup is the
    most reliable approach.

    Returns:
        True if file was deleted, False if file didn't exist
    """
    try:
        os.remove('ble_secrets.json')
        print("✓ Cleared old bonding data")
        return True
    except OSError:
        # File doesn't exist - nothing to clear
        return False


def bonding_data_exists():
    """
    Check if bonding data file exists.

    Returns:
        True if ble_secrets.json exists, False otherwise
    """
    try:
        os.stat('ble_secrets.json')
        return True
    except OSError:
        return False


def get_bonding_info():
    """
    Get information about stored bonding data.

    Returns:
        Dictionary with bonding data info:
        {
            'exists': bool,
            'size': int (bytes, -1 if doesn't exist)
        }
    """
    try:
        stats = os.stat('ble_secrets.json')
        return {
            'exists': True,
            'size': stats[6]  # st_size
        }
    except OSError:
        return {
            'exists': False,
            'size': -1
        }
