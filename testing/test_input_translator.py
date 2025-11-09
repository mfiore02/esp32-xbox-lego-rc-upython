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
from src.utils.constants import LIGHTS_ON, LIGHTS_OFF, LIGHTS_BRAKE


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
    assert cmd.lights == LIGHTS_OFF, f"Expected lights off ({LIGHTS_OFF}), got {cmd.lights}"

    print("✓ PASSED: Neutral state produces zero output")
    return True


def test_forward_backward():
    """Test forward and backward movement (gas pedal + direction toggle)."""
    print("\n" + "="*60)
    print("TEST: Forward and Backward Movement")
    print("="*60)

    translator = InputTranslator()

    # Test forward with gas pedal (default direction is forward)
    state = create_neutral_state()
    state.right_trigger = 1.0  # Full gas

    cmd = translator.translate(state)
    print(f"Input: Right trigger = 1.0 (full gas, forward direction)")
    print(f"Output: motor_a = {cmd.motor_a_speed}")

    assert cmd.motor_a_speed == 100, f"Expected motor_a=100, got {cmd.motor_a_speed}"
    assert cmd.motor_b_speed == 0, f"Expected motor_b=0, got {cmd.motor_b_speed}"

    # Toggle to reverse direction
    state.right_trigger = 0.0  # Release gas
    state.button_b = True
    translator.translate(state)  # Process button press
    state.button_b = False
    translator.translate(state)  # Update button state

    # Test backward (gas pedal in reverse direction)
    state.right_trigger = 1.0  # Full gas in reverse

    cmd = translator.translate(state)
    print(f"Input: Right trigger = 1.0 (full gas, reverse direction)")
    print(f"Output: motor_a = {cmd.motor_a_speed}")

    assert cmd.motor_a_speed == -100, f"Expected motor_a=-100, got {cmd.motor_a_speed}"

    # Toggle back to forward
    state.right_trigger = 0.0
    state.button_b = True
    translator.translate(state)
    state.button_b = False
    translator.translate(state)

    # Test partial gas (should apply curve)
    state.right_trigger = 0.5  # Half gas

    cmd = translator.translate(state)
    print(f"Input: Right trigger = 0.5 (half gas)")
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


def test_gas_and_brake():
    """Test gas pedal (right trigger) and brake pedal (left trigger)."""
    print("\n" + "="*60)
    print("TEST: Gas and Brake Pedals")
    print("="*60)

    translator = InputTranslator()

    # Test gas pedal only
    state = create_neutral_state()
    state.right_trigger = 1.0  # Full gas
    cmd_gas = translator.translate(state)
    gas_speed = cmd_gas.motor_a_speed

    print(f"Full gas pedal: {gas_speed}")
    assert gas_speed == 100, f"Expected 100, got {gas_speed}"

    # Test brake pedal only (negative drive input)
    state.right_trigger = 0.0  # No gas
    state.left_trigger = 1.0  # Full brake
    cmd_brake = translator.translate(state)
    brake_speed = cmd_brake.motor_a_speed

    print(f"Full brake pedal: {brake_speed}")
    assert brake_speed == -100, f"Expected -100, got {brake_speed}"

    # Test brake takes priority when both pressed
    state.right_trigger = 1.0  # Full gas
    state.left_trigger = 1.0  # Full brake
    cmd_both = translator.translate(state)
    both_speed = cmd_both.motor_a_speed

    print(f"Both pedals pressed (brake priority): {both_speed}")
    assert both_speed == -100, "Brake should take priority over gas"

    # Test partial gas
    state.left_trigger = 0.0  # No brake
    state.right_trigger = 0.5  # Half gas
    cmd_half_gas = translator.translate(state)
    print(f"Half gas: {cmd_half_gas.motor_a_speed}")
    # With quadratic curve (power=2.0), 0.5^2 = 0.25, so expect 25% speed
    assert 20 <= cmd_half_gas.motor_a_speed <= 30, f"Expected ~25, got {cmd_half_gas.motor_a_speed}"

    # Test partial brake
    state.right_trigger = 0.0  # No gas
    state.left_trigger = 0.5  # Half brake
    cmd_half_brake = translator.translate(state)
    print(f"Half brake: {cmd_half_brake.motor_a_speed}")
    # With quadratic curve, -0.5^2 = -0.25, so expect -25% speed
    assert -30 <= cmd_half_brake.motor_a_speed <= -20, f"Expected ~-25, got {cmd_half_brake.motor_a_speed}"

    print("✓ PASSED: Gas and brake pedals work correctly")
    return True


