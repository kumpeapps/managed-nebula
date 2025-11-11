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

      <table *ngIf="cas.length" class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Validity</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let ca of cas">
            <td>{{ ca.name }}</td>
            <td>
              <span class="badge" [ngClass]="statusClass(ca.status)">{{ ca.status }}</span>
            </td>
            <td>{{ ca.not_before | date:'shortDate' }} → {{ ca.not_after | date:'shortDate' }}</td>
            <td>
              <button class="btn btn-sm btn-danger" (click)="deleteCA(ca.id)" [disabled]="ca.is_active">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p *ngIf="!cas.length">No CA certificates.</p>
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
    .modal { position:fixed; inset:0; background:rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; }
    .modal-content { background:#fff; padding:1.5rem; width:600px; max-width:95%; border-radius:8px; }
    .form-group { margin-bottom:1rem; }
    .form-actions { display:flex; gap:.75rem; justify-content:flex-end; }
    .monospace { font-family:monospace; }
  `]
})
export class CAComponent implements OnInit {
  cas: CACertificate[] = [];
  showCreate = false;
  showImport = false;
  creating = false;
  importing = false;
  createPayload: { name: string; validity_months?: number } = { name: '', validity_months: 18 };
  importPayload: { name: string; pem_cert: string; pem_key?: string } = { name: '', pem_cert: '', pem_key: '' };

  constructor(private api: ApiService) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.api.getCACertificates().subscribe({
      next: (cas: CACertificate[]) => (this.cas = cas),
      error: (e: any) => console.error('Failed to load CA list', e)
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
        this.createPayload = { name: '', validity_months: 18 };
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

  deleteCA(id: number): void {
    if (!confirm('Delete this CA? (Cannot delete active)')) return;
    this.api.deleteCA(id).subscribe({
      next: () => (this.cas = this.cas.filter(c => c.id !== id)),
      error: (e: any) => alert('Delete failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }

  statusClass(status: string): string {
    return 'badge-' + status;
  }
}
