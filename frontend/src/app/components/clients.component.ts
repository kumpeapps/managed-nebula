import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { Client, Group, IPPool, IPGroup, AvailableIP, FirewallRuleset, ClientCreateRequest } from '../models';

@Component({
  selector: 'app-clients',
  template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <div class="header">
          <h2>Clients</h2>
          <div class="header-actions">
            <span class="count">{{ clients.length }} total</span>
            <button *ngIf="isAdmin" (click)="openCreateModal()" class="btn btn-primary">
              <span class="icon">+</span> Create Client
            </button>
          </div>
        </div>
        
        <div class="clients-list">
          <table *ngIf="clients.length > 0">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Owner</th>
                <th>IP Address</th>
                <th>Status</th>
                <th>Groups</th>
                <th>Rulesets</th>
                <th>Last Config Download</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let client of clients">
                <td>{{ client.id }}</td>
                <td>
                  <strong>{{ client.name }}</strong>
                </td>
                <td>
                  <span *ngIf="client.owner" class="text-muted">{{ client.owner.email }}</span>
                  <span *ngIf="!client.owner" class="text-muted">—</span>
                </td>
                <td>{{ client.ip_address || 'Not assigned' }}</td>
                <td>
                  <div class="status-badges">
                    <span *ngIf="client.is_lighthouse" class="badge badge-info">Lighthouse</span>
                    <span *ngIf="client.is_blocked" class="badge badge-danger">Blocked</span>
                    <span *ngIf="!client.is_lighthouse && !client.is_blocked" class="badge badge-success">Active</span>
                  </div>
                </td>
                <td>
                  <div class="group-tags">
                    <span *ngFor="let group of client.groups" class="tag">{{ group.name }}</span>
                    <span *ngIf="client.groups.length === 0" class="text-muted">—</span>
                  </div>
                </td>
                <td>
                  <div class="group-tags">
                    <span *ngFor="let rs of client.firewall_rulesets" class="tag">{{ rs.name }}</span>
                    <span *ngIf="client.firewall_rulesets?.length === 0" class="text-muted">—</span>
                  </div>
                </td>
                <td>
                  <span *ngIf="client.last_config_download_at">{{ client.last_config_download_at | date:'short' }}</span>
                  <span *ngIf="!client.last_config_download_at" class="text-muted">Never</span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button (click)="viewClient(client.id)" class="btn btn-sm btn-primary">View</button>
                    <button *ngIf="isAdmin" (click)="deleteClient(client.id)" class="btn btn-sm btn-danger">Delete</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
          <p *ngIf="clients.length === 0">No clients found.</p>
        </div>
      </div>

      <!-- Create Client Modal -->
      <div class="modal" *ngIf="showCreateModal" (click)="showCreateModal = false">
        <div class="modal-content" (click)="$event.stopPropagation()">
          <h3>Create New Client</h3>
          <form (ngSubmit)="createClient()">
            <div class="form-group">
              <label>Client Name *</label>
              <input type="text" class="form-control" [(ngModel)]="newClient.name" name="name" required>
            </div>
            
            <div class="form-group">
              <label>
                <input type="checkbox" [(ngModel)]="newClient.is_lighthouse" name="is_lighthouse">
                Lighthouse
              </label>
            </div>
            
            <div class="form-group" *ngIf="newClient.is_lighthouse">
              <label>Public IP (Required for Lighthouse)</label>
              <input type="text" class="form-control" [(ngModel)]="newClient.public_ip" name="public_ip" placeholder="e.g., 1.2.3.4:4242">
            </div>

            <hr>
            <div class="form-group">
              <label>IP Pool</label>
              <select class="form-control" [(ngModel)]="newClient.pool_id" name="pool_id" (change)="onPoolChange()">
                <option [ngValue]="null">Auto-select default pool</option>
                <option *ngFor="let pool of ipPools" [ngValue]="pool.id">{{ pool.cidr }} ({{ pool.description || 'no description' }})</option>
              </select>
            </div>

            <div class="form-group" *ngIf="newClient.pool_id">
              <label>IP Group (optional)</label>
              <select class="form-control" [(ngModel)]="newClient.ip_group_id" name="ip_group_id" (change)="onIPGroupChange()">
                <option [ngValue]="null">All IPs in pool</option>
                <option *ngFor="let g of ipGroups" [ngValue]="g.id">{{ g.name }} ({{ g.start_ip }} - {{ g.end_ip }})</option>
              </select>
            </div>

            <div class="form-group" *ngIf="newClient.pool_id">
              <label>IP Address</label>
              <label style="display:block; margin-bottom:0.5rem;">
                <input type="checkbox" [(ngModel)]="useManualIP" name="use_manual_ip"> Enter manually
              </label>
              <ng-container *ngIf="useManualIP; else autoIpSelect">
                <input type="text" class="form-control" [(ngModel)]="newClient.ip_address" name="ip_address" placeholder="e.g., 10.100.0.42">
              </ng-container>
              <ng-template #autoIpSelect>
                <select class="form-control" [(ngModel)]="newClient.ip_address" name="ip_address_select">
                  <option [ngValue]="null">Auto-allocate</option>
                  <option *ngFor="let ip of availableIPs" [ngValue]="ip.ip_address">{{ ip.ip_address }}</option>
                </select>
              </ng-template>
              <small class="text-muted">We list up to 100 available IPs. Choose one or leave as Auto-allocate.</small>
            </div>

            <hr>
            <div class="form-group">
              <label>Groups</label>
              <div class="checkbox-grid">
                <label *ngFor="let g of nebulaGroups">
                  <input type="checkbox" [checked]="selectedGroups.has(g.id)" (change)="toggleGroup(g.id)"> {{ g.name }}
                </label>
              </div>
            </div>

            <div class="form-group">
              <label>Firewall Rulesets</label>
              <div class="checkbox-grid">
                <label *ngFor="let rs of firewallRulesets">
                  <input type="checkbox" [checked]="selectedRulesets.has(rs.id)" (change)="toggleRuleset(rs.id)"> {{ rs.name }}
                </label>
              </div>
            </div>
            
            <div class="form-actions">
              <button type="button" (click)="showCreateModal = false" class="btn btn-secondary">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="!newClient.name">Create</button>
            </div>
          </form>
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
    
    .header-actions {
      display: flex;
      gap: 1rem;
      align-items: center;
    }
    
    .icon {
      font-weight: bold;
    }
    
    h2 {
      margin: 0;
      color: #333;
    }
    
    .clients-list {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    table {
      width: 100%;
      border-collapse: collapse;
    }
    
    th, td {
      text-align: left;
      padding: 0.75rem;
      border-bottom: 1px solid #eee;
    }
    
    th {
      background: #f9f9f9;
      font-weight: 600;
      color: #666;
    }
    
    .badge {
      padding: 0.25rem 0.75rem;
      border-radius: 12px;
      font-size: 0.85rem;
      font-weight: 500;
      margin-right: 0.25rem;
    }
    
    .badge-success {
      background: #d4edda;
      color: #155724;
    }
    
    .badge-danger {
      background: #f8d7da;
      color: #721c24;
    }
    
    .badge-info {
      background: #d1ecf1;
      color: #0c5460;
    }
    
    .badge-secondary {
      background: #e2e3e5;
      color: #383d41;
    }
    
    .badge-warning {
      background: #fff3cd;
      color: #856404;
    }
    
    .status-badges {
      display: flex;
      gap: 0.25rem;
      flex-wrap: wrap;
    }
    
    .group-tags {
      display: flex;
      gap: 0.25rem;
      flex-wrap: wrap;
    }
    
    .tag {
      background: #e0e0e0;
      color: #333;
      padding: 0.2rem 0.5rem;
      border-radius: 10px;
      font-size: 0.8rem;
    }
    
    .text-muted {
      color: #999;
    }
    
    .action-buttons {
      display: flex;
      gap: 0.5rem;
    }
    
    .header-info {
      color: #666;
    }
    
    .count {
      font-weight: 600;
      color: #4CAF50;
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
      z-index: 1000;
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
    
    .form-actions {
      display: flex;
      gap: 1rem;
      justify-content: flex-end;
      margin-top: 1.5rem;
    }
  `]
})
export class ClientsComponent implements OnInit {
  clients: Client[] = [];
  isAdmin = this.authService.isAdmin();
  showCreateModal = false;
  newClient: ClientCreateRequest = {
    name: '',
    is_lighthouse: false,
    public_ip: null,
    is_blocked: false,
    group_ids: [],
    firewall_ruleset_ids: [],
    pool_id: null,
    ip_group_id: null,
    ip_address: null,
  };
  
  ipPools: IPPool[] = [];
  ipGroups: IPGroup[] = [];
  availableIPs: AvailableIP[] = [];
  nebulaGroups: Group[] = [];
  firewallRulesets: FirewallRuleset[] = [];
  selectedGroups: Set<number> = new Set();
  selectedRulesets: Set<number> = new Set();
  useManualIP = false;

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadClients();
    this.loadPoolsGroupsRulesets();
  }

  openCreateModal(): void {
    this.showCreateModal = true;
    this.resetCreateForm();
    this.loadPoolsGroupsRulesets();
  }

  resetCreateForm(): void {
    this.newClient = {
      name: '',
      is_lighthouse: false,
      public_ip: null,
      is_blocked: false,
      group_ids: [],
      firewall_ruleset_ids: [],
      pool_id: null,
      ip_group_id: null,
      ip_address: null,
    };
    this.selectedGroups.clear();
    this.selectedRulesets.clear();
    this.useManualIP = false;
    this.ipGroups = [];
    this.availableIPs = [];
  }

  loadPoolsGroupsRulesets(): void {
  this.apiService.getIPPools().subscribe({ next: (pools: IPPool[]) => this.ipPools = pools });
  this.apiService.getGroups().subscribe({ next: (gs: Group[]) => this.nebulaGroups = gs });
  this.apiService.getFirewallRulesets().subscribe({ next: (rs: FirewallRuleset[]) => this.firewallRulesets = rs });
  }

  onPoolChange(): void {
    this.newClient.ip_group_id = null;
    this.newClient.ip_address = null;
    this.ipGroups = [];
    this.availableIPs = [];
    if (this.newClient.pool_id) {
  this.apiService.getIPGroups(this.newClient.pool_id).subscribe({ next: (gs: IPGroup[]) => this.ipGroups = gs });
      this.loadAvailableIPs();
    }
  }

  onIPGroupChange(): void {
    this.newClient.ip_address = null;
    this.loadAvailableIPs();
  }

  loadAvailableIPs(): void {
    if (!this.newClient.pool_id) return;
    this.apiService.getAvailableIPs(this.newClient.pool_id, this.newClient.ip_group_id || undefined)
      .subscribe({ next: (ips: AvailableIP[]) => this.availableIPs = ips });
  }

  toggleGroup(id: number): void {
    if (this.selectedGroups.has(id)) this.selectedGroups.delete(id); else this.selectedGroups.add(id);
  }

  toggleRuleset(id: number): void {
    if (this.selectedRulesets.has(id)) this.selectedRulesets.delete(id); else this.selectedRulesets.add(id);
  }

  loadClients(): void {
    this.apiService.getClients().subscribe({
      next: (clients: Client[]) => {
        this.clients = clients;
      },
      error: (error: unknown) => {
        console.error('Failed to load clients:', error);
      }
    });
  }

  viewClient(id: number): void {
    this.router.navigate(['/clients', id]);
  }

  deleteClient(id: number): void {
    if (confirm('Are you sure you want to delete this client? This will remove all associated data.')) {
      this.apiService.deleteClient(id).subscribe({
        next: () => {
          this.loadClients();
        },
        error: (error: any) => {
          console.error('Failed to delete client:', error);
          alert('Failed to delete client: ' + (error.error?.detail || 'Unknown error'));
        }
      });
    }
  }

  createClient(): void {
    if (!this.newClient.name) {
      alert('Client name is required');
      return;
    }

    if (this.newClient.is_lighthouse && !this.newClient.public_ip) {
      alert('Public IP is required for lighthouse clients');
      return;
    }

    const payload: ClientCreateRequest = {
      ...this.newClient,
      group_ids: Array.from(this.selectedGroups),
      firewall_ruleset_ids: Array.from(this.selectedRulesets),
    };

    this.apiService.createClient(payload).subscribe({
      next: (client: Client) => {
        this.showCreateModal = false;
        this.loadClients();
        alert(`Client created successfully! Token: ${client.token || 'N/A'}`);
      },
      error: (error: any) => {
        console.error('Failed to create client:', error);
        alert('Failed to create client: ' + (error.error?.detail || 'Unknown error'));
      }
    });
  }
}
