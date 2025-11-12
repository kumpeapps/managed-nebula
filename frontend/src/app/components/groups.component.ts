import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { Group } from '../models';

@Component({
  selector: 'app-groups',
  template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <div class="header">
          <h2>Groups</h2>
          <button (click)="showCreateForm = true" class="btn btn-primary">Add Group</button>
        </div>
        
        <div *ngIf="showCreateForm" class="modal">
          <div class="modal-content">
            <h3>Create New Group</h3>
            <form (ngSubmit)="createGroup()" #groupForm="ngForm">
              <div class="form-group">
                <label for="name">Group Name *</label>
                <input type="text" id="name" [(ngModel)]="newGroup.name" name="name" required class="form-control" 
                       placeholder="e.g., 'production' or 'kumpeapps:waf:www' for hierarchical">
                <small class="help-text">Use colons (:) for hierarchical groups. Example: parent:child:grandchild</small>
              </div>
              
              <div class="form-actions">
                <button type="button" (click)="showCreateForm = false" class="btn btn-secondary">Cancel</button>
                <button type="submit" [disabled]="groupForm.invalid || creating" class="btn btn-primary">{{ creating ? 'Creating...' : 'Create' }}</button>
              </div>
            </form>
          </div>
        </div>
        
        <div class="groups-list">
          <div *ngIf="groups.length > 0" class="groups-grid">
            <div *ngFor="let group of groups" class="group-card" [class.subgroup]="group.is_subgroup">
              <div class="group-header">
                <h3 class="group-name">
                  <span *ngIf="group.is_subgroup" class="hierarchy-icon">↳</span>
                  {{ group.name }}
                </h3>
                <span *ngIf="group.owner" class="owner-badge">Owner: {{ group.owner.email }}</span>
              </div>
              <div class="group-meta">
                <span>Clients: {{ group.client_count }}</span>
                <span *ngIf="group.created_at">Created: {{ group.created_at | date:'short' }}</span>
                <span *ngIf="group.parent_name" class="parent-info">Parent: {{ group.parent_name }}</span>
              </div>
              <div class="group-actions">
                <button *ngIf="canManagePermissions(group)" (click)="openPermissionsModal(group)" class="btn btn-sm btn-secondary">Manage Permissions</button>
                <button (click)="deleteGroup(group.id)" class="btn btn-sm btn-danger">Delete</button>
              </div>
            </div>
          </div>
          <p *ngIf="groups.length === 0">No groups found. Create one to get started.</p>
        </div>

        <!-- Permissions Modal -->
        <div *ngIf="selectedGroup && showPermissionsModal" class="modal">
          <div class="modal-content large-modal">
            <h3>Manage Permissions: {{ selectedGroup.name }}</h3>
            
            <div class="permissions-section">
              <h4>Current Permissions</h4>
              <div *ngIf="loadingPermissions" class="loading">Loading permissions...</div>
              <div *ngIf="!loadingPermissions && groupPermissions.length === 0" class="no-data">
                No permissions granted yet.
              </div>
              <table *ngIf="!loadingPermissions && groupPermissions.length > 0" class="permissions-table">
                <thead>
                  <tr>
                    <th>User/Group</th>
                    <th>Add to Client</th>
                    <th>Remove from Client</th>
                    <th>Create Subgroup</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let perm of groupPermissions">
                    <td>
                      <span *ngIf="perm.user">{{ perm.user.email }}</span>
                      <span *ngIf="perm.user_group" class="user-group-badge">{{ perm.user_group.name }}</span>
                    </td>
                    <td>
                      <span class="permission-badge" [class.active]="perm.can_add_to_client">
                        {{ perm.can_add_to_client ? '✓' : '✗' }}
                      </span>
                    </td>
                    <td>
                      <span class="permission-badge" [class.active]="perm.can_remove_from_client">
                        {{ perm.can_remove_from_client ? '✓' : '✗' }}
                      </span>
                    </td>
                    <td>
                      <span class="permission-badge" [class.active]="perm.can_create_subgroup">
                        {{ perm.can_create_subgroup ? '✓' : '✗' }}
                      </span>
                    </td>
                    <td>
                      <button (click)="revokeGroupPermission(perm.id)" class="btn btn-xs btn-danger">Revoke</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="permissions-section">
              <h4>Grant New Permission</h4>
              <form (ngSubmit)="grantPermission()" #permForm="ngForm">
                <div class="form-row">
                  <div class="form-group">
                    <label for="permUser">User</label>
                    <select id="permUser" [(ngModel)]="newPermission.user_id" name="user_id" class="form-control"
                            [disabled]="newPermission.user_group_id !== null">
                      <option [ngValue]="null">-- Select User --</option>
                      <option *ngFor="let user of availableUsers" [ngValue]="user.id">{{ user.email }}</option>
                    </select>
                  </div>
                  
                  <div class="form-group">
                    <label for="permUserGroup">User Group</label>
                    <select id="permUserGroup" [(ngModel)]="newPermission.user_group_id" name="user_group_id" class="form-control"
                            [disabled]="newPermission.user_id !== null">
                      <option [ngValue]="null">-- Select User Group --</option>
                      <option *ngFor="let ug of availableUserGroups" [ngValue]="ug.id">{{ ug.name }}</option>
                    </select>
                  </div>
                </div>
                
                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" [(ngModel)]="newPermission.can_add_to_client" name="can_add_to_client">
                    Can add to client
                  </label>
                </div>
                
                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" [(ngModel)]="newPermission.can_remove_from_client" name="can_remove_from_client">
                    Can remove from client
                  </label>
                </div>
                
                <div class="form-group">
                  <label class="checkbox-label">
                    <input type="checkbox" [(ngModel)]="newPermission.can_create_subgroup" name="can_create_subgroup">
                    Can create subgroups
                  </label>
                </div>
                
                <div class="form-actions">
                  <button type="button" (click)="closePermissionsModal()" class="btn btn-secondary">Close</button>
                  <button type="submit" 
                          [disabled]="!canGrantPermission() || grantingPermission" 
                          class="btn btn-primary">
                    {{ grantingPermission ? 'Granting...' : 'Grant Permission' }}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard {
      min-height: 100vh;
      background: #f5f5f5;
    }
    
    .navbar {
      background: white;
      padding: 1rem 2rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .navbar h1 {
      margin: 0;
      color: #333;
    }
    
    .nav-links {
      display: flex;
      gap: 1rem;
      align-items: center;
    }
    
    .nav-links a {
      color: #666;
      text-decoration: none;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      transition: background 0.3s;
    }
    
    .nav-links a:hover,
    .nav-links a.active {
      background: #f0f0f0;
      color: #333;
    }
    
    .user-info {
      color: #666;
      padding: 0 1rem;
      border-left: 1px solid #ddd;
    }
    
    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 2rem;
    }
    
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
    }
    
    h2 {
      margin: 0;
      color: #333;
    }
    
    .groups-list {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .groups-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 1.5rem;
    }
    
    .group-card {
      border: 1px solid #eee;
      border-radius: 8px;
      padding: 1.5rem;
      background: #fafafa;
    }
    
    .group-card.subgroup {
      border-left: 3px solid #4CAF50;
      background: #f5f9f5;
    }
    
    .group-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
    }
    
    .group-name {
      margin: 0;
      color: #333;
      font-size: 1.1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    
    .hierarchy-icon {
      color: #4CAF50;
      font-size: 1.2rem;
    }
    
    .owner-badge {
      font-size: 0.75rem;
      background: #e3f2fd;
      color: #1976d2;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
    }
    
    .group-card h3 {
      margin: 0 0 0.5rem 0;
      color: #333;
    }
    
    .group-card p {
      color: #666;
      margin: 0 0 1rem 0;
    }
    
    .group-meta {
      font-size: 0.85rem;
      color: #999;
      margin-bottom: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    
    .parent-info {
      color: #4CAF50;
      font-weight: 500;
    }
    
    .help-text {
      display: block;
      margin-top: 0.25rem;
      color: #666;
      font-size: 0.875rem;
    }
    
    .group-actions {
      display: flex;
      gap: 0.5rem;
    }
    
    .btn {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.3s;
    }
    
    .btn-primary {
      background: #4CAF50;
      color: white;
    }
    
    .btn-primary:hover {
      background: #45a049;
    }
    
    .btn-secondary {
      background: #6c757d;
      color: white;
    }
    
    .btn-secondary:hover {
      background: #5a6268;
    }
    
    .btn-danger {
      background: #dc3545;
      color: white;
    }
    
    .btn-danger:hover {
      background: #c82333;
    }
    
    .btn-sm {
      padding: 0.25rem 0.5rem;
      font-size: 0.85rem;
    }
    
    .modal {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0,0,0,0.5);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 9999;
    }
    
    .modal-content {
      background: white;
      padding: 2rem;
      border-radius: 8px;
      width: 90%;
      max-width: 500px;
    }
    
    .modal-content h3 {
      margin-top: 0;
      color: #333;
    }
    
    .form-group {
      margin-bottom: 1rem;
    }
    
    .form-group label {
      display: block;
      margin-bottom: 0.5rem;
      color: #333;
      font-weight: 500;
    }
    
    .form-control {
      width: 100%;
      padding: 0.5rem;
      border: 1px solid #ddd;
      border-radius: 4px;
    }
    
    textarea.form-control {
      resize: vertical;
    }
    
    .form-actions {
      display: flex;
      gap: 1rem;
      justify-content: flex-end;
      margin-top: 1.5rem;
    }
    
    .large-modal {
      max-width: 800px;
      max-height: 90vh;
      overflow-y: auto;
    }
    
    .permissions-section {
      margin-bottom: 2rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid #eee;
    }
    
    .permissions-section:last-child {
      border-bottom: none;
    }
    
    .permissions-section h4 {
      margin-top: 0;
      margin-bottom: 1rem;
      color: #333;
    }
    
    .permissions-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
    }
    
    .permissions-table th,
    .permissions-table td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 1px solid #eee;
    }
    
    .permissions-table th {
      background: #f8f9fa;
      font-weight: 600;
      color: #495057;
    }
    
    .permission-badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 3px;
      font-size: 0.85rem;
      font-weight: 600;
      background: #e9ecef;
      color: #6c757d;
    }
    
    .permission-badge.active {
      background: #d4edda;
      color: #155724;
    }
    
    .user-group-badge {
      background: #e3f2fd;
      color: #1976d2;
      padding: 0.25rem 0.5rem;
      border-radius: 3px;
      font-size: 0.85rem;
    }
    
    .btn-xs {
      padding: 0.15rem 0.4rem;
      font-size: 0.75rem;
    }
    
    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    
    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-weight: normal;
      cursor: pointer;
    }
    
    .checkbox-label input[type="checkbox"] {
      width: auto;
      margin: 0;
    }
    
    .loading {
      text-align: center;
      padding: 2rem;
      color: #666;
    }
    
    .no-data {
      text-align: center;
      padding: 1rem;
      color: #999;
      font-style: italic;
    }
    
    @media (max-width: 768px) {
      .container {
        padding: 1rem;
      }
      
      .header {
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
      }
      
      .header button {
        width: 100%;
      }
      
      .groups-grid {
        grid-template-columns: 1fr;
      }
      
      .group-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
      }
      
      .group-actions {
        flex-direction: column;
        width: 100%;
      }
      
      .group-actions button {
        width: 100%;
      }
      
      .modal {
        padding: 0.5rem;
      }
      
      .modal-content {
        padding: 1rem;
        width: 95%;
      }
      
      .large-modal {
        max-width: 95%;
      }
      
      .form-actions {
        flex-direction: column;
      }
      
      .form-actions button {
        width: 100%;
      }
      
      .permissions-table {
        font-size: 0.85rem;
      }
      
      .permissions-table th,
      .permissions-table td {
        padding: 0.5rem 0.25rem;
      }
    }
  `]
})
export class GroupsComponent implements OnInit {
  currentUser = this.authService.getCurrentUser();
  groups: Group[] = [];
  showCreateForm = false;
  newGroup: any = { name: '' };
  creating = false;
  loading = false;
  errorMessage: string | null = null;
  
  // Permissions modal
  showPermissionsModal = false;
  selectedGroup: Group | null = null;
  groupPermissions: any[] = [];
  loadingPermissions = false;
  grantingPermission = false;
  availableUsers: any[] = [];
  availableUserGroups: any[] = [];
  newPermission: any = {
    user_id: null,
    user_group_id: null,
    can_add_to_client: false,
    can_remove_from_client: false,
    can_create_subgroup: false
  };

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadGroups();
    this.loadUsers();
    this.loadUserGroups();
  }

  loadGroups(): void {
    this.loading = true;
    this.apiService.getGroups().subscribe({
      next: (groups: Group[]) => {
        this.groups = groups;
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Failed to load groups:', error);
        this.errorMessage = error.error?.detail || 'Failed to load groups';
        this.loading = false;
      }
    });
  }

  createGroup(): void {
    if (!this.newGroup.name) return;
    this.creating = true;
    this.apiService.createGroup(this.newGroup).subscribe({
      next: (created: Group) => {
        this.showCreateForm = false;
        this.newGroup = { name: '' };
        this.groups = [...this.groups, created];
        this.creating = false;
      },
      error: (error: any) => {
        console.error('Failed to create group:', error);
        alert('Failed to create group: ' + (error.error?.detail || 'Unknown error'));
        this.creating = false;
      }
    });
  }

  deleteGroup(id: number): void {
    if (!confirm('Are you sure you want to delete this group?')) return;
    this.apiService.deleteGroup(id).subscribe({
      next: () => {
        this.groups = this.groups.filter(g => g.id !== id);
      },
      error: (error: any) => {
        console.error('Failed to delete group:', error);
        alert('Failed to delete group: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

  updateGroup(group: Group, patch: Partial<Group>): void {
    // Backend GroupUpdate expects only 'name'
    const payload: any = { name: patch.name ?? group.name };
    this.apiService.updateGroup(group.id, payload).subscribe({
      next: (updated: Group) => Object.assign(group, updated),
      error: (error: any) => {
        console.error('Failed to update group:', error);
        alert('Failed to update group: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

  canManagePermissions(group: Group): boolean {
    // Can manage permissions if admin or owner
    const user = this.currentUser;
    if (!user) return false;
    if (user.is_admin) return true;
    if (group.owner && group.owner.id === user.id) return true;
    return false;
  }

  openPermissionsModal(group: Group): void {
    this.selectedGroup = group;
    this.showPermissionsModal = true;
    this.loadGroupPermissions(group.id);
    this.resetNewPermission();
  }

  closePermissionsModal(): void {
    this.showPermissionsModal = false;
    this.selectedGroup = null;
    this.groupPermissions = [];
    this.resetNewPermission();
  }

  loadGroupPermissions(groupId: number): void {
    this.loadingPermissions = true;
    this.apiService.getGroupPermissions(groupId).subscribe({
      next: (permissions: any[]) => {
        this.groupPermissions = permissions;
        this.loadingPermissions = false;
      },
      error: (error: any) => {
        console.error('Failed to load group permissions:', error);
        alert('Failed to load permissions: ' + (error.error?.detail || 'Unknown error'));
        this.loadingPermissions = false;
      }
    });
  }

  loadUsers(): void {
    this.apiService.getUsers().subscribe({
      next: (users: any[]) => {
        this.availableUsers = users;
      },
      error: (error: any) => {
        console.error('Failed to load users:', error);
      }
    });
  }

  loadUserGroups(): void {
    this.apiService.getUserGroups().subscribe({
      next: (userGroups: any[]) => {
        this.availableUserGroups = userGroups;
      },
      error: (error: any) => {
        console.error('Failed to load user groups:', error);
      }
    });
  }

  canGrantPermission(): boolean {
    // Must have either user_id or user_group_id (but not both or neither)
    const hasUser = this.newPermission.user_id !== null;
    const hasUserGroup = this.newPermission.user_group_id !== null;
    return (hasUser && !hasUserGroup) || (!hasUser && hasUserGroup);
  }

  resetNewPermission(): void {
    this.newPermission = {
      user_id: null,
      user_group_id: null,
      can_add_to_client: false,
      can_remove_from_client: false,
      can_create_subgroup: false
    };
  }

  grantPermission(): void {
    if (!this.canGrantPermission() || !this.selectedGroup) return;
    
    this.grantingPermission = true;
    this.apiService.grantGroupPermission(this.selectedGroup.id, this.newPermission).subscribe({
      next: (granted: any) => {
        this.loadGroupPermissions(this.selectedGroup!.id);
        this.resetNewPermission();
        this.grantingPermission = false;
      },
      error: (error: any) => {
        console.error('Failed to grant permission:', error);
        alert('Failed to grant permission: ' + (error.error?.detail || 'Unknown error'));
        this.grantingPermission = false;
      }
    });
  }

  revokeGroupPermission(permissionId: number): void {
    if (!this.selectedGroup) return;
    if (!confirm('Are you sure you want to revoke this permission?')) return;
    
    this.apiService.revokeGroupPermission(this.selectedGroup.id, permissionId).subscribe({
      next: () => {
        this.groupPermissions = this.groupPermissions.filter(p => p.id !== permissionId);
      },
      error: (error: any) => {
        console.error('Failed to revoke permission:', error);
        alert('Failed to revoke permission: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

}
