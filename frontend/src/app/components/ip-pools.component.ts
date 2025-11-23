import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { IPPool, Client } from '../models';
import { Router } from '@angular/router';

@Component({
    selector: 'app-ip-pools',
    template: `
    <app-navbar></app-navbar>
    <div class="resource-page">
      <h2>IP Pools</h2>
      <div class="actions">
        <button class="btn btn-primary" (click)="showForm = true">New Pool</button>
      </div>

      <div *ngIf="showForm" class="modal">
        <div class="modal-content">
          <h3>Create IP Pool</h3>
          <form (ngSubmit)="createPool()" #poolForm="ngForm">
            <div class="form-group">
              <label>CIDR *</label>
              <input class="form-control" name="cidr" [(ngModel)]="newPool.cidr" required placeholder="10.0.0.0/24" />
            </div>
            <div class="form-group">
              <label>Description</label>
              <input class="form-control" name="description" [(ngModel)]="newPool.description" />
            </div>
            <div class="form-actions">
              <button type="button" (click)="showForm = false" class="btn btn-secondary">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="creating || poolForm.invalid">{{ creating ? 'Creating...' : 'Create' }}</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Loading State -->
      <div *ngIf="isLoading" class="loading-container">
        <div class="spinner"></div>
        <p>Loading IP pools...</p>
      </div>

      <!-- Error State -->
      <div *ngIf="!isLoading && error" class="error-container">
        <p class="error-message">{{ error }}</p>
        <button (click)="load()" class="btn btn-secondary">Retry</button>
      </div>

      <!-- Empty State -->
      <p *ngIf="!isLoading && !error && !pools.length" class="no-data">No IP pools defined.</p>

      <!-- Pools Table -->
      <table *ngIf="!isLoading && !error && pools.length" class="table">
        <thead>
          <tr>
            <th>CIDR</th>
            <th>Description</th>
            <th>Allocated</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let p of pools">
            <td>{{ p.cidr }}</td>
            <td>
              <input [value]="p.description || ''" class="form-control" (change)="updatePoolDescription(p, $event)" />
            </td>
            <td>{{ p.allocated_count }}</td>
            <td>
              <button class="btn btn-sm btn-secondary" (click)="openClientsModal(p)">View Clients</button>
              <button class="btn btn-sm btn-danger" (click)="deletePool(p.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      
      <!-- Pool Clients Modal -->
      <div class="modal" *ngIf="showClientsModal" (click)="closeClientsModal()">
        <div class="modal-content" (click)="$event.stopPropagation()" style="max-width:800px;">
          <h3>Clients in {{ currentPool?.cidr }}</h3>
          <table *ngIf="poolClients.length" class="table">
            <thead>
              <tr><th>ID</th><th>Name</th><th>IP</th><th>Groups</th><th>Rulesets</th><th>Actions</th></tr>
            </thead>
            <tbody>
              <tr *ngFor="let c of poolClients">
                <td>{{ c.id }}</td>
                <td>{{ c.name }}</td>
                <td>{{ c.ip_address || '—' }}</td>
                <td>
                  <span *ngFor="let g of c.groups" class="tag">{{ g.name }}</span>
                </td>
                <td>
                  <span *ngFor="let rs of c.firewall_rulesets" class="tag">{{ rs.name }}</span>
                </td>
                <td>
                  <button class="btn btn-sm btn-primary" (click)="viewClient(c.id)">View</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p *ngIf="!poolClients.length">No clients assigned to this pool.</p>
          <div class="form-actions" style="margin-top:1rem;">
            <button class="btn btn-secondary" (click)="closeClientsModal()">Close</button>
          </div>
        </div>
      </div>
    </div>
  `,
    styles: [`
    .resource-page { padding: 1.5rem; }
    .actions { margin-bottom: 1rem; }
    .table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.5rem; border-bottom: 1px solid #eee; vertical-align: top; }
    .form-control { width: 100%; }
    .modal { position: fixed; inset:0; background: rgba(0,0,0,.45); display:flex; align-items:center; justify-content:center; overflow-y: auto; padding: 1rem; }
    .modal-content { background:#fff; padding:1.5rem; width:600px; max-width:95%; border-radius:8px; max-height: 90vh; overflow-y: auto; margin: auto; }
    .form-group { margin-bottom: 1rem; }
    .form-actions { display:flex; gap:.75rem; justify-content:flex-end; }
    
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
      .page { padding: 1rem; }
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
export class IPPoolsComponent implements OnInit {
  pools: IPPool[] = [];
  isLoading = false;
  error: string | null = null;
  showForm = false;
  creating = false;
  newPool: { cidr: string; description?: string } = { cidr: '', description: '' };

  showClientsModal = false;
  poolClients: Client[] = [];
  currentPool: IPPool | null = null;

  constructor(private api: ApiService, private router: Router) {}

  ngOnInit(): void { this.load(); }

  load(): void {
    this.isLoading = true;
    this.error = null;
    this.api.getIPPools().subscribe({
      next: (p: IPPool[]) => {
        this.pools = p;
        this.isLoading = false;
      },
      error: (e: any) => {
        console.error('Failed to load pools', e);
        this.error = 'Failed to load IP pools. Please try again.';
        this.isLoading = false;
      }
    });
  }

  createPool(): void {
    if (!this.newPool.cidr || !this.newPool.cidr.includes('/')) {
      alert('CIDR must include a subnet, e.g., 10.0.0.0/24');
      return;
    }
    this.creating = true;
    this.api.createIPPool(this.newPool).subscribe({
      next: (created: IPPool) => {
        this.pools = [...this.pools, created];
        this.newPool = { cidr: '', description: '' };
        this.creating = false;
        this.showForm = false;
      },
      error: (e: any) => {
        alert('Create failed: ' + (e.error?.detail || 'Unknown error'));
        this.creating = false;
      }
    });
  }

  updatePoolDescription(pool: IPPool, event: Event): void {
    const target = event.target as HTMLInputElement;
    this.updatePool(pool, { description: target.value });
  }

  updatePool(pool: IPPool, patch: { cidr?: string; description?: string }): void {
    const payload = { cidr: patch.cidr, description: patch.description };
    this.api.updateIPPool(pool.id, payload).subscribe({
      next: (updated: IPPool) => Object.assign(pool, updated),
      error: (e: any) => alert('Update failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }

  deletePool(id: number): void {
    if (!confirm('Delete this pool?')) return;
    this.api.deleteIPPool(id).subscribe({
      next: () => (this.pools = this.pools.filter(p => p.id !== id)),
      error: (e: any) => alert('Delete failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }

  openClientsModal(pool: IPPool): void {
    this.currentPool = pool;
    this.showClientsModal = true;
    this.poolClients = [];
    this.api.getPoolClients(pool.id).subscribe({
      next: (clients: Client[]) => this.poolClients = clients,
      error: (e: any) => {
        console.error('Failed to load pool clients', e);
        this.poolClients = [];
      }
    });
  }

  closeClientsModal(): void {
    this.showClientsModal = false;
    this.poolClients = [];
    this.currentPool = null;
  }

  viewClient(id: number): void {
    this.closeClientsModal();
    this.router.navigate(['/clients', id]);
  }
}
