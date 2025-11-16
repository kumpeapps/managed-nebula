import { Component } from '@angular/core';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';
import { User } from '../models';

@Component({
  selector: 'app-profile',
  template: `
    <app-navbar></app-navbar>
    <div class="resource-page">
      <h2>My Profile</h2>
      <div *ngIf="externallyManagedUsers" class="banner warning">
        Profile changes are disabled because users are managed externally.
      </div>
      <form (ngSubmit)="onSubmit()" #form="ngForm" class="profile-form">
        <div class="form-group">
          <label>Email</label>
          <input class="form-control" name="email" [(ngModel)]="email" [disabled]="externallyManagedUsers" required />
        </div>
        <div class="form-group">
          <label>Current Password</label>
          <input type="password" class="form-control" name="current_password" [(ngModel)]="current_password" [disabled]="externallyManagedUsers" required />
        </div>
        <div class="form-group">
          <label>New Password (optional)</label>
          <input type="password" class="form-control" name="new_password" [(ngModel)]="new_password" [disabled]="externallyManagedUsers" />
        </div>
        <div class="form-actions">
          <button type="submit" class="btn btn-primary" [disabled]="saving || externallyManagedUsers">{{ saving ? 'Saving...' : 'Save Changes' }}</button>
        </div>
      </form>
    </div>
  `,
  styles: [`
    .resource-page { padding: 1.5rem; }
    .banner.warning { background: #fff3cd; color: #856404; padding: 0.75rem 1rem; border: 1px solid #ffeeba; border-radius: 4px; margin-bottom: 1rem; }
    .form-group { margin-bottom: 1rem; }
    .form-actions { display: flex; gap: .75rem; justify-content: flex-end; }
  `],
  standalone: false
})
export class ProfileComponent {
  email = '';
  current_password = '';
  new_password = '';
  saving = false;
  externallyManagedUsers = false;

  constructor(private api: ApiService, private auth: AuthService) {
    const me = this.auth.getCurrentUser();
    if (me) this.email = me.email;
    this.api.getSettings().subscribe({
      next: s => this.externallyManagedUsers = !!s.externally_managed_users,
      error: () => {}
    });
  }

  onSubmit(): void {
    if (this.externallyManagedUsers) return;
    if (!this.email || !this.current_password) return;
    this.saving = true;
    const payload: any = { email: this.email, current_password: this.current_password };
    if (this.new_password) payload.new_password = this.new_password;
    this.api.updateMe(payload).subscribe({
      next: (_u: User) => {
        this.saving = false;
        this.current_password = '';
        this.new_password = '';
        // Refresh navbar/user state
        this.auth.refreshMe();
        alert('Profile updated');
      },
      error: (e) => {
        this.saving = false;
        alert('Update failed: ' + (e?.error?.detail || 'Unknown error'));
      }
    });
  }
}
