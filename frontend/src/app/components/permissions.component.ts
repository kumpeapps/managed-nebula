import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';

interface Permission {
  id: number;
  resource: string;
  action: string;
  description: string;
}

interface UserGroup {
  id: number;
  name: string;
  description: string;
  is_admin: boolean;
  member_count: number;
}

interface ResourceGroup {
  resource: string;
  permissions: Permission[];
}

interface GroupPermissionStatus {
  [groupId: number]: {
    [permissionId: number]: boolean;
  };
}

@Component({
  selector: 'app-permissions',
  standalone: false,
  template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <h2 class="title">Permissions Management</h2>
      
      <div *ngIf="loading" class="loading">
        <p>Loading permissions...</p>
      </div>
      
      <div *ngIf="error" class="error">
        {{ error }}
      </div>
      
      <div *ngIf="!loading && !error" class="permissions-grid">
        <!-- Left sidebar: header + list grouped together so grid places them in one column -->
        <div class="sidebar">
          <div class="groups-header">
            <h3>User Groups</h3>
            <button class="btn btn-secondary" (click)="loadData()">
              <i class="fas fa-sync"></i> Refresh
            </button>
          </div>
          
          <div class="groups-list">
            <div *ngFor="let group of userGroups" 
                 class="group-card"
                 [class.selected]="selectedGroupId === group.id"
                 (click)="selectGroup(group.id)">
              <div class="group-name">
                {{ group.name }}
                <span *ngIf="group.is_admin" class="badge badge-admin">ADMIN</span>
              </div>
              <div class="group-description">{{ group.description }}</div>
              <div class="group-stats">
                {{ group.member_count }} member(s)
              </div>
            </div>
          </div>
        </div>
        
        <!-- Right main area: full-height permissions panel -->
        <div *ngIf="selectedGroupId" class="permissions-panel">
          <h3>Permissions for {{ selectedGroup?.name }}</h3>
          
          <div *ngIf="selectedGroup?.is_admin" class="admin-notice">
            <i class="fas fa-crown"></i> This is an admin group with all permissions
          </div>
          
          <div *ngFor="let resourceGroup of groupedPermissions" class="resource-section">
            <h4 class="resource-title">{{ formatResource(resourceGroup.resource) }}</h4>
            
            <table class="permissions-table">
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Description</th>
                  <th>Granted</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let perm of resourceGroup.permissions">
                  <td>
                    <code>{{ perm.action }}</code>
                  </td>
                  <td>{{ perm.description }}</td>
                  <td>
                    <label class="switch">
                      <input type="checkbox" 
                             [checked]="hasPermission(perm.id)"
                             [disabled]="selectedGroup?.is_admin || updating"
                             (change)="togglePermission(perm.id, $event)">
                      <span class="slider"></span>
                    </label>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        
        <div *ngIf="!selectedGroupId" class="no-selection">
          <i class="fas fa-hand-pointer"></i>
          <p>Select a user group to manage its permissions</p>
        </div>
      </div>
    </div>
    </div>
  `,
  styles: [`
    .container {
      padding: 20px;
      max-width: 1400px;
      margin: 0 auto;
    }

    .title {
      margin-bottom: 20px;
      color: #333;
    }

    .loading, .error {
      text-align: center;
      padding: 40px;
      font-size: 16px;
    }

    .error {
      color: #d32f2f;
      background: #ffebee;
      border-radius: 4px;
    }

    .permissions-grid {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 20px;
      align-items: start;
      height: calc(100vh - 150px);
    }

    .sidebar {
      display: flex;
      flex-direction: column;
      min-height: 0; /* allow children to size with overflow */
      height: 100%;
    }

    .groups-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
    }

    .groups-header h3 {
      margin: 0;
      font-size: 18px;
    }

    .groups-list {
      flex: 1;
      overflow-y: auto;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 10px;
      background: #f5f5f5;
      min-height: 0; /* enable proper scrolling in flex container */
    }

    .group-card {
      background: white;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 12px;
      margin-bottom: 10px;
      cursor: pointer;
      transition: all 0.2s;
    }

    .group-card:hover {
      border-color: #2196F3;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .group-card.selected {
      border-color: #2196F3;
      background: #e3f2fd;
    }

    .group-name {
      font-weight: 600;
      margin-bottom: 5px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .group-description {
      font-size: 13px;
      color: #666;
      margin-bottom: 5px;
    }

    .group-stats {
      font-size: 12px;
      color: #999;
    }

    .badge-admin {
      background: #ff9800;
      color: white;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 11px;
      font-weight: bold;
    }

    .permissions-panel {
      overflow-y: auto;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 20px;
      background: white;
      height: calc(100vh - 200px);
      min-height: 400px;
    }

    .permissions-panel h3 {
      margin-top: 0;
      margin-bottom: 20px;
    }

    .admin-notice {
      background: #fff3e0;
      border: 1px solid #ff9800;
      border-radius: 4px;
      padding: 12px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .admin-notice i {
      color: #ff9800;
    }

    .resource-section {
      margin-bottom: 30px;
    }

    .resource-title {
      background: #f5f5f5;
      padding: 10px 15px;
      border-radius: 4px;
      margin-bottom: 10px;
      font-size: 16px;
      color: #555;
    }

    .permissions-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 20px;
    }

    .permissions-table th {
      background: #fafafa;
      padding: 10px;
      text-align: left;
      border-bottom: 2px solid #ddd;
      font-weight: 600;
    }

    .permissions-table td {
      padding: 10px;
      border-bottom: 1px solid #eee;
    }

    .permissions-table code {
      background: #f5f5f5;
      padding: 2px 6px;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
      font-size: 13px;
    }

    .switch {
      position: relative;
      display: inline-block;
      width: 50px;
      height: 24px;
    }

    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }

    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #ccc;
      transition: .4s;
      border-radius: 24px;
    }

    .slider:before {
      position: absolute;
      content: "";
      height: 18px;
      width: 18px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: .4s;
      border-radius: 50%;
    }

    input:checked + .slider {
      background-color: #4CAF50;
    }

    input:disabled + .slider {
      background-color: #ddd;
      cursor: not-allowed;
    }

    input:checked + .slider:before {
      transform: translateX(26px);
    }

    .no-selection {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      color: #999;
      font-size: 18px;
      height: 100%;
    }

    .no-selection i {
      font-size: 48px;
      margin-bottom: 20px;
      color: #ddd;
    }

    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .btn-secondary {
      background: #6c757d;
      color: white;
    }

    .btn-secondary:hover {
      background: #5a6268;
    }
  `]
})
export class PermissionsComponent implements OnInit {
  permissions: Permission[] = [];
  userGroups: UserGroup[] = [];
  groupedPermissions: ResourceGroup[] = [];
  selectedGroupId: number | null = null;
  selectedGroup: UserGroup | null = null;
  groupPermissions: GroupPermissionStatus = {};
  loading = false;
  updating = false;
  error: string | null = null;
  currentUser: any = null;

  constructor(
    private apiService: ApiService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    this.loadData();
  }

  async loadData(): Promise<void> {
    this.loading = true;
    this.error = null;

    try {
      // Load all permissions and user groups in parallel
      const [perms, groups] = await Promise.all([
        this.apiService.getPermissions().toPromise(),
        this.apiService.getUserGroups().toPromise()
      ]);

      this.permissions = perms || [];
      this.userGroups = groups || [];
      this.groupPermissionsByResource();

      // If a group is selected, reload its permissions
      if (this.selectedGroupId) {
        await this.loadGroupPermissions(this.selectedGroupId);
      }
    } catch (err: any) {
      console.error('Error loading permissions:', err);
      this.error = err.error?.detail || 'Failed to load permissions';
    } finally {
      this.loading = false;
    }
  }

  groupPermissionsByResource(): void {
    const resourceMap = new Map<string, Permission[]>();

    for (const perm of this.permissions) {
      if (!resourceMap.has(perm.resource)) {
        resourceMap.set(perm.resource, []);
      }
      resourceMap.get(perm.resource)!.push(perm);
    }

    // Sort permissions within each resource by action
    this.groupedPermissions = Array.from(resourceMap.entries()).map(([resource, perms]) => ({
      resource,
      permissions: perms.sort((a, b) => {
        const actionOrder = ['read', 'create', 'update', 'delete', 'download', 'manage_members', 'manage_permissions', 'docker_compose'];
        const aIdx = actionOrder.indexOf(a.action);
        const bIdx = actionOrder.indexOf(b.action);
        if (aIdx !== -1 && bIdx !== -1) return aIdx - bIdx;
        if (aIdx !== -1) return -1;
        if (bIdx !== -1) return 1;
        return a.action.localeCompare(b.action);
      })
    })).sort((a, b) => a.resource.localeCompare(b.resource));
  }

  async selectGroup(groupId: number): Promise<void> {
    this.selectedGroupId = groupId;
    this.selectedGroup = this.userGroups.find(g => g.id === groupId) || null;
    await this.loadGroupPermissions(groupId);
  }

  async loadGroupPermissions(groupId: number): Promise<void> {
    try {
      const perms = await this.apiService.getUserGroupPermissions(groupId).toPromise();
      
      // Build permission status map
      if (!this.groupPermissions[groupId]) {
        this.groupPermissions[groupId] = {};
      }

      // Clear existing status
      for (const perm of this.permissions) {
        this.groupPermissions[groupId][perm.id] = false;
      }

      // Set granted permissions
      if (perms) {
        for (const perm of perms) {
          this.groupPermissions[groupId][perm.id] = true;
        }
      }
    } catch (err: any) {
      console.error('Error loading group permissions:', err);
      this.error = err.error?.detail || 'Failed to load group permissions';
    }
  }

  hasPermission(permissionId: number): boolean {
    if (!this.selectedGroupId) return false;
    return this.groupPermissions[this.selectedGroupId]?.[permissionId] || false;
  }

  async togglePermission(permissionId: number, event: Event): Promise<void> {
    if (!this.selectedGroupId || this.updating) return;

    const checkbox = event.target as HTMLInputElement;
    const grant = checkbox.checked;

    this.updating = true;

    try {
      if (grant) {
        await this.apiService.grantPermissionToUserGroup(this.selectedGroupId, permissionId).toPromise();
        if (!this.groupPermissions[this.selectedGroupId]) {
          this.groupPermissions[this.selectedGroupId] = {};
        }
        this.groupPermissions[this.selectedGroupId][permissionId] = true;
      } else {
        await this.apiService.revokePermissionFromUserGroup(this.selectedGroupId, permissionId).toPromise();
        if (this.groupPermissions[this.selectedGroupId]) {
          this.groupPermissions[this.selectedGroupId][permissionId] = false;
        }
      }
    } catch (err: any) {
      console.error('Error updating permission:', err);
      // Revert checkbox state
      checkbox.checked = !grant;
      alert(err.error?.detail || 'Failed to update permission');
    } finally {
      this.updating = false;
    }
  }

  formatResource(resource: string): string {
    return resource
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }
}
