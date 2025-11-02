"""
Test script for Input Translator

Tests the mapping of Xbox controller inputs to LEGO vehicle commands
without requiring actual hardware connections.

Run from REPL:
>>> import testing.test_input_translator as t
>>> t.run_all_tests()
"""

import time
from src.input_translator import InputTranslator, ControlMode, VehicleCommand
from src.xbox_client import ControllerState
from src.utils.constants import LEGO_COLORS


def create_neutral_state():
    """Create a controller state with all inputs at neutral."""
    state = ControllerState()
    # All values default to 0/False which is neutral
    return state


def test_neutral_state():
    """Test that neutral controller produces zero motor commands."""
    print("\n" + "="*60)
    print("TEST: Neutral State")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()

    cmd = translator.translate(state)

    print(f"Input: All neutral")
    print(f"Output: {cmd}")

    assert cmd.motor_a_speed == 0, f"Expected motor_a=0, got {cmd.motor_a_speed}"
    assert cmd.motor_b_speed == 0, f"Expected motor_b=0, got {cmd.motor_b_speed}"
    assert cmd.led_color == LEGO_COLORS.BLACK, "Expected LEDs off"
    assert not cmd.emergency_stop, "Unexpected emergency stop"

    print("✓ PASSED: Neutral state produces zero output")
    return True


def test_forward_backward():
    """Test forward and backward movement (left stick Y-axis)."""
    print("\n" + "="*60)
    print("TEST: Forward and Backward Movement")
    print("="*60)

    translator = InputTranslator()

    # Test forward (positive Y)
    state = create_neutral_state()
    state.left_stick_y = 1.0  # Full forward

    cmd = translator.translate(state)
    print(f"Input: Left stick Y = 1.0 (forward)")
    print(f"Output: motor_a = {cmd.motor_a_speed}")

    assert cmd.motor_a_speed == 100, f"Expected motor_a=100, got {cmd.motor_a_speed}"
    assert cmd.motor_b_speed == 0, f"Expected motor_b=0, got {cmd.motor_b_speed}"

    # Test backward (negative Y)
    state.left_stick_y = -1.0  # Full backward

    cmd = translator.translate(state)
    print(f"Input: Left stick Y = -1.0 (backward)")
    print(f"Output: motor_a = {cmd.motor_a_speed}")

    assert cmd.motor_a_speed == -100, f"Expected motor_a=-100, got {cmd.motor_a_speed}"

    # Test partial forward (should apply curve)
    state.left_stick_y = 0.5  # Half forward

    cmd = translator.translate(state)
    print(f"Input: Left stick Y = 0.5 (half forward)")
    print(f"Output: motor_a = {cmd.motor_a_speed}")

    # With quadratic curve (power=2.0), 0.5^2 = 0.25, so expect 25% speed
    assert 20 <= cmd.motor_a_speed <= 30, f"Expected motor_a~25, got {cmd.motor_a_speed}"

    print("✓ PASSED: Forward/backward movement works correctly")
    return True


def test_steering():
    """Test left and right steering (right stick X-axis)."""
    print("\n" + "="*60)
    print("TEST: Steering")
    print("="*60)

    translator = InputTranslator()

    # Test right turn
    state = create_neutral_state()
    state.right_stick_x = 1.0  # Full right

    cmd = translator.translate(state)
    print(f"Input: Right stick X = 1.0 (right)")
    print(f"Output: motor_b = {cmd.motor_b_speed}")

    assert cmd.motor_b_speed == 100, f"Expected motor_b=100, got {cmd.motor_b_speed}"
    assert cmd.motor_a_speed == 0, f"Expected motor_a=0, got {cmd.motor_a_speed}"

    # Test left turn
    state.right_stick_x = -1.0  # Full left

    cmd = translator.translate(state)
    print(f"Input: Right stick X = -1.0 (left)")
    print(f"Output: motor_b = {cmd.motor_b_speed}")

    assert cmd.motor_b_speed == -100, f"Expected motor_b=-100, got {cmd.motor_b_speed}"

    print("✓ PASSED: Steering works correctly")
    return True


