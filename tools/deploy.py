#!/usr/bin/env python3
"""
Deployment script for ESP32 Xbox LEGO RC Controller

This script uploads the source code to your ESP32-S3 device using mpremote.

Requirements:
    pip install mpremote

Usage:
    python tools/deploy.py [--port PORT] [--test]

Options:
    --port PORT    Specify serial port (default: auto-detect)
    --test         Also upload test scripts
    --clean        Remove all files from device first
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

libs = [
    "aioble",
]

utils = [
    "src/utils/__init__.py",
    "src/utils/ble_utils.py",
    "src/bonding_utils.py",
    "src/utils/constants.py",
    "src/utils/math_utils.py",
]

sources = [
    "src/ble_manager.py",
    "src/input_translator.py",
    "src/lego_client.py",
    "src/main.py",
    "src/xbox_client.py",
    "boot.py",
]



tests = [
    "testing/ble_scan.py",
    "testing/test_ble_manager.py",
    "testing/test_input_translator.py",
    "testing/test_lego_hub.py",
    "testing/test_xbox_controller.py",
]


def run_mpremote(args, verbose=True):
    """Run mpremote command."""
    cmd = ["mpremote"] + args
    if verbose:
        print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if verbose and result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def check_mpremote():
    """Check if mpremote is installed."""
    try:
        subprocess.run(["mpremote", "--help"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: mpremote not found!")
        print("Install it with: pip install mpremote")
        return False


def get_project_root():
    """Get the project root directory."""
    script_path = Path(__file__).resolve()
    return script_path.parent.parent


def deploy_utils(port_arg):
    """Deploy utility modules."""
    print("\n=== Deploying utility modules ===")

    # Create directories
    run_mpremote(port_arg + ["mkdir", ":src"])
    run_mpremote(port_arg + ["mkdir", ":src/utils"])

    # Upload files
    root = get_project_root()
    for file in utils:
        src = root / file
        dst = f":{file}"
        if not src.exists():
            print(f"Warning: {file} not found, skipping")
            continue

        if not run_mpremote(port_arg + ["cp", str(src), dst]):
            print(f"Failed to upload {file}")
            return False

    print("✓ Utility modules deployed")
    return True


def deploy_clients(port_arg):
    """Deploy client modules."""
    print("\n=== Deploying client modules ===")

    root = get_project_root()
    for file in sources:
        src = root / file
        dst = f":{file}"
        if not src.exists():
            print(f"Warning: {file} not found, skipping")
            continue

        if not run_mpremote(port_arg + ["cp", str(src), dst]):
            print(f"Failed to upload {file}")
            return False

    print("✓ Client modules deployed")
    return True


def deploy_tests(port_arg):
    """Deploy test scripts."""
    print("\n=== Deploying test scripts ===")

    root = get_project_root()
    for file in tests:
        src = root / file
        dst = f":{Path(file).name}"
        if not src.exists():
            print(f"Warning: {file} not found, skipping")
            continue

        if not run_mpremote(port_arg + ["cp", str(src), dst]):
            print(f"Failed to upload {file}")
            return False

    print("✓ Test scripts deployed")
    return True


def install_libraries(port_arg):
    """Install required MicroPython libraries."""
    print("\n=== Installing required libraries ===")

    for lib in libs:
        print(f"Installing {lib}...")

        if not run_mpremote(port_arg + ["mip", "install", lib]):
            print(f"Failed to install {lib}")
            return False

    print("✓ Libraries installed")
    return True


def clean_device(port_arg):
    """Remove all files from device."""
    print("\n=== Cleaning device ===")
    print("Warning: This will remove all files from the device!")
    response = input("Continue? (y/N): ")

    if response.lower() != 'y':
        print("Cancelled")
        return True

    # Remove common directories
    dirs_to_remove = [":src", ":testing"]
    for d in dirs_to_remove:
        run_mpremote(port_arg + ["rm", "-rf", d], verbose=False)

    print("✓ Device cleaned")
    return True


def list_files(port_arg):
    """List files on device."""
    print("\n=== Files on device ===")
    run_mpremote(port_arg + ["ls"])


def main():
    parser = argparse.ArgumentParser(
        description="Deploy code to ESP32-S3 device"
    )
    parser.add_argument(
        "--port",
        help="Serial port (e.g., COM3 or /dev/ttyUSB0)",
        default=None
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help=f"Also deploy test scripts: {" ".join([test for test in tests])}"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean device before deploying"
    )
    parser.add_argument(
        "--libs",
        action="store_true",
        help=f"Install required libraries: {" ".join([lib for lib in libs])}",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List files on device and exit"
    )

    args = parser.parse_args()

    # Check mpremote
    if not check_mpremote():
        sys.exit(1)

    # Build port argument
    port_arg = []
    if args.port:
        port_arg = ["connect", args.port]

    print("=" * 60)
    print("ESP32 Xbox LEGO RC Controller - Deployment Script")
    print("=" * 60)

    # List files only
    if args.list:
        list_files(port_arg)
        sys.exit(0)

    # Clean if requested
    if args.clean:
        if not clean_device(port_arg):
            sys.exit(1)

    # Install libraries if requested
    if args.libs:
        if not install_libraries(port_arg):
            print("\n✗ Library installation failed")
            sys.exit(1)

    # Deploy code
    success = True

    # Deploy utilities
    if not deploy_utils(port_arg):
        success = False

    # Deploy clients
    if success and not deploy_clients(port_arg):
        success = False

    # Deploy tests if requested
    if success and args.test:
        if not deploy_tests(port_arg):
            success = False

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("✓ Deployment successful!")
        print("\nNext steps:")
        print("1. Connect to device REPL: mpremote")
        if args.test:
            print("2. Run tests:")
            print("   >>> import test_lego_hub")
            print("   >>> test_lego_hub.run()")
            print("   >>> import test_xbox_controller")
            print("   >>> test_xbox_controller.run()")
        else:
            print("2. Deploy test scripts: python tools/deploy.py --test")
            print("3. Run tests as above")
    else:
        print("✗ Deployment failed")
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()
