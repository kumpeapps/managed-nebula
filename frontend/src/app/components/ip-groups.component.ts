import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { IPGroup, IPPool } from '../models';

@Component({
  selector: 'app-ip-groups',
  template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <div class="header">
          <h2>IP Groups</h2>
          <button (click)="showCreateForm = true" class="btn btn-primary">Add IP Group</button>
        </div>
        
        <div *ngIf="showCreateForm" class="modal">
          <div class="modal-content">
            <h3>Create New IP Group</h3>
            <form (ngSubmit)="createIPGroup()" #groupForm="ngForm">
              <div class="form-group">
                <label for="pool">IP Pool *</label>
                <select id="pool" [(ngModel)]="newGroup.pool_id" name="pool_id" required class="form-control">
                  <option [ngValue]="null">-- Select IP Pool --</option>
                  <option *ngFor="let pool of ipPools" [ngValue]="pool.id">{{ pool.cidr }}</option>
                </select>
              </div>
              
              <div class="form-group">
                <label for="name">Group Name *</label>
                <input type="text" id="name" [(ngModel)]="newGroup.name" name="name" required class="form-control" 
                       placeholder="e.g., 'Production Servers'">
              </div>
              
              <div class="form-group">
                <label for="start_ip">Start IP *</label>
                <input type="text" id="start_ip" [(ngModel)]="newGroup.start_ip" name="start_ip" required class="form-control" 
                       placeholder="e.g., '10.100.0.10'">
              </div>
              
              <div class="form-group">
                <label for="end_ip">End IP *</label>
                <input type="text" id="end_ip" [(ngModel)]="newGroup.end_ip" name="end_ip" required class="form-control" 
                       placeholder="e.g., '10.100.0.50'">
              </div>
              
              <div class="form-actions">
                <button type="button" (click)="showCreateForm = false" class="btn btn-secondary">Cancel</button>
                <button type="submit" [disabled]="groupForm.invalid || creating" class="btn btn-primary">{{ creating ? 'Creating...' : 'Create' }}</button>
              </div>
            </form>
          </div>
        </div>
        
        <div *ngIf="showEditForm && selectedGroup" class="modal">
          <div class="modal-content">
            <h3>Edit IP Group</h3>
            <form (ngSubmit)="updateIPGroup()" #editForm="ngForm">
              <div class="form-group">
                <label for="edit_name">Group Name *</label>
                <input type="text" id="edit_name" [(ngModel)]="selectedGroup.name" name="name" required class="form-control">
              </div>
              
              <div class="form-group">
                <label for="edit_start_ip">Start IP *</label>
                <input type="text" id="edit_start_ip" [(ngModel)]="selectedGroup.start_ip" name="start_ip" required class="form-control">
              </div>
              
              <div class="form-group">
                <label for="edit_end_ip">End IP *</label>
                <input type="text" id="edit_end_ip" [(ngModel)]="selectedGroup.end_ip" name="end_ip" required class="form-control">
              </div>
              
              <div class="form-actions">
                <button type="button" (click)="showEditForm = false; selectedGroup = null" class="btn btn-secondary">Cancel</button>
                <button type="submit" [disabled]="editForm.invalid || updating" class="btn btn-primary">{{ updating ? 'Updating...' : 'Update' }}</button>
              </div>
            </form>
          </div>
        </div>
        
        <div class="filters">
          <label for="poolFilter">Filter by Pool:</label>
          <select id="poolFilter" [(ngModel)]="filterPoolId" (ngModelChange)="loadIPGroups()" class="form-control">
            <option [ngValue]="null">All Pools</option>
            <option *ngFor="let pool of ipPools" [ngValue]="pool.id">{{ pool.cidr }}</option>
          </select>
        </div>
        
        <div class="groups-list">
          <div *ngIf="ipGroups.length > 0" class="groups-grid">
            <div *ngFor="let group of ipGroups" class="group-card">
              <div class="group-header">
                <h3 class="group-name">{{ group.name }}</h3>
                <span class="pool-badge">Pool: {{ getPoolName(group.pool_id) }}</span>
              </div>
              <div class="group-meta">
                <span><strong>Range:</strong> {{ group.start_ip }} - {{ group.end_ip }}</span>
                <span><strong>Clients:</strong> {{ group.client_count }}</span>
              </div>
              <div class="group-actions">
                <button (click)="editGroup(group)" class="btn btn-sm btn-secondary">Edit</button>
                <button (click)="deleteIPGroup(group.id)" class="btn btn-sm btn-danger">Delete</button>
              </div>
            </div>
          </div>
          <p *ngIf="ipGroups.length === 0">No IP groups found. Create one to organize your IP allocations.</p>
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
    
    .filters {
      display: flex;
      gap: 1rem;
      align-items: center;
      margin-bottom: 1.5rem;
      padding: 1rem;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .filters label {
      font-weight: 600;
      color: #666;
    }
    
    .filters select {
      width: auto;
      min-width: 200px;
    }
    
    .groups-list {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .groups-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 1.5rem;
    }
    
    .group-card {
      border: 1px solid #eee;
      border-radius: 8px;
      padding: 1.5rem;
      background: #fafafa;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .group-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .group-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1rem;
      gap: 1rem;
    }
    
    .group-name {
      margin: 0;
      color: #333;
      font-size: 1.25rem;
      flex: 1;
    }
    
    .pool-badge {
      background: #4CAF50;
      color: white;
      padding: 0.25rem 0.75rem;
      border-radius: 4px;
      font-size: 0.875rem;
      white-space: nowrap;
    }
    
    .group-meta {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      color: #666;
      font-size: 0.875rem;
      margin-bottom: 1rem;
      border-top: 1px solid #ddd;
      padding-top: 0.75rem;
    }
    
    .group-meta span {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    
    .group-actions {
      display: flex;
      gap: 0.5rem;
      justify-content: flex-end;
    }
    
    .btn {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-weight: 500;
      transition: background 0.3s;
    }
    
    .btn-primary {
      background: #2196F3;
      color: white;
    }
    
    .btn-primary:hover {
      background: #1976D2;
    }
    
    .btn-primary:disabled {
      background: #ccc;
      cursor: not-allowed;
    }
    
    .btn-secondary {
      background: #666;
      color: white;
    }
    
    .btn-secondary:hover {
      background: #555;
    }
    
    .btn-danger {
      background: #f44336;
      color: white;
    }
    
    .btn-danger:hover {
      background: #d32f2f;
    }
    
    .btn-sm {
      padding: 0.375rem 0.75rem;
      font-size: 0.875rem;
    }
    
    .modal {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }
    
    .modal-content {
      background: white;
      padding: 2rem;
      border-radius: 8px;
      width: 90%;
      max-width: 500px;
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
      font-size: 1rem;
    }
    
    .form-control:focus {
      outline: none;
      border-color: #2196F3;
    }
    
    .form-actions {
      display: flex;
      gap: 1rem;
      justify-content: flex-end;
      margin-top: 1.5rem;
    }
    
    p {
      text-align: center;
      padding: 2rem;
      color: #666;
    }
  `]
})
export class IPGroupsComponent implements OnInit {
  ipGroups: IPGroup[] = [];
  ipPools: IPPool[] = [];
  filterPoolId: number | null = null;
  showCreateForm = false;
  showEditForm = false;
  newGroup: any = { pool_id: null, name: '', start_ip: '', end_ip: '' };
  selectedGroup: IPGroup | null = null;
  creating = false;
  updating = false;

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadIPPools();
    this.loadIPGroups();
  }

  loadIPPools(): void {
    this.apiService.getIPPools().subscribe({
      next: (pools: IPPool[]) => {
        this.ipPools = pools;
      },
      error: (error: any) => {
        console.error('Failed to load IP pools:', error);
        alert('Failed to load IP pools: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

  loadIPGroups(): void {
    this.apiService.getIPGroups(this.filterPoolId || undefined).subscribe({
      next: (groups: IPGroup[]) => {
        this.ipGroups = groups;
      },
      error: (error: any) => {
        console.error('Failed to load IP groups:', error);
        alert('Failed to load IP groups: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }

  getPoolName(poolId: number): string {
    const pool = this.ipPools.find(p => p.id === poolId);
    return pool ? pool.cidr : `Pool ${poolId}`;
  }

  createIPGroup(): void {
    if (this.creating) return;
    
    this.creating = true;
    this.apiService.createIPGroup(this.newGroup).subscribe({
      next: (group: IPGroup) => {
        this.ipGroups.push(group);
        this.showCreateForm = false;
        this.newGroup = { pool_id: null, name: '', start_ip: '', end_ip: '' };
        this.creating = false;
      },
      error: (error: any) => {
        console.error('Failed to create IP group:', error);
        alert('Failed to create IP group: ' + (error.error?.detail || 'Unknown error'));
        this.creating = false;
      }
    });
  }

  editGroup(group: IPGroup): void {
    this.selectedGroup = { ...group };
    this.showEditForm = true;
  }

  updateIPGroup(): void {
    if (!this.selectedGroup || this.updating) return;
    
    this.updating = true;
    const updates = {
      name: this.selectedGroup.name,
      start_ip: this.selectedGroup.start_ip,
      end_ip: this.selectedGroup.end_ip
    };
    
    this.apiService.updateIPGroup(this.selectedGroup.id, updates).subscribe({
      next: (updated: IPGroup) => {
        const index = this.ipGroups.findIndex(g => g.id === updated.id);
        if (index !== -1) {
          this.ipGroups[index] = updated;
        }
        this.showEditForm = false;
        this.selectedGroup = null;
        this.updating = false;
      },
      error: (error: any) => {
        console.error('Failed to update IP group:', error);
        alert('Failed to update IP group: ' + (error.error?.detail || 'Unknown error'));
        this.updating = false;
      }
    });
  }

  deleteIPGroup(id: number): void {
    if (!confirm('Are you sure you want to delete this IP group? This will fail if there are clients using IPs from this group.')) {
      return;
    }
    
    this.apiService.deleteIPGroup(id).subscribe({
      next: () => {
        this.ipGroups = this.ipGroups.filter(g => g.id !== id);
      },
      error: (error: any) => {
        console.error('Failed to delete IP group:', error);
        alert('Failed to delete IP group: ' + (error.error?.detail || 'Clients may be using IPs from this group'));
      }
    });
  }
}
