import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';
import { User, UserGroup } from '../models';

@Component({
    selector: 'app-users',
    template: `
    <app-navbar></app-navbar>
    <div class="resource-page">
      <h2>Users</h2>
        <div *ngIf="externallyManagedUsers" class="banner warning">
          User management is handled externally. Local add/edit/delete are disabled.
        </div>
      <div class="actions" *ngIf="isAdmin">
          <button class="btn btn-primary" (click)="showForm = true" [disabled]="externallyManagedUsers" title="Disabled when users are externally managed">New User</button>
      </div>

      <div *ngIf="showForm" class="modal">
        <div class="modal-content">
          <h3>Create User</h3>
          <form (ngSubmit)="createUser()" #userForm="ngForm">
            <div class="form-group">
              <label>Email *</label>
              <input class="form-control" name="email" [(ngModel)]="newUser.email" required />
            </div>
            <div class="form-group">
              <label>Password *</label>
              <input type="password" class="form-control" name="password" [(ngModel)]="newUser.password" required />
            </div>
            <div class="form-group">
              <label>User Groups</label>
              <div class="checkbox-list">
                <label *ngFor="let g of availableGroups" class="checkbox-item">
                  <input type="checkbox" [value]="g.id" (change)="onGroupToggle($event, g.id)"/>
                  {{ g.name }}
                </label>
              </div>
            </div>
            <div class="form-group">
              <label>Active</label>
              <input type="checkbox" name="is_active" [(ngModel)]="newUser.is_active" />
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" (click)="showForm = false">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="creating || userForm.invalid || externallyManagedUsers">{{ creating ? 'Creating...' : 'Create' }}</button>
            </div>
          </form>
        </div>
      </div>

      <table *ngIf="users.length" class="table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Groups</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let u of users">
            <td>{{ u.email }}</td>
            <td>{{ groupNames(u) }}</td>
            <td>
              <label>
                <input type="checkbox" [checked]="u.is_active" (change)="toggleUserActive(u, $event)" [disabled]="externallyManagedUsers" /> Active
              </label>
            </td>
            <td>
              <button class="btn btn-sm" (click)="openEdit(u)" [disabled]="externallyManagedUsers" title="Edit user">Edit</button>
              <button class="btn btn-sm btn-danger" (click)="deleteUser(u)" [disabled]="isSelfDelete(u) || externallyManagedUsers">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p *ngIf="!users.length">No users found.</p>

      <!-- Edit User Modal -->
      <div *ngIf="editingUser" class="modal">
        <div class="modal-content">
          <h3>Edit User</h3>
          <form (ngSubmit)="saveEdit()" #editForm="ngForm">
            <div class="form-group">
              <label>Email *</label>
              <input class="form-control" name="email" [(ngModel)]="editUser.email" required [disabled]="externallyManagedUsers" />
            </div>
            <div class="form-group">
              <label>New Password (optional)</label>
              <input type="password" class="form-control" name="password" [(ngModel)]="editUser.password" [disabled]="externallyManagedUsers" />
            </div>
            <div class="form-group">
              <label>User Groups</label>
              <div class="checkbox-list">
                <label *ngFor="let g of availableGroups" class="checkbox-item">
                  <input type="checkbox" [checked]="editUser.user_group_ids.includes(g.id)" (change)="onEditGroupToggle($event, g.id)" [disabled]="externallyManagedUsers"/>
                  {{ g.name }}
                </label>
              </div>
            </div>
            <div class="form-group">
              <label>Active</label>
              <input type="checkbox" name="is_active" [(ngModel)]="editUser.is_active" [disabled]="externallyManagedUsers" />
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" (click)="closeEdit()">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="savingEdit || editForm.invalid || externallyManagedUsers">{{ savingEdit ? 'Saving...' : 'Save' }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
    styles: [`
    .resource-page { padding:1.5rem; }
    .banner.warning { background: #fff3cd; color: #856404; padding: 0.75rem 1rem; border: 1px solid #ffeeba; border-radius: 4px; margin-bottom: 1rem; }
    .actions { margin-bottom:1rem; }
    .table { width:100%; border-collapse:collapse; }
    th, td { padding:.5rem; border-bottom:1px solid #eee; }
    .form-group { margin-bottom:1rem; }
    .form-actions { display:flex; gap:.75rem; justify-content:flex-end; }
    .modal { position:fixed; inset:0; background:rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; padding: 1rem; overflow-y: auto; }
    .modal-content { background:#fff; padding:1.5rem; width:500px; max-width:95%; border-radius:8px; max-height: 90vh; overflow-y: auto; margin: auto; }
    
    @media (max-width: 768px) {
      .resource-page { padding: 1rem; }
      .modal-content { padding: 1rem; }
      .form-actions { flex-direction: column; }
      .form-actions button { width: 100%; }
      table { font-size: 0.9rem; }
      th, td { padding: 0.5rem 0.25rem; }
      .table-responsive { overflow-x: auto; }
    }
  `],
    standalone: false
})
export class UsersComponent implements OnInit {
  users: User[] = [];
  showForm = false;
  creating = false;
  availableGroups: UserGroup[] = [];
  selectedGroupIds: number[] = [];
  newUser: { email: string; password: string; is_active: boolean } = {
    email: '', password: '', is_active: true
  };
  isAdmin = this.auth.isAdmin();
  currentUser = this.auth.getCurrentUser();
  externallyManagedUsers = false;
  editingUser: User | null = null;
  editUser: { email: string; password?: string; is_active: boolean; user_group_ids: number[] } = { email: '', is_active: true, user_group_ids: [] };
  savingEdit = false;

  constructor(private api: ApiService, private auth: AuthService) {}

  ngOnInit(): void { this.load(); this.loadGroups(); this.loadSettings(); }

  load(): void {
    this.api.getUsers().subscribe({
      next: (u: User[]) => (this.users = u),
      error: (e: any) => console.error('Failed to load users', e)
    });
  }

  loadGroups(): void {
    this.api.getUserGroups().subscribe({
      next: (groups: any[]) => { this.availableGroups = groups as UserGroup[]; },
      error: (e: any) => console.error('Failed to load user groups', e)
    });
  }

  loadSettings(): void {
    this.api.getSettings().subscribe({
      next: s => this.externallyManagedUsers = !!s.externally_managed_users,
      error: e => console.error('Failed to load settings', e)
    });
  }

  onGroupToggle(event: Event, groupId: number): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      if (!this.selectedGroupIds.includes(groupId)) this.selectedGroupIds.push(groupId);
    } else {
      this.selectedGroupIds = this.selectedGroupIds.filter(id => id !== groupId);
    }
  }

  createUser(): void {
    if (!this.isAdmin || this.externallyManagedUsers) return;
    if (!this.newUser.email || !this.newUser.password) return;
    this.creating = true;
    const payload: any = { ...this.newUser, user_group_ids: this.selectedGroupIds };
    this.api.createUser(payload).subscribe({
      next: (created: User) => {
        this.users = [...this.users, created];
        this.showForm = false;
        this.creating = false;
        this.newUser = { email: '', password: '', is_active: true };
        this.selectedGroupIds = [];
      },
      error: (e: any) => {
        alert('Create failed: ' + (e.error?.detail || 'Unknown error'));
        this.creating = false;
      }
    });
  }

  isSelfDelete(user: User): boolean {
    return user.id === this.currentUser?.id;
  }


  toggleUserActive(user: User, event: Event): void {
    const target = event.target as HTMLInputElement;
    if (this.externallyManagedUsers) return;
    this.updateUser(user, { is_active: target.checked });
  }

  updateUser(user: User, patch: { email?: string; password?: string; is_active?: boolean; user_group_ids?: number[] }): void {
    if (!this.isAdmin) return;
    this.api.updateUser(user.id, patch).subscribe({
      next: (updated: User) => Object.assign(user, updated),
      error: (e: any) => alert('Update failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }

  deleteUser(user: User): void {
    if (!this.isAdmin || this.externallyManagedUsers || user.id === this.currentUser?.id) return;
    if (!confirm('Delete this user?')) return;
    this.api.deleteUser(user.id).subscribe({
      next: () => (this.users = this.users.filter(u => u.id !== user.id)),
      error: (e: any) => alert('Delete failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }

  groupNames(u: User): string {
    const groups = (u && Array.isArray(u.groups)) ? u.groups : [];
    const names = groups.map(g => g.name);
    return names.length ? names.join(', ') : '—';
  }

  openEdit(user: User): void {
    if (!this.isAdmin || this.externallyManagedUsers) return;
    this.editingUser = user;
    this.editUser = {
      email: user.email,
      is_active: user.is_active,
      user_group_ids: (user.groups || []).map(g => g.id)
    };
  }

  closeEdit(): void {
    this.editingUser = null;
    this.savingEdit = false;
    this.editUser = { email: '', is_active: true, user_group_ids: [] };
  }

  onEditGroupToggle(event: Event, groupId: number): void {
    const target = event.target as HTMLInputElement;
    if (target.checked) {
      if (!this.editUser.user_group_ids.includes(groupId)) this.editUser.user_group_ids.push(groupId);
    } else {
      this.editUser.user_group_ids = this.editUser.user_group_ids.filter(id => id !== groupId);
    }
  }

  saveEdit(): void {
    if (!this.isAdmin || this.externallyManagedUsers || !this.editingUser) return;
    this.savingEdit = true;
    const patch: any = {
      email: this.editUser.email,
      is_active: this.editUser.is_active,
      user_group_ids: this.editUser.user_group_ids
    };
    if (this.editUser.password && this.editUser.password.length) {
      patch.password = this.editUser.password;
    }
    this.api.updateUser(this.editingUser.id, patch).subscribe({
      next: (updated: User) => {
        // Update local row
        const idx = this.users.findIndex(u => u.id === updated.id);
        if (idx >= 0) this.users[idx] = { ...this.users[idx], ...updated };
        this.closeEdit();
      },
      error: (e: any) => {
        alert('Update failed: ' + (e.error?.detail || 'Unknown error'));
        this.savingEdit = false;
      }
    });
  }
}
