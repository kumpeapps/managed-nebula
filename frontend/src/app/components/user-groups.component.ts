import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { UserGroup } from '../models';

@Component({
  selector: 'app-user-groups',
  template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <div class="header">
          <h2>User Groups</h2>
          <button (click)="showCreateForm = true" class="btn btn-primary">Create User Group</button>
        </div>
        
        <!-- Create Modal -->
        <div *ngIf="showCreateForm" class="modal">
          <div class="modal-content">
            <h3>Create New User Group</h3>
            <form (ngSubmit)="createUserGroup()" #createForm="ngForm">
              <div class="form-group">
                <label for="name">Name *</label>
                <input type="text" id="name" [(ngModel)]="newUserGroup.name" name="name" required class="form-control">
              </div>
              
              <div class="form-group">
                <label for="description">Description</label>
                <textarea id="description" [(ngModel)]="newUserGroup.description" name="description" 
                          class="form-control" rows="3"></textarea>
              </div>
              
              <div class="form-actions">
                <button type="button" (click)="showCreateForm = false" class="btn btn-secondary">Cancel</button>
                <button type="submit" [disabled]="createForm.invalid || creating" class="btn btn-primary">
                  {{ creating ? 'Creating...' : 'Create' }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- Edit Modal -->
        <div *ngIf="showEditForm && selectedUserGroup" class="modal">
          <div class="modal-content">
            <h3>Edit User Group</h3>
            <form (ngSubmit)="updateUserGroup()" #editForm="ngForm">
              <div class="form-group">
                <label for="editName">Name *</label>
                <input type="text" id="editName" [(ngModel)]="editData.name" name="name" required class="form-control">
              </div>
              
              <div class="form-group">
                <label for="editDescription">Description</label>
                <textarea id="editDescription" [(ngModel)]="editData.description" name="description" 
                          class="form-control" rows="3"></textarea>
              </div>
              
              <div class="form-actions">
                <button type="button" (click)="closeEditForm()" class="btn btn-secondary">Cancel</button>
                <button type="submit" [disabled]="editForm.invalid || updating" class="btn btn-primary">
                  {{ updating ? 'Updating...' : 'Update' }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- Members Modal -->
        <div *ngIf="showMembersModal && selectedUserGroup" class="modal">
          <div class="modal-content large-modal">
            <h3>Members: {{ selectedUserGroup.name }}</h3>
            
            <div class="members-section">
              <h4>Current Members</h4>
              <div *ngIf="loadingMembers" class="loading">Loading members...</div>
              <div *ngIf="!loadingMembers && members.length === 0" class="no-data">
                No members yet.
              </div>
              <table *ngIf="!loadingMembers && members.length > 0" class="members-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Added</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let member of members">
                    <td>{{ member.user?.email }}</td>
                    <td>{{ member.added_at | date:'short' }}</td>
                    <td>
                      <button (click)="removeMember(member.user!.id)" class="btn btn-xs btn-danger">Remove</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="members-section">
              <h4>Add Members</h4>
              <form (ngSubmit)="addMembers()" #membersForm="ngForm">
                <div class="form-group">
                  <label>Select Users</label>
                  <div class="user-selection">
                    <div *ngFor="let user of getAvailableUsersToAdd()" class="checkbox-option">
                      <label class="checkbox-label">
                        <input type="checkbox" 
                               [checked]="isUserSelected(user.id)"
                               (change)="toggleUserSelection(user.id)">
                        {{ user.email }}
                      </label>
                    </div>
                  </div>
                  <div *ngIf="getAvailableUsersToAdd().length === 0" class="no-data">
                    All users are already members.
                  </div>
                </div>
                
                <div class="form-actions">
                  <button type="button" (click)="closeMembersModal()" class="btn btn-secondary">Close</button>
                  <button type="submit" 
                          [disabled]="selectedUserIds.length === 0 || addingMembers" 
                          class="btn btn-primary">
                    {{ addingMembers ? 'Adding...' : 'Add Selected' }}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>

        <!-- User Groups List -->
        <div class="user-groups-list">
          <div *ngIf="userGroups.length > 0" class="user-groups-grid">
            <div *ngFor="let ug of userGroups" class="user-group-card">
              <div class="ug-header">
                <h3>{{ ug.name }}</h3>
                <span *ngIf="ug.owner" class="owner-badge">Owner: {{ ug.owner.email }}</span>
              </div>
              
              <p class="ug-description" *ngIf="ug.description">{{ ug.description }}</p>
              
              <div class="ug-meta">
                <span>Members: {{ ug.member_count || 0 }}</span>
                <span>Created: {{ ug.created_at | date:'short' }}</span>
              </div>
              
              <div class="ug-actions" *ngIf="canManage(ug)">
                <button (click)="openMembersModal(ug)" class="btn btn-sm btn-secondary">Manage Members</button>
                <button (click)="openEditForm(ug)" class="btn btn-sm btn-primary">Edit</button>
                <button (click)="deleteUserGroup(ug.id)" class="btn btn-sm btn-danger">Delete</button>
              </div>
            </div>
          </div>
          <p *ngIf="userGroups.length === 0">No user groups found. Create one to get started.</p>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard {
      min-height: 100vh;
      background: #f5f5f5;
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
    
    .user-groups-list {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .user-groups-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 1.5rem;
    }
    
    .user-group-card {
      border: 1px solid #eee;
      border-radius: 8px;
      padding: 1.5rem;
      background: #fafafa;
    }
    
    .ug-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.75rem;
    }
    
    .ug-header h3 {
      margin: 0;
      color: #333;
      font-size: 1.1rem;
    }
    
    .owner-badge {
      font-size: 0.75rem;
      background: #e3f2fd;
      color: #1976d2;
      padding: 0.25rem 0.5rem;
      border-radius: 4px;
    }
    
    .ug-description {
      color: #666;
      margin: 0.5rem 0;
      font-size: 0.9rem;
    }
    
    .ug-meta {
      font-size: 0.85rem;
      color: #999;
      margin-bottom: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    
    .ug-actions {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
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
    
    .btn-xs {
      padding: 0.15rem 0.4rem;
      font-size: 0.75rem;
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
      z-index: 1000;
    }
    
    .modal-content {
      background: white;
      padding: 2rem;
      border-radius: 8px;
      width: 90%;
      max-width: 500px;
    }
    
    .large-modal {
      max-width: 700px;
      max-height: 90vh;
      overflow-y: auto;
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
    
    .members-section {
      margin-bottom: 2rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid #eee;
    }
    
    .members-section:last-child {
      border-bottom: none;
    }
    
    .members-section h4 {
      margin-top: 0;
      margin-bottom: 1rem;
      color: #333;
    }
    
    .members-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 1rem;
    }
    
    .members-table th,
    .members-table td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 1px solid #eee;
    }
    
    .members-table th {
      background: #f8f9fa;
      font-weight: 600;
      color: #495057;
    }
    
    .user-selection {
      max-height: 300px;
      overflow-y: auto;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 0.5rem;
    }
    
    .checkbox-option {
      padding: 0.5rem;
      border-bottom: 1px solid #f0f0f0;
    }
    
    .checkbox-option:last-child {
      border-bottom: none;
    }
    
    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      font-weight: normal;
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
  `]
})
export class UserGroupsComponent implements OnInit {
  currentUser = this.authService.getCurrentUser();
  userGroups: UserGroup[] = [];
  showCreateForm = false;
  showEditForm = false;
  showMembersModal = false;
  selectedUserGroup: UserGroup | null = null;
  newUserGroup: any = { name: '', description: '' };
  editData: any = { name: '', description: '' };
  creating = false;
  updating = false;
  loading = false;
  
  // Members management
  members: any[] = [];
  loadingMembers = false;
  addingMembers = false;
  availableUsers: any[] = [];
  selectedUserIds: number[] = [];

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadUserGroups();
    this.loadUsers();
  }

  loadUserGroups(): void {
    this.loading = true;
    this.apiService.getUserGroups().subscribe({
      next: (userGroups: UserGroup[]) => {
        this.userGroups = userGroups;
        this.loading = false;
      },
      error: (error: any) => {
        console.error('Failed to load user groups:', error);
        this.loading = false;
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

  createUserGroup(): void {
    if (!this.newUserGroup.name) return;
    this.creating = true;
    this.apiService.createUserGroup(this.newUserGroup).subscribe({
      next: (created: UserGroup) => {
        this.showCreateForm = false;
        this.newUserGroup = { name: '', description: '' };
        this.userGroups = [...this.userGroups, created];
        this.creating = false;
      },
      error: (error: any) => {
        console.error('Failed to create user group:', error);
        alert('Failed to create user group: ' + (error.error?.detail || 'Unknown error'));
        this.creating = false;
      }
    });
  }

  openEditForm(ug: UserGroup): void {
    this.selectedUserGroup = ug;
    this.editData = { name: ug.name, description: ug.description };
    this.showEditForm = true;
  }

  closeEditForm(): void {
    this.showEditForm = false;
    this.selectedUserGroup = null;
    this.editData = { name: '', description: '' };
  }

  updateUserGroup(): void {
    if (!this.selectedUserGroup) return;
    this.updating = true;
    this.apiService.updateUserGroup(this.selectedUserGroup.id, this.editData).subscribe({
      next: (updated: UserGroup) => {
        Object.assign(this.selectedUserGroup!, updated);
        this.closeEditForm();
        this.updating = false;
      },
      error: (error: any) => {
        console.error('Failed to update user group:', error);
        alert('Failed to update user group: ' + (error.error?.detail || 'Unknown error'));
        this.updating = false;
      }
    });
  }

  deleteUserGroup(id: number): void {
    if (!confirm('Are you sure you want to delete this user group?')) return;
    this.apiService.deleteUserGroup(id).subscribe({
      next: () => {
        this.userGroups = this.userGroups.filter(ug => ug.id !== id);
      },
      error: (error: any) => {
        console.error('Failed to delete user group:', error);
        alert('Failed to delete user group: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

  canManage(ug: UserGroup): boolean {
    const user = this.currentUser;
    if (!user) return false;
    if (user.role?.name === 'admin') return true;
    if (ug.owner && ug.owner.id === user.id) return true;
    return false;
  }

  openMembersModal(ug: UserGroup): void {
    this.selectedUserGroup = ug;
    this.showMembersModal = true;
    this.loadMembers(ug.id);
    this.selectedUserIds = [];
  }

  closeMembersModal(): void {
    this.showMembersModal = false;
    this.selectedUserGroup = null;
    this.members = [];
    this.selectedUserIds = [];
  }

  loadMembers(userGroupId: number): void {
    this.loadingMembers = true;
    this.apiService.getUserGroupMembers(userGroupId).subscribe({
      next: (members: any[]) => {
        this.members = members;
        this.loadingMembers = false;
      },
      error: (error: any) => {
        console.error('Failed to load members:', error);
        this.loadingMembers = false;
      }
    });
  }

  getAvailableUsersToAdd(): any[] {
    // Filter out users who are already members
    const memberUserIds = this.members.map(m => m.user?.id).filter(id => id !== undefined);
    return this.availableUsers.filter(user => !memberUserIds.includes(user.id));
  }

  isUserSelected(userId: number): boolean {
    return this.selectedUserIds.includes(userId);
  }

  toggleUserSelection(userId: number): void {
    const index = this.selectedUserIds.indexOf(userId);
    if (index > -1) {
      this.selectedUserIds.splice(index, 1);
    } else {
      this.selectedUserIds.push(userId);
    }
  }

  addMembers(): void {
    if (!this.selectedUserGroup || this.selectedUserIds.length === 0) return;
    this.addingMembers = true;
    this.apiService.addUserGroupMembers(this.selectedUserGroup.id, this.selectedUserIds).subscribe({
      next: (members: any[]) => {
        this.members = members;
        this.selectedUserIds = [];
        this.addingMembers = false;
        // Reload user groups to update member count
        this.loadUserGroups();
      },
      error: (error: any) => {
        console.error('Failed to add members:', error);
        alert('Failed to add members: ' + (error.error?.detail || 'Unknown error'));
        this.addingMembers = false;
      }
    });
  }

  removeMember(userId: number): void {
    if (!this.selectedUserGroup) return;
    if (!confirm('Are you sure you want to remove this member?')) return;
    this.apiService.removeUserGroupMember(this.selectedUserGroup.id, userId).subscribe({
      next: () => {
        this.members = this.members.filter(m => m.user?.id !== userId);
        // Reload user groups to update member count
        this.loadUserGroups();
      },
      error: (error: any) => {
        console.error('Failed to remove member:', error);
        alert('Failed to remove member: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }
}
