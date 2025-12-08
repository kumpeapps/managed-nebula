#!/usr/bin/env python3
"""
Quick validation test for hybrid certificate constraints.
This test verifies the IPv4 validation logic without requiring a full database.
"""

def validate_hybrid_ip(ip_address: str) -> tuple[bool, str]:
    """
    Validate that an IP address meets hybrid certificate constraints.
    
    Args:
        ip_address: IP address string to validate
        
    Returns:
        (is_valid, error_message) - error_message is empty string if valid
    """
    if not ip_address:
        return False, "Hybrid mode requires a client IP address"
    
    # Check for multiple IPs (comma-separated)
    if ',' in ip_address:
        return False, "Hybrid mode only supports single IPv4 addresses (no multiple IPs)"
    
    # Check for IPv6 (contains colon)
    if ':' in ip_address:
        return False, "Hybrid mode only supports single IPv4 addresses (no IPv6)"
    
    # Validate IPv4 format
    import ipaddress
    try:
        ip_obj = ipaddress.ip_address(ip_address.split('/')[0])  # Strip CIDR if present
        if ip_obj.version != 4:
            return False, "Hybrid certificates only support IPv4 addresses"
    except ValueError as e:
        return False, f"Invalid IP address for hybrid certificate: {e}"
    
    return True, ""


def test_hybrid_validation():
    """Test hybrid certificate IP validation."""
    
    test_cases = [
        # (ip, should_pass, description)
        ("10.1.1.1", True, "Valid single IPv4"),
        ("192.168.1.100", True, "Valid single IPv4"),
        ("10.1.1.1,10.1.1.2", False, "Multiple IPs (comma-separated)"),
        ("2001:db8::1", False, "IPv6 address"),
        ("fe80::1", False, "IPv6 link-local"),
        ("", False, "Empty IP"),
        ("invalid", False, "Invalid IP format"),
        ("256.1.1.1", False, "Invalid IPv4 (out of range)"),
    ]
    
    print("Testing hybrid certificate IP validation:\n")
    passed = 0
    failed = 0
    
    for ip, should_pass, description in test_cases:
        is_valid, error_msg = validate_hybrid_ip(ip)
        
        if is_valid == should_pass:
            status = "✓ PASS"
            passed += 1
        else:
            status = "✗ FAIL"
            failed += 1
        
        result = "Valid" if is_valid else f"Invalid: {error_msg}"
        print(f"{status} | {description:40s} | IP: {ip:20s} | {result}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*80}")
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = test_hybrid_validation()
    sys.exit(0 if success else 1)
