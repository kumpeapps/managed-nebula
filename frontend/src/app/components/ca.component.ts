import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { CACertificate } from '../models';

@Component({
    selector: 'app-ca',
    template: `
    <app-navbar></app-navbar>
    <div class="resource-page">
      <h2>Certificate Authorities</h2>
      <div class="actions">
        <button class="btn btn-primary" (click)="showCreate = true">New CA</button>
        <button class="btn btn-secondary" (click)="showImport = true">Import CA</button>
      </div>

      <!-- Create CA Modal -->
      <div *ngIf="showCreate" class="modal">
        <div class="modal-content">
          <h3>Create CA</h3>
          <form (ngSubmit)="createCA()" #createForm="ngForm">
            <div class="form-group">
              <label>Name *</label>
              <input class="form-control" name="name" [(ngModel)]="createPayload.name" required />
            </div>
            <div class="form-group">
              <label>Validity (months)</label>
              <input class="form-control" type="number" name="validity" [(ngModel)]="createPayload.validity_months" min="1" />
            </div>
            <div class="form-group">
              <label>Certificate Authority Version</label>
              <select class="form-control" name="cert_version" [(ngModel)]="createPayload.cert_version">
                <option value="v1">v1 CA (Can only sign v1 certificates - for legacy servers)</option>
                <option value="v2">v2 CA (Can sign BOTH v1 and v2 certificates - recommended)</option>
              </select>
              <small class="form-text">
                <strong>Recommended:</strong> Choose v2 CA. It can sign v1 certificates for clients running Nebula &lt; 1.10.0 
                AND v2 certificates for clients running Nebula 1.10.0+. Only choose v1 CA if your server cannot run Nebula 1.10.0+.
              </small>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" (click)="showCreate = false">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="creating || createForm.invalid">{{ creating ? 'Creating...' : 'Create' }}</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Import CA Modal -->
      <div *ngIf="showImport" class="modal">
        <div class="modal-content">
          <h3>Import Existing CA</h3>
          <form (ngSubmit)="importCA()" #importForm="ngForm">
            <div class="form-group">
              <label>Name *</label>
              <input class="form-control" name="name" [(ngModel)]="importPayload.name" required />
            </div>
            <div class="form-group">
              <label>PEM Certificate *</label>
              <textarea class="form-control monospace" rows="6" name="pem_cert" [(ngModel)]="importPayload.pem_cert" required></textarea>
            </div>
            <div class="form-group">
              <label>PEM Private Key (optional)</label>
              <textarea class="form-control monospace" rows="6" name="pem_key" [(ngModel)]="importPayload.pem_key"></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" (click)="showImport = false">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="importing || importForm.invalid">{{ importing ? 'Importing...' : 'Import' }}</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="isLoading" class="loading-container">
        <div class="spinner"></div>
        <p>Loading certificate authorities...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="!isLoading && error" class="error-container">
        <p class="error-message">{{ error }}</p>
        <button (click)="load()" class="btn btn-secondary">Retry</button>
      </div>

      <!-- Empty State -->
      <p *ngIf="!isLoading && !error && !cas.length" class="no-data">No CA certificates.</p>

      <!-- CA Table -->
      <table *ngIf="!isLoading && !error && cas.length" class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Cert Version</th>
            <th>Status</th>
            <th>Can Sign</th>
            <th>Validity</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let ca of cas">
            <td>{{ ca.name }}</td>
            <td>
              <span class="badge" [ngClass]="ca.cert_version === 'v2' ? 'badge-v2' : 'badge-v1'">
                {{ ca.cert_version || 'v1' }}
              </span>
              <span *ngIf="ca.cert_version === 'v2'" class="cert-version-note" title="Can sign both v1 and v2 certificates">✓ Multi-version</span>
            </td>
            <td>
              <span class="badge" [ngClass]="statusClass(ca.status)">{{ ca.status }}</span>
              <span *ngIf="ca.is_active && ca.can_sign" class="badge badge-signing">Signing</span>
            </td>
            <td>
              <span class="badge" [ngClass]="ca.can_sign ? 'badge-yes' : 'badge-no'">{{ ca.can_sign ? 'Yes' : 'No' }}</span>
            </td>
            <td>{{ ca.not_before | localDate:'short' }} → {{ ca.not_after | localDate:'short' }}</td>
            <td class="actions-cell">
              <button *ngIf="ca.can_sign && !ca.is_active" class="btn btn-sm btn-primary" (click)="setSigningCA(ca.id)">Set as Signing</button>
              <button class="btn btn-sm btn-danger" (click)="deleteCA(ca.id)" [disabled]="ca.is_active" [title]="ca.is_active ? 'Cannot delete active CA' : 'Delete CA'">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `,
    styles: [`
    .resource-page { padding:1.5rem; }
    .actions { margin-bottom:1rem; display:flex; gap:.5rem; }
    .table { width:100%; border-collapse:collapse; }
    th, td { padding:.5rem; border-bottom:1px solid #eee; }
    .badge { padding:.25rem .5rem; border-radius:4px; text-transform:capitalize; font-size:.75rem; }
    .badge-current { background:#d4edda; color:#155724; }
    .badge-previous { background:#fff3cd; color:#856404; }
    .badge-expired { background:#f8d7da; color:#721c24; }
    .badge-inactive { background:#e2e3e5; color:#383d41; }
    .badge-signing { background:#007bff; color:#fff; margin-left:0.5rem; }
    .badge-yes { background:#d4edda; color:#155724; }
    .badge-no { background:#f8d7da; color:#721c24; }
    .badge-v1 { background:#e2e3e5; color:#383d41; }
    .badge-v2 { background:#cfe2ff; color:#084298; }
    .cert-version-note { font-size:.7rem; color:#666; margin-left:.5rem; }
    .actions-cell { display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap; }
    .modal { position:fixed; inset:0; background:rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; }
    .modal-content { background:#fff; padding:1.5rem; width:600px; max-width:95%; border-radius:8px; }
    .form-group { margin-bottom:1rem; }
    .form-actions { display:flex; gap:.75rem; justify-content:flex-end; }
    .monospace { font-family:monospace; }
    
    /* Loading and Error States */
    .loading-container, .error-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 3rem 1.5rem;
      text-align: center;
      background: white;
      border-radius: 8px;
    }
    
    .spinner {
      width: 48px;
      height: 48px;
      border: 4px solid #f3f3f3;
      border-top: 4px solid #4CAF50;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 1rem;
    }
    
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    
    .error-message {
      color: #d32f2f;
      margin-bottom: 1rem;
    }
    
    .no-data {
      text-align: center;
      color: #666;
      padding: 2rem;
      font-style: italic;
      background: white;
      border-radius: 8px;
    }

    @media (max-width: 768px) {
      .resource-page { padding: 1rem; }
      .modal-content { padding: 1rem; width: 95%; }
      .form-actions { flex-direction: column; }
      .form-actions button { width: 100%; }
      table { font-size: 0.9rem; }
      th, td { padding: 0.5rem 0.25rem; }
      .table-responsive { overflow-x: auto; }
    }
  `],
    standalone: false
})
export class CAComponent implements OnInit {
  cas: CACertificate[] = [];
  isLoading = false;
  error: string | null = null;
  showCreate = false;
  showImport = false;
  creating = false;
  importing = false;
  createPayload: { name: string; validity_months?: number; cert_version?: string } = { name: '', validity_months: 18, cert_version: 'v1' };
  importPayload: { name: string; pem_cert: string; pem_key?: string } = { name: '', pem_cert: '', pem_key: '' };