def test_control_modes():
    """Test different control modes (normal, turbo, slow)."""
    print("\n" + "="*60)
    print("TEST: Control Modes")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()
    state.right_trigger = 0.5  # Half gas

    # Test normal mode
    translator.set_mode(ControlMode.NORMAL)
    cmd_normal = translator.translate(state)
    print(f"Normal mode (0.5 gas): motor_a = {cmd_normal.motor_a_speed}")

    # Test turbo mode (more linear, less curve)
    translator.set_mode(ControlMode.TURBO)
    cmd_turbo = translator.translate(state)
    print(f"Turbo mode (0.5 gas): motor_a = {cmd_turbo.motor_a_speed}")

    # Turbo should give higher speed for same input (power=1.5 vs 2.0)
    assert cmd_turbo.motor_a_speed > cmd_normal.motor_a_speed, \
        "Turbo should be more responsive"

    # Test slow mode (lower max speed)
    translator.set_mode(ControlMode.SLOW)
    state.right_trigger = 1.0  # Full gas
    cmd_slow = translator.translate(state)
    print(f"Slow mode (full gas): motor_a = {cmd_slow.motor_a_speed}")

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
    """Test user-adjustable speed limit with bumpers."""
    print("\n" + "="*60)
    print("TEST: Speed Limit")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()
    state.right_trigger = 1.0  # Full gas

    # Test with default limit (100%)
    cmd_full = translator.translate(state)
    print(f"Default limit (100%): motor_a = {cmd_full.motor_a_speed}")
    assert cmd_full.motor_a_speed == 100

    # Reduce speed limit with left bumper (LB decreases)
    state.button_lb = True
    translator.translate(state)  # -10%
    state.button_lb = False
    translator.translate(state)
    state.button_lb = True
    translator.translate(state)  # -10%
    state.button_lb = False
    translator.translate(state)
    state.button_lb = True
    translator.translate(state)  # -10%
    state.button_lb = False
    translator.translate(state)

    # Should be at 70%
    cmd_limited = translator.translate(state)
    print(f"After 3x LB press (70% limit): motor_a = {cmd_limited.motor_a_speed}")
    assert cmd_limited.motor_a_speed == 70

    # Increase speed limit with right bumper (RB increases)
    state.button_rb = True
    translator.translate(state)  # +10%
    state.button_rb = False
    cmd_increased = translator.translate(state)
    print(f"After 1x RB press (80% limit): motor_a = {cmd_increased.motor_a_speed}")
    assert cmd_increased.motor_a_speed == 80

    # Test limit boundaries using direct method
    translator.adjust_speed_limit(-100)  # Should clamp to 0
    assert translator.max_speed_limit == 0

    translator.adjust_speed_limit(200)  # Should clamp to 100
    assert translator.max_speed_limit == 100

    print("✓ PASSED: Speed limit works correctly")
    return True


def test_direction_toggle():
    """Test direction toggle (B button)."""
    print("\n" + "="*60)
    print("TEST: Direction Toggle")
    print("="*60)

    translator = InputTranslator()

    # Initial direction should be forward (1)
    assert translator.direction == 1, "Initial direction should be forward (1)"
    print("Initial direction: FORWARD (1)")

    # Set up driving state with gas
    state = create_neutral_state()
    state.right_trigger = 1.0  # Full gas

    # First call in forward direction
    cmd1 = translator.translate(state)
    print(f"Forward: motor_a = {cmd1.motor_a_speed}")
    assert cmd1.motor_a_speed == 100, "Should be positive in forward"

    # Press B button to toggle to reverse
    state.button_b = True
    cmd2 = translator.translate(state)
    state.button_b = False
    translator.translate(state)  # Update button state

    # Check direction changed to reverse
    assert translator.direction == -1, "Direction should be reverse (-1)"
    print("After B press: REVERSE (-1)")

    # Test with gas in reverse
    cmd3 = translator.translate(state)
    print(f"Reverse: motor_a = {cmd3.motor_a_speed}")
    assert cmd3.motor_a_speed == -100, "Should be negative in reverse"

    # Press B button again to toggle back to forward
    state.button_b = True
    translator.translate(state)
    state.button_b = False
    translator.translate(state)

    # Check direction changed back to forward
    assert translator.direction == 1, "Direction should be forward (1) again"
    print("After second B press: FORWARD (1)")

    # Test with gas in forward again
    cmd4 = translator.translate(state)
    print(f"Forward again: motor_a = {cmd4.motor_a_speed}")
    assert cmd4.motor_a_speed == 100, "Should be positive in forward"

    # Verify edge detection (holding B doesn't toggle repeatedly)
    state.button_b = True
    translator.translate(state)  # First press toggles
    initial_direction = translator.direction
    translator.translate(state)  # Holding doesn't toggle
    assert translator.direction == initial_direction, "Holding B shouldn't toggle"

    print("✓ PASSED: Direction toggle works correctly")
    return True


