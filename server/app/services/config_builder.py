from __future__ import annotations
import json
import yaml
from yaml import SafeDumper
from ..models import Client, GlobalSettings
from ..models.client import FirewallRule


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

    cfg = {
        "pki": {
            # Nebula accepts file paths or inline PEMs. If inline provided, embed directly using literal block `|`.
            "ca": ca_value if ca_value is not None else ca_path,
            "cert": cert_value if cert_value is not None else cert_path,
            "key": key_path,
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

    return yaml.safe_dump(cfg, sort_keys=False)