def test_brake_and_boost():
    """Test brake (left trigger) and boost (right trigger) modifiers."""
    print("\n" + "="*60)
    print("TEST: Brake and Boost")
    print("="*60)

    translator = InputTranslator()

    # Test normal forward
    state = create_neutral_state()
    state.left_stick_y = 1.0
    cmd_normal = translator.translate(state)
    normal_speed = cmd_normal.motor_a_speed

    print(f"Normal forward speed: {normal_speed}")

    # Test with brake
    state.left_trigger = 1.0  # Full brake
    cmd_brake = translator.translate(state)
    brake_speed = cmd_brake.motor_a_speed

    print(f"With full brake: {brake_speed}")
    assert brake_speed < normal_speed, "Brake should reduce speed"
    assert brake_speed >= normal_speed * 0.2, "Brake shouldn't reduce below 20%"

    # Test with boost
    state.left_trigger = 0.0  # No brake
    state.right_trigger = 1.0  # Full boost
    cmd_boost = translator.translate(state)
    boost_speed = cmd_boost.motor_a_speed

    print(f"With full boost: {boost_speed}")
    # Boost adds up to 50%, but can't exceed 100
    assert boost_speed == 100, f"Expected 100 (capped), got {boost_speed}"

    # Test boost with lower initial speed
    state.left_stick_y = 0.5  # Half forward
    cmd_boost_half = translator.translate(state)
    print(f"Half forward with boost: {cmd_boost_half.motor_a_speed}")

    print("✓ PASSED: Brake and boost work correctly")
    return True


def test_control_modes():
    """Test different control modes (normal, turbo, slow)."""
    print("\n" + "="*60)
    print("TEST: Control Modes")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()
    state.left_stick_y = 0.5  # Half stick

    # Test normal mode
    translator.set_mode(ControlMode.NORMAL)
    cmd_normal = translator.translate(state)
    print(f"Normal mode (0.5 input): motor_a = {cmd_normal.motor_a_speed}")

    # Test turbo mode (more linear, less curve)
    translator.set_mode(ControlMode.TURBO)
    cmd_turbo = translator.translate(state)
    print(f"Turbo mode (0.5 input): motor_a = {cmd_turbo.motor_a_speed}")

    # Turbo should give higher speed for same input (power=1.5 vs 2.0)
    assert cmd_turbo.motor_a_speed > cmd_normal.motor_a_speed, \
        "Turbo should be more responsive"

    # Test slow mode (lower max speed)
    translator.set_mode(ControlMode.SLOW)
    state.left_stick_y = 1.0  # Full stick
    cmd_slow = translator.translate(state)
    print(f"Slow mode (full input): motor_a = {cmd_slow.motor_a_speed}")

    # Slow mode caps at 50%
    assert cmd_slow.motor_a_speed <= 50, "Slow mode should cap at 50%"

    # Test mode cycling
    translator.set_mode(ControlMode.NORMAL)
    translator.cycle_mode()
    assert translator.mode == ControlMode.TURBO, "Should cycle to turbo"
    translator.cycle_mode()
    assert translator.mode == ControlMode.SLOW, "Should cycle to slow"
    translator.cycle_mode()
    assert translator.mode == ControlMode.NORMAL, "Should cycle back to normal"

    print("✓ PASSED: Control modes work correctly")
    return True


def test_speed_limit():
    """Test user-adjustable speed limit."""
    print("\n" + "="*60)
    print("TEST: Speed Limit")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()
    state.left_stick_y = 1.0  # Full forward

    # Test with default limit (100%)
    cmd_full = translator.translate(state)
    print(f"Default limit (100%): motor_a = {cmd_full.motor_a_speed}")
    assert cmd_full.motor_a_speed == 100

    # Reduce speed limit
    translator.adjust_speed_limit(-30)  # Down to 70%
    cmd_limited = translator.translate(state)
    print(f"With 70% limit: motor_a = {cmd_limited.motor_a_speed}")
    assert cmd_limited.motor_a_speed == 70

    # Test limit boundaries
    translator.adjust_speed_limit(-100)  # Should clamp to 0
    assert translator.max_speed_limit == 0

    translator.adjust_speed_limit(200)  # Should clamp to 100
    assert translator.max_speed_limit == 100

    print("✓ PASSED: Speed limit works correctly")
    return True