def test_lights():
    """Test light control (A=lights on/off)."""
    print("\n" + "="*60)
    print("TEST: light Control")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()

    # Initial state (lights off)
    cmd = translator.translate(state)
    print(f"Initial light state: {cmd.lights}")
    assert cmd.lights == LIGHTS_OFF, f"Expected lights off ({LIGHTS_OFF}), got {cmd.lights}"

    # Press A button (toggle lights on)
    state.button_a = True
    cmd = translator.translate(state)
    print(f"After A press (lights OFF): {cmd.lights}")
    assert cmd.lights == LIGHTS_ON, f"Expected lights on ({LIGHTS_ON}), got {cmd.lights}"
    assert translator.lights_on, f"Expected lights_on=True, got {translator.lights_on}"

    # Release A button (lights stay on)
    state.button_a = False
    cmd = translator.translate(state)
    print(f"After A release (lights ON): {cmd.lights}")
    assert cmd.lights == LIGHTS_ON, f"Expected lights on ({LIGHTS_ON}), got {cmd.lights}"
    assert translator.lights_on, f"Expected lights_on=True, got {translator.lights_on}"

    # Press A again (toggle lights off)
    state.button_a = True
    cmd = translator.translate(state)
    print(f"After second A press (lights OFF): {cmd.lights}")
    assert cmd.lights == LIGHTS_OFF, f"Expected lights on ({LIGHTS_OFF}), got {cmd.lights}"
    assert not translator.lights_on, f"Expected lights_on=False, got {translator.lights_on}"

    # Release A again (lights stay off)
    state.button_a = False
    cmd = translator.translate(state)
    print(f"After second A release (lights OFF): {cmd.lights}")
    assert cmd.lights == LIGHTS_OFF, f"Expected lights off ({LIGHTS_OFF}), got {cmd.lights}"
    assert not translator.lights_on, f"Expected lights_on=False, got {translator.lights_on}"

    print("✓ PASSED: light control works correctly")
    return True


def test_button_edge_detection():
    """Test that button actions only trigger on press (not hold)."""
    print("\n" + "="*60)
    print("TEST: Button Edge Detection")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()

    # Press and hold RB (speed limit increase)
    initial_limit = translator.max_speed_limit
    state.button_rb = True

    cmd1 = translator.translate(state)
    limit_after_first = translator.max_speed_limit
    print(f"After first translate with RB held: {limit_after_first}")
    assert limit_after_first == initial_limit + 10, "Should increase by 10 on first press"

    # Keep holding RB (should NOT increase again)
    cmd2 = translator.translate(state)
    limit_after_second = translator.max_speed_limit
    print(f"After second translate with RB still held: {limit_after_second}")
    assert limit_after_second == limit_after_first, "Should not increase while held"

    # Release and press again (should increase)
    state.button_rb = False
    translator.translate(state)  # Update state

    state.button_rb = True
    cmd3 = translator.translate(state)
    limit_after_third = translator.max_speed_limit
    print(f"After releasing and pressing RB again: {limit_after_third}")
    assert limit_after_third == limit_after_second + 10, "Should increase by 10 on new press"

    print("✓ PASSED: Button edge detection works correctly")
    return True


def test_combined_inputs():
    """Test combining multiple inputs simultaneously."""
    print("\n" + "="*60)
    print("TEST: Combined Inputs")
    print("="*60)

    translator = InputTranslator()
    state = create_neutral_state()

    # Drive forward while turning right with gas pedal
    state.right_trigger = 0.7  # 70% gas
    state.right_stick_x = 0.5  # 50% right

    cmd = translator.translate(state)
    print(f"Combined input:")
    print(f"  Right trigger: 0.7 (gas)")
    print(f"  Right stick X: 0.5 (right)")
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
    assert 'lights_on' in status
    assert 'brake_lights_on' in status
    assert 'direction' in status

    # Check initial direction
    assert status['direction'] == 'forward', "Initial direction should be forward"

    # Change some settings
    translator.set_mode(ControlMode.TURBO)
    translator.adjust_speed_limit(-20)
    translator.lights_on = True
    translator.brake_lights_on = True
    translator.direction = -1  # Set to reverse

    status = translator.get_status()
    print(f"Updated status: {status}")

    assert status['mode'] == ControlMode.TURBO
    assert status['max_speed_limit'] == 80
    assert status['lights_on'] == True
    assert status['brake_lights_on'] == True
    assert status['direction'] == 'reverse', "Direction should be reverse"

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
        ("Gas and Brake", test_gas_and_brake),
        ("Control Modes", test_control_modes),
        ("Speed Limit", test_speed_limit),
        ("Direction Toggle", test_direction_toggle),
        ("LED Control", test_lights),
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

def gas_brake():
    """Quick test: gas and brake pedals"""
    return test_gas_and_brake()

def modes():
    """Quick test: control modes"""
    return test_control_modes()

def speed_limit():
    """Quick test: speed limit"""
    return test_speed_limit()

def direction():
    """Quick test: direction toggle"""
    return test_direction_toggle()

def leds():
    """Quick test: light control"""
    return test_lights()

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
