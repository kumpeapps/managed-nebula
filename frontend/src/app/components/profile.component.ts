import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';
import { User, APIKey, APIKeyCreateResponse } from '../models';

@Component({
  selector: 'app-profile',
  template: `
    <app-navbar></app-navbar>
    <div class="resource-page">
      <h2>My Profile</h2>
      
      <!-- Tab Navigation -->
      <div class="tabs">
        <button class="tab" [class.active]="activeTab === 'profile'" (click)="activeTab = 'profile'">Profile Settings</button>
        <button class="tab" [class.active]="activeTab === 'api-keys'" (click)="activeTab = 'api-keys'; loadAPIKeys()">API Keys</button>
      </div>

      <!-- Profile Settings Tab -->
      <div *ngIf="activeTab === 'profile'" class="tab-content">
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

      <!-- API Keys Tab -->
      <div *ngIf="activeTab === 'api-keys'" class="tab-content">
        <div class="api-keys-section">
          <div class="section-header">
            <h3>API Keys</h3>
            <button class="btn btn-primary" (click)="showCreateKeyForm = !showCreateKeyForm">
              {{ showCreateKeyForm ? 'Cancel' : '+ Generate API Key' }}
            </button>
          </div>

          <div class="banner info" style="margin-bottom: 1rem;">
            <strong>💡 What are API Keys?</strong><br>
            API keys allow you to programmatically interact with the Managed Nebula API for automation and integration purposes.
            Keep your keys secure and never share them publicly.
          </div>

          <!-- Create API Key Form -->
          <div *ngIf="showCreateKeyForm" class="create-key-form">
            <h4>Generate New API Key</h4>
            <form (ngSubmit)="createAPIKey()" #keyForm="ngForm">
              <div class="form-group">
                <label>Name *</label>
                <input class="form-control" name="key_name" [(ngModel)]="newKeyName" 
                       placeholder="e.g., CI/CD Pipeline, Automation Script" required />
                <small>A descriptive name to identify this key</small>
              </div>
              <div class="form-group">
                <label>Expires In (days)</label>
                <input type="number" class="form-control" name="expires_in_days" [(ngModel)]="newKeyExpiresInDays" 
                       placeholder="Leave empty for no expiration" min="1" max="3650" />
                <small>Optional: Set an expiration period (max 10 years)</small>
              </div>
              <div class="form-actions">
                <button type="submit" class="btn btn-primary" [disabled]="creatingKey">
                  {{ creatingKey ? 'Generating...' : 'Generate Key' }}
                </button>
                <button type="button" class="btn btn-secondary" (click)="showCreateKeyForm = false">Cancel</button>
              </div>
            </form>
          </div>

          <!-- New Key Display (shown once after creation) -->
          <div *ngIf="newlyCreatedKey" class="alert success">
            <h4>✅ API Key Generated Successfully</h4>
            <p><strong>IMPORTANT:</strong> Copy this key now. You won't be able to see it again!</p>
            <div class="key-display">
              <code>{{ newlyCreatedKey.key }}</code>
              <button class="btn btn-sm" (click)="copyToClipboard(newlyCreatedKey.key)">Copy</button>
            </div>
            <p class="key-info">
              <strong>Name:</strong> {{ newlyCreatedKey.name }}<br>
              <strong>Created:</strong> {{ newlyCreatedKey.created_at | date:'short' }}<br>
              <strong>Expires:</strong> {{ newlyCreatedKey.expires_at ? (newlyCreatedKey.expires_at | date:'short') : 'Never' }}
            </p>
            <button class="btn btn-primary" (click)="newlyCreatedKey = null">I've Saved My Key</button>
          </div>

          <!-- API Keys List -->
          <div *ngIf="loadingKeys" class="loading">Loading API keys...</div>
          <div *ngIf="!loadingKeys && apiKeys.length === 0" class="empty-state">
            <p>No API keys yet. Generate your first key to get started.</p>
          </div>
          <div *ngIf="!loadingKeys && apiKeys.length > 0" class="keys-list">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Key Preview</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Expires</th>
                  <th>Last Used</th>
                  <th>Usage Count</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let key of apiKeys" [class.inactive]="!key.is_active">
                  <td>{{ key.name }}</td>
                  <td><code>{{ key.key_prefix }}...</code></td>
                  <td>
                    <span class="badge" [class.badge-success]="key.is_active" [class.badge-danger]="!key.is_active">
                      {{ key.is_active ? 'Active' : 'Revoked' }}
                    </span>
                  </td>
                  <td>{{ key.created_at | date:'short' }}</td>
                  <td>{{ key.expires_at ? (key.expires_at | date:'short') : 'Never' }}</td>
                  <td>{{ key.last_used_at ? (key.last_used_at | date:'short') : 'Never' }}</td>
                  <td>{{ key.usage_count }}</td>
                  <td>
                    <button *ngIf="key.is_active" class="btn btn-sm btn-danger" 
                            (click)="confirmRevokeKey(key)">Revoke</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .resource-page { padding: 1.5rem; }
    .banner { padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: 1rem; border: 1px solid; }
    .banner.warning { background: #fff3cd; color: #856404; border-color: #ffeeba; }
    .banner.info { background: #d1ecf1; color: #0c5460; border-color: #bee5eb; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; margin-bottom: 0.25rem; font-weight: 500; }
    .form-group small { display: block; margin-top: 0.25rem; color: #6c757d; font-size: 0.875rem; }
    .form-control { width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
    .form-actions { display: flex; gap: .75rem; justify-content: flex-end; margin-top: 1rem; }
    .btn { padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.875rem; }
    .btn-primary { background: #007bff; color: white; }
    .btn-primary:hover { background: #0056b3; }
    .btn-primary:disabled { background: #ccc; cursor: not-allowed; }
    .btn-secondary { background: #6c757d; color: white; }
    .btn-secondary:hover { background: #545b62; }
    .btn-danger { background: #dc3545; color: white; }
    .btn-danger:hover { background: #c82333; }
    .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
    
    .tabs { display: flex; gap: 0.5rem; border-bottom: 2px solid #dee2e6; margin-bottom: 1.5rem; }
    .tab { padding: 0.75rem 1.5rem; background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; font-size: 1rem; margin-bottom: -2px; }
    .tab:hover { background: #f8f9fa; }
    .tab.active { border-bottom-color: #007bff; color: #007bff; font-weight: 500; }
    
    .tab-content { animation: fadeIn 0.3s; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    
    .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .section-header h3 { margin: 0; }
    
    .create-key-form { background: #f8f9fa; padding: 1.5rem; border-radius: 4px; margin-bottom: 1.5rem; }
    .create-key-form h4 { margin-top: 0; }
    
    .alert { padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; }
    .alert.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .alert h4 { margin-top: 0; }
    
    .key-display { display: flex; gap: 0.5rem; align-items: center; background: white; padding: 0.75rem; border-radius: 4px; margin: 1rem 0; }
    .key-display code { flex: 1; font-family: monospace; word-break: break-all; }
    .key-info { margin: 0.5rem 0; }
    
    .loading { text-align: center; padding: 2rem; color: #6c757d; }
    .empty-state { text-align: center; padding: 3rem; color: #6c757d; }
    
    .keys-list { margin-top: 1rem; }
    .data-table { width: 100%; border-collapse: collapse; background: white; }
    .data-table th, .data-table td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #dee2e6; }
    .data-table th { background: #f8f9fa; font-weight: 500; }
    .data-table tr:hover { background: #f8f9fa; }
    .data-table tr.inactive { opacity: 0.6; }
    .data-table code { background: #f8f9fa; padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.85rem; }
    
    .badge { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 3px; font-size: 0.75rem; font-weight: 500; }
    .badge-success { background: #d4edda; color: #155724; }
    .badge-danger { background: #f8d7da; color: #721c24; }
  `],
  standalone: false
})
export class ProfileComponent implements OnInit {
  // Profile form fields
  email = '';
  current_password = '';
  new_password = '';
  saving = false;
  externallyManagedUsers = false;

