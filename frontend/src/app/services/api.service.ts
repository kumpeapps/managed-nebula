import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { delay } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import { Client, Group, FirewallRuleset, IPPool, IPGroup, AvailableIP, CACertificate, User, ClientUpdateRequest, ClientCreateRequest, ClientCertificate, ClientConfigDownload, Settings, SettingsUpdate, DockerComposeTemplate, PlaceholdersResponse, Permission, VersionResponse, VersionStatusResponse, NebulaVersionsResponse, NebulaInstallationStatus, NebulaInstallationResponse } from '../models';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = '/api/v1';

  constructor(private http: HttpClient) {}

  /**
   * Apply test delay to API request if configured
   * Delay is set via environment.apiTestDelay (milliseconds)
   * Set to 0 to disable (default in production)
   */
  private applyDelay<T>(request: Observable<T>): Observable<T> {
    const testDelay = environment.apiTestDelay || 0;
    return testDelay > 0 ? request.pipe(delay(testDelay)) : request;
  }

  // Client endpoints
  getClients(): Observable<Client[]> {
    return this.applyDelay(this.http.get<Client[]>(`${this.apiUrl}/clients`, { withCredentials: true }));
  }

  getClient(id: number): Observable<Client> {
    return this.applyDelay(this.http.get<Client>(`${this.apiUrl}/clients/${id}`, { withCredentials: true }));
  }

  createClient(client: ClientCreateRequest): Observable<Client> {
    return this.applyDelay(this.http.post<Client>(`${this.apiUrl}/clients`, client, { withCredentials: true }));
  }

  updateClient(id: number, payload: ClientUpdateRequest): Observable<Client> {
    return this.applyDelay(this.http.put<Client>(`${this.apiUrl}/clients/${id}`, payload, { withCredentials: true }));
  }

  deleteClient(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/clients/${id}`, { withCredentials: true }));
  }

  // Alternate IP management
  addAlternateIP(clientId: number, payload: { ip_address: string, ip_version: string, pool_id: number | null, ip_group_id: number | null }): Observable<any> {
    return this.applyDelay(this.http.post<any>(`${this.apiUrl}/clients/${clientId}/alternate-ips`, payload, { withCredentials: true }));
  }

  deleteAlternateIP(clientId: number, ipAssignmentId: number): Observable<any> {
    return this.applyDelay(this.http.delete<any>(`${this.apiUrl}/clients/${clientId}/alternate-ips/${ipAssignmentId}`, { withCredentials: true }));
  }

  // Client ownership endpoint
  updateClientOwner(clientId: number, ownerId: number): Observable<Client> {
    return this.applyDelay(this.http.put<Client>(`${this.apiUrl}/clients/${clientId}/owner`, { owner_user_id: ownerId }, { withCredentials: true }));
  }

  // Client permission endpoints
  getClientPermissions(clientId: number): Observable<any[]> {
    return this.applyDelay(this.http.get<any[]>(`${this.apiUrl}/clients/${clientId}/permissions`, { withCredentials: true }));
  }

  grantClientPermission(clientId: number, userId: number, permissions: { can_view: boolean; can_update: boolean; can_download_config: boolean; can_view_token: boolean; can_download_docker_config: boolean }): Observable<any> {
    return this.applyDelay(this.http.post<any>(`${this.apiUrl}/clients/${clientId}/permissions`, { user_id: userId, ...permissions }, { withCredentials: true }));
  }

  revokeClientPermission(clientId: number, permissionId: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/clients/${clientId}/permissions/${permissionId}`, { withCredentials: true }));
  }

  // Client certificate endpoints
  getClientCertificates(clientId: number): Observable<ClientCertificate[]> {
    return this.applyDelay(this.http.get<ClientCertificate[]>(`${this.apiUrl}/clients/${clientId}/certificates`, { withCredentials: true }));
  }

  reissueClientCertificate(clientId: number): Observable<{ status: string; message: string }> {
    return this.applyDelay(this.http.post<{ status: string; message: string }>(`${this.apiUrl}/clients/${clientId}/certificates/reissue`, {}, { withCredentials: true }));
  }

  revokeClientCertificate(clientId: number, certId: number): Observable<{ status: string; certificate_id: number; revoked_at: string }> {
    return this.applyDelay(this.http.post<{ status: string; certificate_id: number; revoked_at: string }>(`${this.apiUrl}/clients/${clientId}/certificates/${certId}/revoke`, {}, { withCredentials: true }));
  }

  // Client token endpoints
  reissueClientToken(clientId: number): Observable<{ id: number; token: string; client_id: number; created_at: string; old_token_id: number }> {
    return this.applyDelay(this.http.post<{ id: number; token: string; client_id: number; created_at: string; old_token_id: number }>(`${this.apiUrl}/clients/${clientId}/token/reissue`, {}, { withCredentials: true }));
  }

  downloadClientConfig(clientId: number): Observable<ClientConfigDownload> {
    return this.applyDelay(this.http.get<ClientConfigDownload>(`${this.apiUrl}/clients/${clientId}/config`, { withCredentials: true }));
  }

  downloadClientDockerCompose(clientId: number): Observable<Blob> {
    return this.applyDelay(this.http.get(`${this.apiUrl}/clients/${clientId}/docker-compose`, { 
      withCredentials: true,
      responseType: 'blob'
    }));
  }

  // Group endpoints
  getGroups(): Observable<Group[]> {
    return this.applyDelay(this.http.get<Group[]>(`${this.apiUrl}/groups`, { withCredentials: true }));
  }

  getGroup(id: number): Observable<Group> {
    return this.applyDelay(this.http.get<Group>(`${this.apiUrl}/groups/${id}`, { withCredentials: true }));
  }

  createGroup(group: Partial<Group>): Observable<Group> {
    return this.applyDelay(this.http.post<Group>(`${this.apiUrl}/groups`, group, { withCredentials: true }));
  }

  updateGroup(id: number, group: Partial<Group>): Observable<Group> {
    return this.applyDelay(this.http.put<Group>(`${this.apiUrl}/groups/${id}`, group, { withCredentials: true }));
  }

  deleteGroup(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/groups/${id}`, { withCredentials: true }));
  }

  // Group permission endpoints
  getGroupPermissions(groupId: number): Observable<any[]> {
    return this.applyDelay(this.http.get<any[]>(`${this.apiUrl}/groups/${groupId}/permissions`, { withCredentials: true }));
  }

  grantGroupPermission(groupId: number, permission: { user_id?: number; user_group_id?: number; can_add_to_client: boolean; can_remove_from_client: boolean; can_create_subgroup: boolean }): Observable<any> {
    return this.applyDelay(this.http.post<any>(`${this.apiUrl}/groups/${groupId}/permissions`, permission, { withCredentials: true }));
  }

  revokeGroupPermission(groupId: number, permissionId: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/groups/${groupId}/permissions/${permissionId}`, { withCredentials: true }));
  }

  // User group endpoints
  getUserGroups(): Observable<any[]> {
    return this.applyDelay(this.http.get<any[]>(`${this.apiUrl}/user-groups`, { withCredentials: true }));
  }

  getUserGroup(id: number): Observable<any> {
    return this.applyDelay(this.http.get<any>(`${this.apiUrl}/user-groups/${id}`, { withCredentials: true }));
  }

  createUserGroup(userGroup: { name: string; description?: string }): Observable<any> {
    return this.applyDelay(this.http.post<any>(`${this.apiUrl}/user-groups`, userGroup, { withCredentials: true }));
  }

  updateUserGroup(id: number, userGroup: { name?: string; description?: string }): Observable<any> {
    return this.applyDelay(this.http.put<any>(`${this.apiUrl}/user-groups/${id}`, userGroup, { withCredentials: true }));
  }

  deleteUserGroup(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/user-groups/${id}`, { withCredentials: true }));
  }

  getUserGroupMembers(userGroupId: number): Observable<any[]> {
    return this.applyDelay(this.http.get<any[]>(`${this.apiUrl}/user-groups/${userGroupId}/members`, { withCredentials: true }));
  }

  addUserGroupMembers(userGroupId: number, userIds: number[]): Observable<any> {
    return this.applyDelay(this.http.post<any>(`${this.apiUrl}/user-groups/${userGroupId}/members`, { user_ids: userIds }, { withCredentials: true }));
  }

  removeUserGroupMember(userGroupId: number, userId: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/user-groups/${userGroupId}/members/${userId}`, { withCredentials: true }));
  }

  // Firewall rule endpoints
  getFirewallRulesets(): Observable<FirewallRuleset[]> {
    return this.applyDelay(this.http.get<FirewallRuleset[]>(`${this.apiUrl}/firewall-rulesets`, { withCredentials: true }));
  }

  getFirewallRuleset(id: number): Observable<FirewallRuleset> {
    return this.applyDelay(this.http.get<FirewallRuleset>(`${this.apiUrl}/firewall-rulesets/${id}`, { withCredentials: true }));
  }

  createFirewallRuleset(ruleset: any): Observable<FirewallRuleset> {
    return this.applyDelay(this.http.post<FirewallRuleset>(`${this.apiUrl}/firewall-rulesets`, ruleset, { withCredentials: true }));
  }

  updateFirewallRuleset(id: number, ruleset: any): Observable<FirewallRuleset> {
    return this.applyDelay(this.http.put<FirewallRuleset>(`${this.apiUrl}/firewall-rulesets/${id}`, ruleset, { withCredentials: true }));
  }

  deleteFirewallRuleset(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/firewall-rulesets/${id}`, { withCredentials: true }));
  }

  // IP Pool endpoints
  getIPPools(): Observable<IPPool[]> {
    return this.applyDelay(this.http.get<IPPool[]>(`${this.apiUrl}/ip-pools`, { withCredentials: true }));
  }

  getIPPool(id: number): Observable<IPPool> {
    return this.applyDelay(this.http.get<IPPool>(`${this.apiUrl}/ip-pools/${id}`, { withCredentials: true }));
  }

  createIPPool(pool: { cidr: string; description?: string }): Observable<IPPool> {
    return this.applyDelay(this.http.post<IPPool>(`${this.apiUrl}/ip-pools`, pool, { withCredentials: true }));
  }

  updateIPPool(id: number, pool: { cidr?: string; description?: string }): Observable<IPPool> {
    return this.applyDelay(this.http.put<IPPool>(`${this.apiUrl}/ip-pools/${id}`, pool, { withCredentials: true }));
  }

  deleteIPPool(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/ip-pools/${id}`, { withCredentials: true }));
  }

  getPoolClients(poolId: number): Observable<Client[]> {
    return this.applyDelay(this.http.get<Client[]>(`${this.apiUrl}/ip-pools/${poolId}/clients`, { withCredentials: true }));
  }

  getAvailableIPs(poolId: number, ipGroupId?: number): Observable<AvailableIP[]> {
    let params = new HttpParams();
    if (ipGroupId) {
      params = params.set('ip_group_id', ipGroupId.toString());
    }
    return this.applyDelay(this.http.get<AvailableIP[]>(`${this.apiUrl}/ip-pools/${poolId}/available-ips`, { params, withCredentials: true }));
  }

  // IP Group endpoints
  getIPGroups(poolId?: number): Observable<IPGroup[]> {
    let params = new HttpParams();
    if (poolId) {
      params = params.set('pool_id', poolId.toString());
    }
    return this.applyDelay(this.http.get<IPGroup[]>(`${this.apiUrl}/ip-groups`, { params, withCredentials: true }));
  }

  getIPGroup(id: number): Observable<IPGroup> {
    return this.applyDelay(this.http.get<IPGroup>(`${this.apiUrl}/ip-groups/${id}`, { withCredentials: true }));
  }

  createIPGroup(group: { pool_id: number; name: string; start_ip: string; end_ip: string }): Observable<IPGroup> {
    return this.applyDelay(this.http.post<IPGroup>(`${this.apiUrl}/ip-groups`, group, { withCredentials: true }));
  }

  updateIPGroup(id: number, group: { name?: string; start_ip?: string; end_ip?: string }): Observable<IPGroup> {
    return this.applyDelay(this.http.put<IPGroup>(`${this.apiUrl}/ip-groups/${id}`, group, { withCredentials: true }));
  }

  deleteIPGroup(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/ip-groups/${id}`, { withCredentials: true }));
  }

  getGroupClients(groupId: number): Observable<Client[]> {
    return this.applyDelay(this.http.get<Client[]>(`${this.apiUrl}/ip-groups/${groupId}/clients`, { withCredentials: true }));
  }

  // CA endpoints
  getCACertificates(): Observable<CACertificate[]> {
    return this.applyDelay(this.http.get<CACertificate[]>(`${this.apiUrl}/ca`, { withCredentials: true }));
  }

  createCA(payload: { name: string; validity_months?: number }): Observable<CACertificate> {
    return this.applyDelay(this.http.post<CACertificate>(`${this.apiUrl}/ca/create`, payload, { withCredentials: true }));
  }

  importCA(payload: { name: string; pem_cert: string; pem_key?: string }): Observable<CACertificate> {
    return this.applyDelay(this.http.post<CACertificate>(`${this.apiUrl}/ca/import`, payload, { withCredentials: true }));
  }

  deleteCA(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/ca/${id}`, { withCredentials: true }));
  }

  setSigningCA(id: number): Observable<CACertificate> {
    return this.applyDelay(this.http.post<CACertificate>(`${this.apiUrl}/ca/${id}/set-signing`, {}, { withCredentials: true }));
  }

  // User endpoints
  getUsers(): Observable<User[]> {
    return this.applyDelay(this.http.get<User[]>(`${this.apiUrl}/users`, { withCredentials: true }));
  }

  getUser(id: number): Observable<User> {
    return this.applyDelay(this.http.get<User>(`${this.apiUrl}/users/${id}`, { withCredentials: true }));
  }

  createUser(user: Partial<User> & { password: string }): Observable<User> {
    return this.applyDelay(this.http.post<User>(`${this.apiUrl}/users`, user, { withCredentials: true }));
  }

  updateUser(id: number, user: Partial<User>): Observable<User> {
    return this.applyDelay(this.http.put<User>(`${this.apiUrl}/users/${id}`, user, { withCredentials: true }));
  }

  deleteUser(id: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/users/${id}`, { withCredentials: true }));
  }

  // Settings endpoints
  getSettings(): Observable<Settings> {
    return this.applyDelay(this.http.get<Settings>(`${this.apiUrl}/settings`, { withCredentials: true }));
  }

  updateSettings(settings: SettingsUpdate): Observable<Settings> {
    return this.applyDelay(this.http.put<Settings>(`${this.apiUrl}/settings`, settings, { withCredentials: true }));
  }

  // Self-service: update current user (email/password)
  updateMe(payload: { email?: string; current_password: string; new_password?: string }): Observable<User> {
    return this.applyDelay(this.http.put<User>(`${this.apiUrl}/auth/me`, payload, { withCredentials: true }));
  }

  // Docker compose template endpoints
  getDockerComposeTemplate(): Observable<DockerComposeTemplate> {
    return this.applyDelay(this.http.get<DockerComposeTemplate>(`${this.apiUrl}/settings/docker-compose-template`, { withCredentials: true }));
  }

  updateDockerComposeTemplate(template: string): Observable<DockerComposeTemplate> {
    return this.applyDelay(this.http.put<DockerComposeTemplate>(`${this.apiUrl}/settings/docker-compose-template`, { template }, { withCredentials: true }));
  }

  getPlaceholders(): Observable<PlaceholdersResponse> {
    return this.applyDelay(this.http.get<PlaceholdersResponse>(`${this.apiUrl}/settings/placeholders`, { withCredentials: true }));
  }

  // Nebula version management endpoints
  getNebulaVersions(): Observable<NebulaVersionsResponse> {
    return this.applyDelay(this.http.get<NebulaVersionsResponse>(`${this.apiUrl}/nebula/versions`, { withCredentials: true }));
  }

  getNebulaInstallationStatus(): Observable<NebulaInstallationStatus> {
    return this.applyDelay(this.http.get<NebulaInstallationStatus>(`${this.apiUrl}/nebula/installation-status`, { withCredentials: true }));
  }

  installNebulaVersion(): Observable<NebulaInstallationResponse> {
    return this.applyDelay(this.http.post<NebulaInstallationResponse>(`${this.apiUrl}/nebula/install`, {}, { withCredentials: true }));
  }

  getVersionCacheStatus(): Observable<any> {
    return this.applyDelay(this.http.get<any>(`${this.apiUrl}/settings/version-cache`, { withCredentials: true }));
  }

  refreshVersionCache(): Observable<any> {
    return this.applyDelay(this.http.post<any>(`${this.apiUrl}/settings/version-cache/refresh`, {}, { withCredentials: true }));
  }

  // Permissions endpoints
  getPermissions(): Observable<Permission[]> {
    return this.applyDelay(this.http.get<Permission[]>(`${this.apiUrl}/permissions`, { withCredentials: true }));
  }

  // User Group Permissions endpoints
  getUserGroupPermissions(groupId: number): Observable<Permission[]> {
    return this.applyDelay(this.http.get<Permission[]>(`${this.apiUrl}/user-groups/${groupId}/permissions`, { withCredentials: true }));
  }

  grantPermissionToUserGroup(groupId: number, permissionId: number): Observable<void> {
    return this.applyDelay(this.http.post<void>(`${this.apiUrl}/user-groups/${groupId}/permissions`, { permission_id: permissionId }, { withCredentials: true }));
  }

  revokePermissionFromUserGroup(groupId: number, permissionId: number): Observable<void> {
    return this.applyDelay(this.http.delete<void>(`${this.apiUrl}/user-groups/${groupId}/permissions/${permissionId}`, { withCredentials: true }));
  }

  // Version endpoint
  getVersion(): Observable<VersionResponse> {
    return this.applyDelay(this.http.get<VersionResponse>(`${this.apiUrl}/version`, { withCredentials: true }));
  }

  // Version status endpoint
  getVersionStatus(): Observable<VersionStatusResponse> {
    return this.applyDelay(this.http.get<VersionStatusResponse>(`${this.apiUrl}/version-status`, { withCredentials: true }));
  }
}
