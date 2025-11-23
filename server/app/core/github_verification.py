"""GitHub webhook signature verification utilities."""
import hmac
import hashlib


def verify_github_signature(
    payload: bytes,
    signature_header: str,
    webhook_secret: str
) -> bool:
    """Verify GitHub webhook signature using HMAC SHA-256.
    
    GitHub sends a X-Hub-Signature-256 header with format: "sha256=<hex_digest>"
    We compute the expected signature and compare it securely.
    
    Args:
        payload: Raw request body as bytes
        signature_header: Value of X-Hub-Signature-256 header
        webhook_secret: Configured webhook secret
        
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    
    if not webhook_secret:
        # If no secret is configured, verification fails
        return False
    
    # Compute expected signature
    expected_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Extract received signature (remove "sha256=" prefix)
    received_signature = signature_header.split("=", 1)[1]
    
    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, received_signature)


def get_github_pattern_regex(prefix: str) -> str:
    """Generate GitHub secret scanning regex pattern for given prefix.
    
    Args:
        prefix: Token prefix (e.g., 'mnebula_')
        
    Returns:
        Regex pattern string for GitHub secret scanning
    """
    # Escape any special regex characters in prefix (though we validate it doesn't have any)
    # Pattern: prefix followed by exactly 32 lowercase alphanumeric characters
    return f"{prefix}[a-z0-9]{{32}}"