  // Tab state
  activeTab: 'profile' | 'api-keys' = 'profile';

  // API Keys state
  apiKeys: APIKey[] = [];
  loadingKeys = false;
  showCreateKeyForm = false;
  creatingKey = false;
  newKeyName = '';
  newKeyExpiresInDays: number | null = null;
  newlyCreatedKey: APIKeyCreateResponse | null = null;

  constructor(private api: ApiService, private auth: AuthService) {}

  ngOnInit(): void {
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
        this.auth.refreshMe();
        alert('Profile updated');
      },
      error: (e) => {
        this.saving = false;
        alert('Update failed: ' + (e?.error?.detail || 'Unknown error'));
      }
    });
  }

  loadAPIKeys(): void {
    this.loadingKeys = true;
    this.api.getAPIKeys(false).subscribe({
      next: (response) => {
        this.apiKeys = response.keys || [];
        this.loadingKeys = false;
      },
      error: (e) => {
        this.loadingKeys = false;
        alert('Failed to load API keys: ' + (e?.error?.detail || 'Unknown error'));
      }
    });
  }

  createAPIKey(): void {
    if (!this.newKeyName.trim()) {
      alert('Please enter a name for the API key');
      return;
    }

    this.creatingKey = true;
    const payload: any = { name: this.newKeyName.trim() };
    if (this.newKeyExpiresInDays) {
      payload.expires_in_days = this.newKeyExpiresInDays;
    }

    this.api.createAPIKey(payload).subscribe({
      next: (response: APIKeyCreateResponse) => {
        this.creatingKey = false;
        this.newlyCreatedKey = response;
        this.showCreateKeyForm = false;
        this.newKeyName = '';
        this.newKeyExpiresInDays = null;
        // Reload the keys list
        this.loadAPIKeys();
      },
      error: (e) => {
        this.creatingKey = false;
        alert('Failed to create API key: ' + (e?.error?.detail || 'Unknown error'));
      }
    });
  }

  confirmRevokeKey(key: APIKey): void {
    if (confirm(`Are you sure you want to revoke the API key "${key.name}"? This action cannot be undone.`)) {
      this.api.revokeAPIKey(key.id).subscribe({
        next: () => {
          alert('API key revoked successfully');
          this.loadAPIKeys();
        },
        error: (e) => {
          alert('Failed to revoke API key: ' + (e?.error?.detail || 'Unknown error'));
        }
      });
    }
  }

  copyToClipboard(text: string): void {
    navigator.clipboard.writeText(text).then(() => {
      alert('API key copied to clipboard!');
    }).catch(() => {
      alert('Failed to copy to clipboard. Please copy manually.');
    });
  }
}
