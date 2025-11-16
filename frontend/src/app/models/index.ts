// TypeScript interfaces for Managed Nebula API models

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  groups: { id: number; name: string }[];
  role?: { id: number; name: string } | null; // legacy
}

export interface UserRef {
  id: number;
  email: string;
}

// Backend ClientResponse mapping
export interface FirewallRulesetRef {
  id: number;
  name: string;
}

export interface Client {
  id: number;
  name: string; // backend field 'name'
  ip_address: string | null;
  pool_id?: number | null;
  ip_group_id?: number | null;
  is_lighthouse: boolean;
  public_ip: string | null;
  is_blocked: boolean;
  created_at: string;
  config_last_changed_at: string | null;
  last_config_download_at: string | null;
  groups: GroupRef[];
  firewall_rulesets: FirewallRulesetRef[];
  token?: string | null; // only for admins
  owner?: UserRef | null; // owner information
}

export interface ClientPermission {
  id: number;
  user: UserRef;
  can_view: boolean;
  can_update: boolean;
  can_download_config: boolean;
  can_view_token: boolean;
  can_download_docker_config: boolean;
}

export interface GroupRef {
  id: number;
  name: string;
}

export interface Group {
  id: number;
  name: string;
  owner?: UserRef | null;
  created_at: string;
  client_count: number;
  parent_name?: string | null;
  is_subgroup: boolean;
}

export interface GroupPermission {
  id: number;
  user?: UserRef | null;
  user_group?: { id: number; name: string } | null;
  can_add_to_client: boolean;
  can_remove_from_client: boolean;
  can_create_subgroup: boolean;
}

export interface UserGroup {
  id: number;
  name: string;
  description?: string | null;
  owner?: UserRef | null;
  created_at: string;
  member_count: number;
}

export interface UserGroupMembership {
  id: number;
  user: UserRef;
  added_at: string;
}

export interface FirewallRule {
  id: number;
  direction: string; // 'inbound' or 'outbound'
  port: string; // 'any', '80', '200-901', 'fragment'
  proto: string; // 'any', 'tcp', 'udp', 'icmp'
  host?: string | null;
  cidr?: string | null;
  local_cidr?: string | null;
  ca_name?: string | null;
  ca_sha?: string | null;
  groups: GroupRef[];
}

export interface FirewallRuleset {
  id: number;
  name: string;
  description?: string | null;
  rules: FirewallRule[];
  client_count: number;
}

export interface IPPool {
  id: number;
  cidr: string;
  description?: string | null;
  allocated_count: number;
}

export interface IPGroup {
  id: number;
  pool_id: number;
  name: string;
  start_ip: string;
  end_ip: string;
  client_count: number;
}

export interface AvailableIP {
  ip_address: string;
  is_available: boolean;
}

export interface CACertificate {
  id: number;
  name: string;
  not_before: string;
  not_after: string;
  is_active: boolean;
  is_previous: boolean;
  can_sign: boolean;
  include_in_config: boolean;
  created_at: string;
  status: 'current' | 'previous' | 'expired' | 'inactive';
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface ApiError {
  detail: string;
}

export interface ClientConfig {
  config: string;
  client_cert_pem: string;
  ca_chain_pems: string[];
  cert_not_before: string;
  cert_not_after: string;
  lighthouse: boolean;
  key_path: string;
}

export interface ClientCertificate {
  id: number;
  client_id: number;
  not_before: string;
  not_after: string;
  created_at: string;
  fingerprint: string | null;
  issued_for_ip_cidr: string | null;
  issued_for_groups_hash: string | null;
  revoked: boolean;
  revoked_at: string | null;
}

export interface ClientConfigDownload {
  config_yaml: string;
  client_cert_pem: string;
  ca_chain_pems: string[];
}

// Update request payload matching backend ClientUpdate schema
export interface ClientUpdateRequest {
  name?: string;
  is_lighthouse?: boolean;
  public_ip?: string;
  is_blocked?: boolean;
  group_ids?: number[];
  firewall_ruleset_ids?: number[];
  ip_address?: string;
  pool_id?: number;
  ip_group_id?: number;
}

// Settings interfaces
export interface Settings {
  punchy_enabled: boolean;
  client_docker_image: string;
  server_url: string;
  docker_compose_template: string;
  externally_managed_users: boolean;
}

export interface SettingsUpdate {
  punchy_enabled?: boolean;
  client_docker_image?: string;
  server_url?: string;
  docker_compose_template?: string;
}

export interface DockerComposeTemplate {
  template: string;
}

export interface Placeholder {
  name: string;
  description: string;
  example: string;
}

export interface PlaceholdersResponse {
  placeholders: Placeholder[];
}

// Permission model
export interface Permission {
  id: number;
  resource: string;
  action: string;
  description: string;
}

// Client create request payload
export interface ClientCreateRequest {
  name: string;
  is_lighthouse: boolean;
  public_ip?: string | null;
  is_blocked: boolean;
  group_ids: number[];
  firewall_ruleset_ids: number[];
  pool_id?: number | null;
  ip_group_id?: number | null;
  ip_address?: string | null;
}
