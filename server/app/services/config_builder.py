from __future__ import annotations
import json
import yaml
from yaml import SafeDumper
from ..models import Client, GlobalSettings
from ..models.client import FirewallRule


# Define custom YAML string classes at module level
class LiteralStr(str):
    """String subclass for literal block scalar (|) style in YAML."""
    pass

class QuotedPath(str):
    """String subclass that forces quoted output in YAML."""
    pass

# Register custom representers at module level
def _repr_literal_str(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

def _repr_quoted_path(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data), style='"')

SafeDumper.add_representer(LiteralStr, _repr_literal_str)
SafeDumper.add_representer(QuotedPath, _repr_quoted_path)


def _build_firewall_rule_dict(rule: FirewallRule) -> dict:
    """Convert a structured FirewallRule model into a dict for Nebula YAML."""
    rule_dict = {
        "port": rule.port,
        "proto": rule.proto,
    }
    
    # Add optional fields only if present
    if rule.host:
        rule_dict["host"] = rule.host
    if rule.cidr:
        rule_dict["cidr"] = rule.cidr
    if rule.local_cidr:
        rule_dict["local_cidr"] = rule.local_cidr
    if rule.ca_name:
        rule_dict["ca_name"] = rule.ca_name
    if rule.ca_sha:
        rule_dict["ca_sha"] = rule.ca_sha
    
    # Handle groups: single group vs multiple groups
    if hasattr(rule, "groups") and rule.groups:
        group_names = [g.name for g in rule.groups]
        if len(group_names) == 1:
            rule_dict["group"] = group_names[0]
        elif len(group_names) > 1:
            rule_dict["groups"] = group_names
    
    return rule_dict