def test_emergency_stop():
    """Test emergency stop (X button)."""
    print("\n" + "="*60)
    print("TEST: Emergency Stop")
    print("="*60)

    translator = InputTranslator()

    # Set up driving state
    state = create_neutral_state()
    state.left_stick_y = 1.0
    state.right_stick_x = 0.5

    # First call without X button
    cmd1 = translator.translate(state)
    print(f"Before E-stop: {cmd1}")
    assert not cmd1.emergency_stop

    # Press X button
    state.button_x = True
    cmd2 = translator.translate(state)
    print(f"With X pressed: {cmd2}")
    assert cmd2.emergency_stop, "Should trigger emergency stop"

    # Release X button (should not trigger again)
    state.button_x = False
    cmd3 = translator.translate(state)
    print(f"After X released: {cmd3}")
    assert not cmd3.emergency_stop, "Should not trigger on button release"

    print("✓ PASSED: Emergency stop works correctly")
    return True


def test_led_control():
    """Test LED control (A=headlights, B=taillights)."""
    print("\n" + "="*60)
    print("TEST: LED Control")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()

    # Initial state (LEDs off)
    cmd = translator.translate(state)
    print(f"Initial LED state: {cmd.led_color}")
    assert cmd.led_color == LEGO_COLORS.BLACK

    # Press A button (toggle headlights on)
    state.button_a = True
    cmd = translator.translate(state)
    print(f"After A press (headlights ON): {cmd.led_color}")
    assert cmd.led_color == LEGO_COLORS.WHITE
    assert translator.headlights_on

    # Release A button (stay on)
    state.button_a = False
    cmd = translator.translate(state)
    print(f"After A release (headlights still ON): {cmd.led_color}")
    assert cmd.led_color == LEGO_COLORS.WHITE

    # Press A again (toggle headlights off)
    state.button_a = True
    cmd = translator.translate(state)
    print(f"After second A press (headlights OFF): {cmd.led_color}")
    assert cmd.led_color == LEGO_COLORS.BLACK
    assert not translator.headlights_on

    # Test taillights (B button)
    state.button_a = False
    state.button_b = True
    cmd = translator.translate(state)
    print(f"After B press (taillights ON): {cmd.led_color}")
    assert cmd.led_color == LEGO_COLORS.RED
    assert translator.taillights_on

    # Test both lights on (should be yellow)
    # Taillights are currently ON from previous test
    state.button_b = False  # Release B (taillights stay ON)
    translator.translate(state)  # Update button state
    state.button_a = True   # Press A to toggle headlights ON
    cmd = translator.translate(state)  # Now both should be ON
    print(f"With both lights ON: {cmd.led_color}")
    assert cmd.led_color == LEGO_COLORS.YELLOW
    assert translator.headlights_on
    assert translator.taillights_on

    print("✓ PASSED: LED control works correctly")
    return True


def test_button_edge_detection():
    """Test that button actions only trigger on press (not hold)."""
    print("\n" + "="*60)
    print("TEST: Button Edge Detection")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()

    # Press and hold LB (mode cycle)
    initial_mode = translator.mode
    state.button_lb = True

    cmd1 = translator.translate(state)
    mode_after_first = translator.mode
    print(f"After first translate with LB held: {mode_after_first}")
    assert mode_after_first != initial_mode, "Should cycle on first press"

    # Keep holding LB (should NOT cycle again)
    cmd2 = translator.translate(state)
    mode_after_second = translator.mode
    print(f"After second translate with LB still held: {mode_after_second}")
    assert mode_after_second == mode_after_first, "Should not cycle while held"

    # Release and press again (should cycle)
    state.button_lb = False
    translator.translate(state)  # Update state

    state.button_lb = True
    cmd3 = translator.translate(state)
    mode_after_third = translator.mode
    print(f"After releasing and pressing LB again: {mode_after_third}")
    assert mode_after_third != mode_after_second, "Should cycle on new press"

    print("✓ PASSED: Button edge detection works correctly")
    return True


