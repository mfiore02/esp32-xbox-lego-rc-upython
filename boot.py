"""
Boot script for ESP32 RC Car Controller

This file runs automatically when the ESP32 boots.

For development:
- Comment out the auto-start line to prevent automatic execution
- Use REPL to run tests manually

For production:
- Uncomment the auto-start line to run on boot
"""

import time
import sys

sys.path.append("src")
sys.path.append("src/utils")
sys.path.append("testing")

# Small delay to allow serial connection
time.sleep(2)

print("\n" + "="*60)
print(" " * 10 + "ESP32 RC CAR CONTROLLER - BOOT")
print("="*60)
print()

# =============================================================================
# AUTO-START CONFIGURATION
# =============================================================================

# Set to True to automatically start the RC car controller on boot
AUTO_START = False

# Set to True to run quick hardware tests before starting
RUN_TESTS = False

# =============================================================================

if RUN_TESTS:
    print("Running hardware tests...")
    print("(Not implemented yet - set RUN_TESTS = False)")
    print()

if AUTO_START:
    print("Auto-starting RC car controller...")
    print("Press Ctrl+C within 3 seconds to cancel...")
    print()

    # Give user time to cancel
    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)

    try:
        import src.main as main
        main.run()
    except KeyboardInterrupt:
        print("\nAuto-start cancelled by user")
    except Exception as e:
        print(f"\n✗ Error during auto-start: {e}")
        import sys
        sys.print_exception(e)
else:
    print("Auto-start disabled")
    print()
    print("To start the RC car controller, run:")
    print("  >>> import src.main as main")
    print("  >>> main.run()")
    print()
    print("To run tests, see files in testing/ directory")
    print()

print("="*60)
print("Ready for REPL commands")
print("="*60)
print()