def build_nebula_config(
    client: Client,
    client_ip_cidr: str,
    settings: GlobalSettings | None,
    static_host_map: dict[str, list[str]] | None = None,
    lighthouse_host_ips: list[str] | None = None,
    revoked_fingerprints: list[str] | None = None,
    key_path: str = "/var/lib/nebula/host.key",
    ca_path: str = "/etc/nebula/ca.crt",
    cert_path: str = "/etc/nebula/host.crt",
    inline_ca_pem: str | None = None,
    inline_cert_pem: str | None = None,
    os_type: str = "docker",
) -> str:
    """Build a Nebula config YAML.
    - client_ip_cidr must include the network mask (e.g., "10.100.0.10/16"), not /32.
    """

    lh_port = 4242
    lh_hosts = []
    if settings:
        lh_port = settings.lighthouse_port
        try:
            lh_hosts = json.loads(settings.lighthouse_hosts)
        except Exception:
            # Invalid JSON format; defaults to empty list
            lh_hosts = []

    # Start with defaults
    # Ensure multiline strings (PEM bundles) are emitted with a literal block scalar `|` as in Nebula docs
    class LiteralStr(str):
        pass

    def _repr_literal_str(dumper, data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')

    # Register representer for SafeDumper once (idempotent)
    try:
        SafeDumper.add_representer(LiteralStr, _repr_literal_str)
    except Exception:
        # Representer already registered; safe to ignore
        pass

    # Wrap inline PEMs so they are dumped using `|` block style
    ca_value = None
    cert_value = None
    if inline_ca_pem:
        # Normalize trailing newline; Nebula accepts concatenated PEMs one after the other
        ca_value = LiteralStr(inline_ca_pem.strip() + "\n")
    if inline_cert_pem:
        cert_value = LiteralStr(inline_cert_pem.strip() + "\n")

    # Wrapper class for paths that need quoting (contain spaces)
    class QuotedPath(str):
        """String subclass that forces quoted output in YAML."""
        pass

    def _repr_quoted_path(dumper, data):
        """Force double-quoted style for paths with spaces."""
        return dumper.represent_scalar('tag:yaml.org,2002:str', str(data), style='"')

    # Register representer for QuotedPath - must be registered each time to ensure it's active
    SafeDumper.add_representer(QuotedPath, _repr_quoted_path)

    # Helper to wrap paths with spaces
    def quote_path_if_needed(path: str) -> str | QuotedPath:
        """Return QuotedPath if path contains spaces, otherwise return as-is."""
        if isinstance(path, str) and ' ' in path:
            result = QuotedPath(path)
            print(f"[DEBUG] QuotedPath created for: {path} -> {type(result)}")
            return result
        return path

    cfg = {
        "pki": {
            # Nebula accepts file paths or inline PEMs. If inline provided, embed directly using literal block `|`.
            "ca": ca_value if ca_value is not None else quote_path_if_needed(ca_path),
            "cert": cert_value if cert_value is not None else quote_path_if_needed(cert_path),
            "key": quote_path_if_needed(key_path),
            # Distribute revocation blocklist
            "blocklist": revoked_fingerprints or [],
            # Force disconnect if a cert becomes expired/invalid
            "disconnect_invalid": True,
        },
        "static_host_map": static_host_map or {},
        "listen": {
            "host": "0.0.0.0",
            "port": lh_port,
        },
        "lighthouse": {
            "am_lighthouse": client.is_lighthouse,
            # Lighthouse clients should not list other lighthouses (only static_host_map)
            "hosts": [] if client.is_lighthouse else (lighthouse_host_ips or lh_hosts),
            # Interval for non-lighthouse clients to check in (critical for NAT traversal)
            "interval": 60,
        },
        "tun": {
            "disabled": False,
            # Do not specify a device name; Nebula will pick an appropriate one.
            # On Darwin, a fixed utunX can conflict if already in use.
            "drop_local_broadcast": False,
            "drop_multicast": False,
            "tx_queue": 500,
            "mtu": 1300,
        },
        "firewall": {
            "outbound": [
                {"port": "any", "proto": "any", "host": "any"}
            ],
            "inbound": [
                {"port": "any", "proto": "any", "host": "any"}
            ],
        },
    }

    # Windows-specific: explicitly set adapter name to avoid empty-name error on some systems
    if os_type == "windows":
        # Keep name short and ASCII to avoid Windows adapter name issues
        # Nebula/Wintun will create a Wintun adapter with this friendly name
        cfg["tun"]["dev"] = "Nebula"

    # macOS-specific: use system route table for proper TUN interface operation
    # Required for macOS 14+ (Sonoma, Sequoia, Tahoe) to properly create utun interfaces
    if os_type == "darwin" or os_type == "macos":
        cfg["tun"]["use_system_route_table"] = True

    # Optional punchy block - critical for NAT traversal
    try:
        if settings and getattr(settings, "punchy_enabled", False):
            cfg["punchy"] = {
                "punch": True,
                "punch_back": True,
                "respond": True,
                "delay": "1s",  # Delay before responding to punches (helps with misbehaving NATs)
                "respond_delay": "5s",  # Delay before punch_back response
            }
    except Exception:
        # If settings is None or missing attribute, ignore punchy
        pass

    # Add relay configuration for NAT traversal
    # Non-lighthouse clients can use lighthouses as relays if direct connection fails
    cfg["relay"] = {
        "am_relay": client.is_lighthouse,  # Lighthouses act as relays
        "use_relays": not client.is_lighthouse,  # Non-lighthouses can use relays
    }
    # If not a lighthouse and we have lighthouse IPs, list them as potential relays
    # Use list() to create a copy and avoid YAML aliases
    if not client.is_lighthouse and (lighthouse_host_ips or lh_hosts):
        cfg["relay"]["relays"] = list(lighthouse_host_ips or lh_hosts)

    # Build firewall rules from assigned rulesets
    try:
        if hasattr(client, "firewall_rulesets") and client.firewall_rulesets:
            inbound = []
            outbound = []
            for ruleset in client.firewall_rulesets:
                for rule in ruleset.rules:
                    rule_dict = _build_firewall_rule_dict(rule)
                    if rule.direction == "inbound":
                        inbound.append(rule_dict)
                    elif rule.direction == "outbound":
                        outbound.append(rule_dict)
            if inbound:
                cfg["firewall"]["inbound"] = inbound
            if outbound:
                cfg["firewall"]["outbound"] = outbound
    except Exception:
        # keep defaults on any error
        pass

    result_yaml = yaml.dump(cfg, Dumper=SafeDumper, sort_keys=False, default_flow_style=False)
    print(f"[DEBUG] YAML output key line: {[line for line in result_yaml.split(chr(10)) if 'key:' in line]}")
    return result_yaml
