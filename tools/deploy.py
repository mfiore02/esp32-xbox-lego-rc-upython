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

utility_files = [
    "src/utils/__init__.py",
    "src/utils/ble_utils.py",
    "src/utils/bonding_utils.py",
    "src/utils/constants.py",
    "src/utils/math_utils.py",
]

primary_files = [
    "boot.py",
    "src/ble_manager.py",
    "src/input_translator.py",
    "src/lego_client.py",
    "src/main.py",
    "src/xbox_client.py",
]

test_files = [
    "testing/ble_scan.py",
    "testing/test_ble_manager.py",
    "testing/test_input_translator.py",
    "testing/test_lego_hub.py",
    "testing/test_xbox_controller.py",
]

dirs_to_create = [
    "testing",
    "lib",
    "src",
    "src/utils",
]

dirs_to_remove = [
    "testing",
    "lib",
    "src",
]


def run_mpremote(args, verbose=False) -> tuple[bool, str]:
    """Run mpremote command."""
    cmd = ["mpremote"] + args
    if verbose:
        print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if verbose and result.stdout:
            print(result.stdout)
        return True, ""
    except subprocess.CalledProcessError as e:
        if verbose and e.stderr:
            print(e.stderr)
        return False, e.stderr


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

    # Upload files
    root = get_project_root()
    for file in utility_files:
        src = root / file
        dst = f":{file}"
        print(f"Uploading utility module {file}...")
        if not src.exists():
            print("Warning: file not found, skipping")
            continue

        ret, stderr = run_mpremote(port_arg + ["cp", str(src), dst])
        if not ret:
            print(f"File not uploaded: {stderr.strip()}")
            return False

    print("✓ Utility modules deployed")
    return True


def deploy_primary(port_arg):
    """Deploy primary modules."""
    print("\n=== Deploying primary modules ===")

    root = get_project_root()
    for file in primary_files:
        src = root / file
        dst = f":{file}"
        print(f"Uploading primary module {file}...")
        if not src.exists():
            print("Warning: file not found, skipping")
            continue

        ret, stderr = run_mpremote(port_arg + ["cp", str(src), dst])
        if not ret:
            print(f"File not uploaded: {stderr.strip()}")
            return False

    print("✓ Primary modules deployed")
    return True


def deploy_tests(port_arg):
    """Deploy test scripts."""
    print("\n=== Deploying test scripts ===")

    root = get_project_root()
    for file in test_files:
        src = root / file
        dst = f":{file}"
        print(f"Uploading test script {file}...")
        if not src.exists():
            print("Warning: file not found, skipping")
            continue

        ret, stderr = run_mpremote(port_arg + ["cp", str(src), dst])
        if not ret:
            print(f"File not uploaded: {stderr.strip()}")
            return False

    print("✓ Test scripts deployed")
    return True


def install_libraries(port_arg):
    """Install required MicroPython libraries."""
    print("\n=== Installing required libraries ===")

    for lib in libs:
        print(f"Installing {lib}...")
        ret, stderr = run_mpremote(port_arg + ["ls", f"lib/{lib}"], verbose=False)
        if ret:
            print("Library already installed, skipping")
            continue  # Directory exists
        ret, stderr = run_mpremote(port_arg + ["mip", "install", lib])
        if not ret:
            print(f"Library not installed: {stderr.strip()}")
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

    # Remove test files
    for t in test_files:
        print(f"Removing test file {t}...")
        ret, stderr = run_mpremote(port_arg + ["rm", t], verbose=False)
        if not ret:
            print(f"File not removed: {stderr.strip()}")

    # Remove primary files
    for p in primary_files:
        print(f"Removing primary file {p}...")
        ret, stderr = run_mpremote(port_arg + ["rm", p], verbose=False)
        if not ret:
            print(f"File not removed: {stderr.strip()}")

    # Remove utility files
    for u in utility_files:
        print(f"Removing utility file {u}...")
        ret, stderr = run_mpremote(port_arg + ["rm", u], verbose=False)
        if not ret:
            print(f"File not removed: {stderr.strip()}")

    # Remove common directories
    for d in dirs_to_remove:
        print(f"Removing directory {d}...")
        ret, stderr = run_mpremote(port_arg + ["rm", "-rf", d], verbose=False)
        if not ret:
            print(f"Directory not removed: {stderr.strip()}")

    print("✓ Device cleaned")
    return True


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
        "--tests",
        action="store_true",
        help=f"Deploy test scripts: {" ".join([t for t in test_files])}"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove all installed files on device and exit"
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

    # Clean if requested
    if args.clean:
        clean_device(port_arg)
        sys.exit(0)

    # Create directories
    for d in dirs_to_create:
        print(f"Creating directory {d}...")
        ret, stderr = run_mpremote(port_arg + ["ls", d], verbose=False)
        if ret:
            print("Directory already exists, skipping")
            continue  # Directory exists
        ret, stderr = run_mpremote(port_arg + ["mkdir", f":{d}"])
        if not ret:
            print(f"Directory creation failed: {stderr.strip()}")
    print("✓ Directories created")

    success = True

    # Install libraries
    if not install_libraries(port_arg):
        print("\n✗ Library installation failed")
        success = False

    # Deploy src
    if success and not deploy_primary(port_arg):
        success = False

    # Deploy utilities
    if success and not deploy_utils(port_arg):
        success = False

    # Deploy tests if requested
    if success and args.tests:
        if not deploy_tests(port_arg):
            success = False

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("✓ Deployment successful!")
        print("\nNext steps:")
        print("1. Connect to device REPL: mpremote soft-reset repl")
        if args.tests:
            print("2. Run tests:")
            print("   >>> import <test>")
            print("   >>> <test>.run()")
        else:
            print("2. Run application:")
            print("   >>> import main")
            print("   >>> main.run()")
    else:
        print("✗ Deployment failed")
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()