  constructor(private api: ApiService) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.isLoading = true;
    this.error = null;
    this.api.getCACertificates().subscribe({
      next: (cas: CACertificate[]) => {
        this.cas = cas;
        this.isLoading = false;
      },
      error: (e: any) => {
        console.error('Failed to load CA list', e);
        this.error = 'Failed to load certificate authorities. Please try again.';
        this.isLoading = false;
      }
    });
  }

  createCA(): void {
    if (!this.createPayload.name) return;
    this.creating = true;
    this.api.createCA(this.createPayload).subscribe({
      next: (created: CACertificate) => {
        this.cas = [...this.cas, created];
        this.showCreate = false;
        this.creating = false;
        this.createPayload = { name: '', validity_months: 18, cert_version: 'v1' };
      },
      error: (e: any) => {
        alert('Create failed: ' + (e.error?.detail || 'Unknown error'));
        this.creating = false;
      }
    });
  }

  importCA(): void {
    if (!this.importPayload.name || !this.importPayload.pem_cert) return;
    this.importing = true;
    this.api.importCA(this.importPayload).subscribe({
      next: (imported: CACertificate) => {
        this.cas = [...this.cas, imported];
        this.showImport = false;
        this.importing = false;
        this.importPayload = { name: '', pem_cert: '', pem_key: '' };
      },
      error: (e: any) => {
        alert('Import failed: ' + (e.error?.detail || 'Unknown error'));
        this.importing = false;
      }
    });
  }

  setSigningCA(id: number): void {
    if (!confirm('Set this CA as the active signing CA? The current signing CA will be marked as previous.')) return;
    this.api.setSigningCA(id).subscribe({
      next: () => this.load(),
      error: (e: any) => alert('Failed to set signing CA: ' + (e.error?.detail || 'Unknown error'))
    });
  }

  deleteCA(id: number): void {
    const ca = this.cas.find(c => c.id === id);
    if (ca?.is_active) {
      alert('Cannot delete active CA. Please set another CA as the signing CA first.');
      return;
    }
    if (!confirm(`Delete CA "${ca?.name}"? This action cannot be undone.`)) return;
    this.api.deleteCA(id).subscribe({
      next: () => {
        this.cas = this.cas.filter(c => c.id !== id);
        console.log(`CA ${id} deleted successfully`);
      },
      error: (e: any) => {
        console.error('Delete CA error:', e);
        alert('Delete failed: ' + (e.error?.detail || 'Unknown error'));
      }
    });
  }

  statusClass(status: string): string {
    return 'badge-' + status;
  }
}
