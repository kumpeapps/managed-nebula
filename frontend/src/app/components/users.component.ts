import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';
import { User } from '../models';

@Component({
    selector: 'app-users',
    template: `
    <app-navbar></app-navbar>
    <div class="resource-page">
      <h2>Users</h2>
      <div class="actions" *ngIf="isAdmin">
        <button class="btn btn-primary" (click)="showForm = true">New User</button>
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
              <label>Role</label>
              <select class="form-control" name="role_name" [(ngModel)]="newUser.role_name">
                <option value="user">User</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div class="form-group">
              <label>Active</label>
              <input type="checkbox" name="is_active" [(ngModel)]="newUser.is_active" />
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" (click)="showForm = false">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="creating || userForm.invalid">{{ creating ? 'Creating...' : 'Create' }}</button>
            </div>
          </form>
        </div>
      </div>

      <table *ngIf="users.length" class="table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let u of users">
            <td>{{ u.email }}</td>
            <td>
              <select class="form-control" [disabled]="!isAdmin" (change)="updateUserRole(u, $event)">
                <option value="user" [selected]="getRoleName(u) === 'user'">User</option>
                <option value="admin" [selected]="getRoleName(u) === 'admin'">Admin</option>
              </select>
            </td>
            <td>
              <label>
                <input type="checkbox" [checked]="u.is_active" (change)="toggleUserActive(u, $event)" /> Active
              </label>
            </td>
            <td>
              <button class="btn btn-sm btn-danger" (click)="deleteUser(u)" [disabled]="isSelfDelete(u)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p *ngIf="!users.length">No users found.</p>
    </div>
  `,
    styles: [`
    .resource-page { padding:1.5rem; }
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
  newUser: { email: string; password: string; role_name: string; is_active: boolean } = {
    email: '', password: '', role_name: 'user', is_active: true
  };
  isAdmin = this.auth.isAdmin();
  currentUser = this.auth.getCurrentUser();

  constructor(private api: ApiService, private auth: AuthService) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.api.getUsers().subscribe({
      next: (u: User[]) => (this.users = u),
      error: (e: any) => console.error('Failed to load users', e)
    });
  }

  createUser(): void {
    if (!this.isAdmin) return;
    if (!this.newUser.email || !this.newUser.password) return;
    this.creating = true;
    this.api.createUser(this.newUser).subscribe({
      next: (created: User) => {
        this.users = [...this.users, created];
        this.showForm = false;
        this.creating = false;
        this.newUser = { email: '', password: '', role_name: 'user', is_active: true };
      },
      error: (e: any) => {
        alert('Create failed: ' + (e.error?.detail || 'Unknown error'));
        this.creating = false;
      }
    });
  }

  getRoleName(user: User): string {
    if (typeof user.role === 'string') return user.role;
    return user.role?.name || 'user';
  }

  isSelfDelete(user: User): boolean {
    return user.id === this.currentUser?.id;
  }

  updateUserRole(user: User, event: Event): void {
    const target = event.target as HTMLSelectElement;
    this.updateUser(user, { role_name: target.value });
  }

  toggleUserActive(user: User, event: Event): void {
    const target = event.target as HTMLInputElement;
    this.updateUser(user, { is_active: target.checked });
  }

  updateUser(user: User, patch: { email?: string; password?: string; role_name?: string; is_active?: boolean }): void {
    if (!this.isAdmin) return;
    this.api.updateUser(user.id, patch).subscribe({
      next: (updated: User) => Object.assign(user, updated),
      error: (e: any) => alert('Update failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }

  deleteUser(user: User): void {
    if (!this.isAdmin || user.id === this.currentUser?.id) return;
    if (!confirm('Delete this user?')) return;
    this.api.deleteUser(user.id).subscribe({
      next: () => (this.users = this.users.filter(u => u.id !== user.id)),
      error: (e: any) => alert('Delete failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }
}