def test_combined_inputs():
    """Test combining multiple inputs simultaneously."""
    print("\n" + "="*60)
    print("TEST: Combined Inputs")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()

    # Drive forward while turning right with boost
    state.left_stick_y = 0.7   # 70% forward
    state.right_stick_x = 0.5  # 50% right
    state.right_trigger = 0.5  # 50% boost

    cmd = translator.translate(state)
    print(f"Combined input:")
    print(f"  Left stick Y: 0.7 (forward)")
    print(f"  Right stick X: 0.5 (right)")
    print(f"  Right trigger: 0.5 (boost)")
    print(f"Output:")
    print(f"  Motor A: {cmd.motor_a_speed}")
    print(f"  Motor B: {cmd.motor_b_speed}")

    assert cmd.motor_a_speed > 0, "Should have forward motion"
    assert cmd.motor_b_speed > 0, "Should have right steering"

    # Both motors should be active
    assert cmd.motor_a_speed != 0 and cmd.motor_b_speed != 0

    print("✓ PASSED: Combined inputs work correctly")
    return True


def test_status_reporting():
    """Test status reporting."""
    print("\n" + "="*60)
    print("TEST: Status Reporting")
    print("="*60)

    translator = InputTranslator()

    status = translator.get_status()
    print(f"Initial status: {status}")

    assert 'mode' in status
    assert 'max_speed_limit' in status
    assert 'headlights' in status
    assert 'taillights' in status

    # Change some settings
    translator.set_mode(ControlMode.TURBO)
    translator.adjust_speed_limit(-20)
    translator.headlights_on = True

    status = translator.get_status()
    print(f"Updated status: {status}")

    assert status['mode'] == ControlMode.TURBO
    assert status['max_speed_limit'] == 80
    assert status['headlights'] == True

    print("✓ PASSED: Status reporting works correctly")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*70)
    print(" " * 20 + "INPUT TRANSLATOR TEST SUITE")
    print("="*70)

    tests = [
        ("Neutral State", test_neutral_state),
        ("Forward/Backward", test_forward_backward),
        ("Steering", test_steering),
        ("Brake and Boost", test_brake_and_boost),
        ("Control Modes", test_control_modes),
        ("Speed Limit", test_speed_limit),
        ("Emergency Stop", test_emergency_stop),
        ("LED Control", test_led_control),
        ("Button Edge Detection", test_button_edge_detection),
        ("Combined Inputs", test_combined_inputs),
        ("Status Reporting", test_status_reporting),
    ]

    passed = 0
    failed = 0
    errors = []

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                errors.append(f"{name}: Test returned False")
        except Exception as e:
            failed += 1
            errors.append(f"{name}: {type(e).__name__}: {e}")
            print(f"✗ FAILED: {name}")
            print(f"  Error: {e}")

    # Summary
    print("\n" + "="*70)
    print(" " * 25 + "TEST SUMMARY")
    print("="*70)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if errors:
        print("\nFailures:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("\n🎉 ALL TESTS PASSED!")

    print("="*70)

    return failed == 0


# Individual test runners for quick testing
def neutral():
    """Quick test: neutral state"""
    return test_neutral_state()

def forward_backward():
    """Quick test: forward/backward movement"""
    return test_forward_backward()

def steering():
    """Quick test: steering"""
    return test_steering()

def brake_boost():
    """Quick test: brake and boost"""
    return test_brake_and_boost()

def modes():
    """Quick test: control modes"""
    return test_control_modes()

def speed_limit():
    """Quick test: speed limit"""
    return test_speed_limit()

def emergency():
    """Quick test: emergency stop"""
    return test_emergency_stop()

def leds():
    """Quick test: LED control"""
    return test_led_control()

def buttons():
    """Quick test: button edge detection"""
    return test_button_edge_detection()

def combined():
    """Quick test: combined inputs"""
    return test_combined_inputs()

def status():
    """Quick test: status reporting"""
    return test_status_reporting()


if __name__ == "__main__":
    run_all_tests()
