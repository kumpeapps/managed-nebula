import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';
import { NotificationService } from '../services/notification.service';
import { Client, Group, FirewallRuleset, ClientCertificate, ClientConfigDownload } from '../models';

@Component({
    selector: 'app-client-detail',
    template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <div class="header">
          <div>
            <button (click)="goBack()" class="btn btn-secondary">← Back to Clients</button>
            <h2>{{ client?.name || 'Client Details' }}</h2>
          </div>
          <div class="header-actions">
            <button *ngIf="isAdmin" (click)="downloadConfig()" class="btn btn-primary">
              <span class="icon">⬇</span> Download Config
            </button>
            <button *ngIf="isAdmin" (click)="downloadDockerCompose()" class="btn btn-secondary">
              <span class="icon">🐳</span> Download Docker Compose
            </button>
          </div>
        </div>

        <div class="detail-container" *ngIf="client">
          <!-- Tabs -->
          <div class="tabs">
            <button 
              class="tab" 
              [class.active]="activeTab === 'details'"
              (click)="activeTab = 'details'">
              Details
            </button>
            <button 
              class="tab" 
              [class.active]="activeTab === 'groups'"
              (click)="activeTab = 'groups'">
              Groups ({{ client.groups.length }})
            </button>
            <button 
              class="tab" 
              [class.active]="activeTab === 'firewall'"
              (click)="activeTab = 'firewall'">
              Firewall Rulesets
            </button>
            <button 
              class="tab" 
              [class.active]="activeTab === 'certificates'"
              (click)="activeTab = 'certificates'; loadCertificates()">
              Certificates
            </button>
          </div>

          <!-- Details Tab -->
          <div class="tab-content" *ngIf="activeTab === 'details'">
            <div class="form-section">
              <h3>Basic Information</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>Name</label>
                  <input type="text" class="form-control" [(ngModel)]="client.name" (blur)="saveDetails()">
                </div>
              </div>

              <h3>IP Configuration</h3>
              <div class="form-row">
                <div class="form-group">
                  <label>IP Pool</label>
                  <select class="form-control" [(ngModel)]="selectedPoolId" (change)="onPoolChange()">
                    <option [ngValue]="null">-- Select Pool --</option>
                    <option *ngFor="let pool of allIPPools" [ngValue]="pool.id">{{ pool.cidr }} - {{ pool.description || 'No description' }}</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>IP Group (Optional)</label>
                  <select class="form-control" [(ngModel)]="selectedIPGroupId" (change)="onIPGroupChange()" [disabled]="!selectedPoolId">
                    <option [ngValue]="null">All IPs in pool</option>
                    <option *ngFor="let group of allIPGroups" [ngValue]="group.id">{{ group.name }} ({{ group.start_ip }} - {{ group.end_ip }})</option>
                  </select>
                </div>
              </div>

              <div class="form-row" *ngIf="selectedPoolId">
                <div class="form-group">
                  <label>IP Address</label>
                  <label style="display:block; margin-bottom:0.5rem;">
                    <input type="checkbox" [(ngModel)]="useManualIP"> Enter manually
                  </label>
                  <ng-container *ngIf="useManualIP; else autoIpSelect">
                    <input type="text" class="form-control" [(ngModel)]="newIPAddress" placeholder="e.g., 10.0.0.5">
                  </ng-container>
                  <ng-template #autoIpSelect>
                    <select class="form-control" [(ngModel)]="newIPAddress">
                      <option [ngValue]="client.ip_address">{{ client.ip_address || 'Current IP' }}</option>
                      <option *ngFor="let ip of availableIPs" [ngValue]="ip.ip_address">{{ ip.ip_address }}</option>
                    </select>
                  </ng-template>
                  <small class="text-muted">Select from available IPs or enter manually. We list up to 100 available IPs.</small>
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <button class="btn btn-primary" (click)="saveIPAddress()" [disabled]="!selectedPoolId">Update IP Configuration</button>
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>
                    <input type="checkbox" [(ngModel)]="client.is_lighthouse" (change)="saveDetails()">
                    Lighthouse
                  </label>
                  <p class="help-text">Lighthouses act as connection coordinators in the mesh</p>
                </div>
                <div class="form-group" *ngIf="client.is_lighthouse">
                  <label>Public IP (Required for Lighthouses)</label>
                  <input type="text" class="form-control" [(ngModel)]="client.public_ip" (blur)="saveDetails()" 
                         placeholder="e.g., 1.2.3.4:4242">
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>
                    <input type="checkbox" [(ngModel)]="client.is_blocked" (change)="saveDetails()">
                    Blocked
                  </label>
                  <p class="help-text">Blocked clients cannot download configs or connect</p>
                </div>
              </div>

              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Created:</span>
                  <span>{{ client.created_at | date:'medium' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Config Last Changed:</span>
                  <span>{{ (client.config_last_changed_at | date:'medium') || 'Never' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Last Config Download:</span>
                  <span>{{ (client.last_config_download_at | date:'medium') || 'Never' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Owner:</span>
                  <span *ngIf="client.owner">{{ client.owner.email }}</span>
                  <span *ngIf="!client.owner" class="text-muted">Unassigned</span>
                </div>
                <div class="info-item" *ngIf="isAdmin && client.token">
                  <span class="label">Token:</span>
                  <code>{{ client.token }}</code>
                </div>
              </div>
            </div>

            <!-- Ownership & Permissions Section -->
            <div class="form-section" *ngIf="isAdmin">
              <h3>Ownership & Permissions</h3>
              
              <!-- Owner Reassignment (Admin Only) -->
              <div class="form-group">
                <label>Reassign Owner</label>
                <select class="form-control" [(ngModel)]="selectedOwnerId" (change)="reassignOwner()">
                  <option [value]="client.owner?.id">{{ client.owner?.email || 'Current Owner' }}</option>
                  <option *ngFor="let user of allUsers" [value]="user.id">{{ user.email }}</option>
                </select>
              </div>

              <!-- Permissions Management -->
              <div class="permissions-section">
                <h4>Granted Permissions</h4>
                <p class="help-text">Grant other users view, update, or config download access</p>
                
                <table *ngIf="clientPermissions.length > 0">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>View</th>
                      <th>Update</th>
                      <th>Download Config</th>
                      <th>View Token</th>
                      <th>Docker Config</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let perm of clientPermissions">
                      <td>{{ perm.user.email }}</td>
                      <td><span *ngIf="perm.can_view">✓</span></td>
                      <td><span *ngIf="perm.can_update">✓</span></td>
                      <td><span *ngIf="perm.can_download_config">✓</span></td>
                      <td><span *ngIf="perm.can_view_token">✓</span></td>
                      <td><span *ngIf="perm.can_download_docker_config">✓</span></td>
                      <td>
                        <button (click)="revokePermission(perm.id)" class="btn btn-sm btn-danger">Revoke</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
                <p *ngIf="clientPermissions.length === 0" class="text-muted">No permissions granted</p>

                <!-- Grant Permission Form -->
                <div class="grant-permission-form">
                  <h4>Grant New Permission</h4>
                  <div class="form-row">
                    <div class="form-group">
                      <label>User</label>
                      <select class="form-control" [(ngModel)]="newPermission.userId">
                        <option value="">Select user...</option>
                        <option *ngFor="let user of allUsers" [value]="user.id">{{ user.email }}</option>
                      </select>
                    </div>
                  </div>
                  <div class="form-row">
                    <label><input type="checkbox" [(ngModel)]="newPermission.canView"> Can View</label>
                    <label><input type="checkbox" [(ngModel)]="newPermission.canUpdate"> Can Update</label>
                    <label><input type="checkbox" [(ngModel)]="newPermission.canDownload"> Can Download Config</label>
                  </div>
                  <div class="form-row">
                    <label><input type="checkbox" [(ngModel)]="newPermission.canViewToken"> Can View Token</label>
                    <label><input type="checkbox" [(ngModel)]="newPermission.canDownloadDocker"> Can Download Docker Config</label>
                  </div>
                  <button (click)="grantPermission()" [disabled]="!newPermission.userId" class="btn btn-primary">Grant Permission</button>
                </div>
              </div>
            </div>
          </div>

          <!-- Groups Tab -->
          <div class="tab-content" *ngIf="activeTab === 'groups'">
            <div class="form-section">
              <h3>Group Memberships</h3>
              <p class="help-text">Groups are used in firewall rules to define access policies</p>
              
              <div class="selection-list">
                <div *ngFor="let group of allGroups" class="selection-item">
                  <label>
                    <input 
                      type="checkbox" 
                      [checked]="isGroupSelected(group.id)"
                      (change)="toggleGroup(group.id)">
                    {{ group.name }}
                  </label>
                </div>
              </div>
              
              <button (click)="saveGroups()" class="btn btn-primary">Save Groups</button>
            </div>
          </div>

          <!-- Firewall Tab -->
          <div class="tab-content" *ngIf="activeTab === 'firewall'">
            <div class="form-section">
              <h3>Firewall Rulesets</h3>
              <p class="help-text">Assign firewall rulesets to control inbound/outbound traffic</p>
              
              <div class="selection-list">
                <div *ngFor="let ruleset of allRulesets" class="selection-item">
                  <label>
                    <input 
                      type="checkbox" 
                      [checked]="isRulesetSelected(ruleset.id)"
                      (change)="toggleRuleset(ruleset.id)">
                    <strong>{{ ruleset.name }}</strong>
                    <span class="badge badge-secondary">{{ ruleset.rules.length }} rules</span>
                  </label>
                  <p class="help-text" *ngIf="ruleset.description">{{ ruleset.description }}</p>
                </div>
              </div>
              
              <button (click)="saveRulesets()" class="btn btn-primary">Save Rulesets</button>
            </div>
          </div>

          <!-- Certificates Tab -->
          <div class="tab-content" *ngIf="activeTab === 'certificates'">
            <div class="form-section">
              <div class="section-header">
                <h3>Client Certificates</h3>
                <button *ngIf="isAdmin" (click)="reissueCertificate()" class="btn btn-primary">
                  <span class="icon">🔄</span> Reissue Certificate
                </button>
              </div>
              
              <table *ngIf="certificates.length > 0">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Valid From</th>
                    <th>Valid Until</th>
                    <th>IP/CIDR</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let cert of certificates">
                    <td>{{ cert.id }}</td>
                    <td>{{ cert.not_before | date:'short' }}</td>
                    <td>{{ cert.not_after | date:'short' }}</td>
                    <td>{{ cert.issued_for_ip_cidr || '—' }}</td>
                    <td>
                      <span *ngIf="!cert.revoked && isValidCert(cert)" class="badge badge-success">Valid</span>
                      <span *ngIf="!cert.revoked && !isValidCert(cert)" class="badge badge-warning">Expired</span>
                      <span *ngIf="cert.revoked" class="badge badge-danger">Revoked</span>
                    </td>
                    <td>
                      <button 
                        *ngIf="!cert.revoked && isAdmin" 
                        (click)="revokeCertificate(cert.id)" 
                        class="btn btn-sm btn-danger">
                        Revoke
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              
              <p *ngIf="certificates.length === 0">No certificates found.</p>
            </div>
          </div>
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
      max-width: 1200px;
      margin: 0 auto;
      padding: 2rem;
    }
    
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
    }
    
    .header > div {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    
    .header-actions {
      display: flex;
      gap: 0.5rem;
    }
    
    h2 {
      margin: 0;
      color: #333;
    }
    
    .detail-container {
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      overflow: hidden;
    }
    
    .tabs {
      display: flex;
      border-bottom: 1px solid #e0e0e0;
      background: #f9f9f9;
    }
    
    .tab {
      padding: 1rem 1.5rem;
      border: none;
      background: transparent;
      cursor: pointer;
      font-size: 1rem;
      color: #666;
      transition: all 0.3s;
      border-bottom: 3px solid transparent;
    }
    
    .tab:hover {
      background: #f0f0f0;
      color: #333;
    }
    
    .tab.active {
      color: #4CAF50;
      border-bottom-color: #4CAF50;
      background: white;
    }
    
    .tab-content {
      padding: 2rem;
    }
    
    .form-section {
      margin-bottom: 2rem;
    }
    
    .form-section h3 {
      margin-top: 0;
      margin-bottom: 1rem;
      color: #333;
      border-bottom: 2px solid #4CAF50;
      padding-bottom: 0.5rem;
    }
    
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
    }
    
    .section-header h3 {
      margin: 0;
      border: none;
      padding: 0;
    }
    
    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-bottom: 1rem;
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
      border-color: #4CAF50;
    }
    
    .form-control:disabled {
      background: #f5f5f5;
      color: #666;
    }
    
    .help-text {
      margin: 0.25rem 0 0 0;
      font-size: 0.85rem;
      color: #666;
    }
    
    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-top: 1.5rem;
      padding: 1rem;
      background: #f9f9f9;
      border-radius: 4px;
    }
    
    .info-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    
    .info-item .label {
      font-size: 0.85rem;
      color: #666;
      font-weight: 600;
    }
    
    .info-item code {
      background: #f0f0f0;
      padding: 0.25rem 0.5rem;
      border-radius: 3px;
      font-size: 0.9rem;
      word-break: break-all;
    }
    
    .selection-list {
      max-height: 400px;
      overflow-y: auto;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 1rem;
      background: #fafafa;
      margin-bottom: 1rem;
    }
    
    .selection-item {
      padding: 0.75rem;
      margin-bottom: 0.5rem;
      background: white;
      border-radius: 4px;
      border: 1px solid #e0e0e0;
    }
    
    .selection-item label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      margin: 0;
    }
    
    .selection-item input[type="checkbox"] {
      width: auto;
      margin-right: 0.5rem;
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
      margin-left: 0.5rem;
    }
    
    .badge-success {
      background: #d4edda;
      color: #155724;
    }
    
    .badge-danger {
      background: #f8d7da;
      color: #721c24;
    }
    
    .badge-warning {
      background: #fff3cd;
      color: #856404;
    }
    
    .badge-secondary {
      background: #e2e3e5;
      color: #383d41;
    }
    
    .btn {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 1rem;
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
    
    .icon {
      font-size: 1.2rem;
      vertical-align: middle;
    }
    
    @media (max-width: 768px) {
      .container {
        padding: 1rem;
      }
      
      .header {
        flex-direction: column;
        align-items: flex-start;
        gap: 1rem;
      }
      
      .header-actions {
        width: 100%;
        flex-direction: column;
      }
      
      .header-actions button {
        width: 100%;
      }
      
      .tabs {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        flex-wrap: nowrap;
      }
      
      .tabs button {
        white-space: nowrap;
      }
      
      .info-grid {
        grid-template-columns: 1fr;
      }
      
      .info-section {
        overflow-x: auto;
      }
      
      .form-actions {
        flex-direction: column;
      }
      
      .form-actions button {
        width: 100%;
      }
      
      .checkbox-grid {
        grid-template-columns: 1fr;
      }
      
      .modal {
        padding: 0.5rem;
      }
      
      .modal-content {
        padding: 1rem;
        width: 95%;
      }
      
      table {
        font-size: 0.85rem;
      }
      
      th, td {
        padding: 0.5rem 0.25rem;
      }
    }
  `],
    standalone: false
})
export class ClientDetailComponent implements OnInit {
  clientId: number = 0;
  client: Client | null = null;
  activeTab: 'details' | 'groups' | 'firewall' | 'certificates' = 'details';
  
  allGroups: Group[] = [];
  selectedGroupIds: Set<number> = new Set();
  
  allRulesets: FirewallRuleset[] = [];
  selectedRulesetIds: Set<number> = new Set();
  
  certificates: ClientCertificate[] = [];
  
  // IP Management
  allIPPools: any[] = [];
  allIPGroups: any[] = [];
  availableIPs: any[] = [];
  selectedPoolId: number | null = null;
  selectedIPGroupId: number | null = null;
  newIPAddress: string = '';
  useManualIP: boolean = false;
  
  isAdmin = this.authService.isAdmin();

  // Ownership & Permissions
  allUsers: any[] = [];
  clientPermissions: any[] = [];
  selectedOwnerId: number | null = null;
  newPermission = {
    userId: null as number | null,
    canView: false,
    canUpdate: false,
    canDownload: false,
    canViewToken: false,
    canDownloadDocker: false
  };

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
    private authService: AuthService,
    private notificationService: NotificationService
  ) {}

  ngOnInit(): void {
    this.route.params.subscribe((params: any) => {
      this.clientId = +params['id'];
      this.loadClient();
      this.loadGroups();
      this.loadRulesets();
      this.loadIPPools();
      if (this.isAdmin) {
        this.loadUsers();
        this.loadPermissions();
      }
    });
  }

  loadClient(): void {
    this.apiService.getClient(this.clientId).subscribe({
      next: (client: Client) => {
        this.client = client;
        this.selectedGroupIds = new Set(client.groups.map(g => g.id));
        this.selectedRulesetIds = new Set(client.firewall_rulesets?.map(r => r.id) || []);
        this.newIPAddress = client.ip_address || '';
        this.selectedPoolId = client.pool_id || null;
        this.selectedIPGroupId = client.ip_group_id || null;
        
        // Load IP groups for the current pool if one is set
        if (this.selectedPoolId) {
          this.loadIPGroups(this.selectedPoolId);
        }
      },
      error: (err: any) => {
        this.notificationService.notify('Failed to load client: ' + (err.error?.detail || 'Unknown error'));
        this.router.navigate(['/clients']);
      }
    });
  }

  loadGroups(): void {
    this.apiService.getGroups().subscribe({
      next: (groups: Group[]) => this.allGroups = groups,
      error: (err: any) => this.notificationService.notify('Failed to load groups')
    });
  }

  loadRulesets(): void {
    this.apiService.getFirewallRulesets().subscribe({
      next: (rulesets: FirewallRuleset[]) => this.allRulesets = rulesets,
      error: (err: any) => this.notificationService.notify('Failed to load firewall rulesets')
    });
  }

  loadCertificates(): void {
    if (!this.isAdmin) return;
    
    this.apiService.getClientCertificates(this.clientId).subscribe({
      next: (certs: ClientCertificate[]) => this.certificates = certs,
      error: (err: any) => this.notificationService.notify('Failed to load certificates')
    });
  }

  saveDetails(): void {
    if (!this.client) return;
    
    this.apiService.updateClient(this.clientId, {
      name: this.client.name,
      is_lighthouse: this.client.is_lighthouse,
      public_ip: this.client.public_ip || undefined,
      is_blocked: this.client.is_blocked
    }).subscribe({
      next: (updated: Client) => {
        this.client = updated;
        this.notificationService.notify('Client details updated', 'success');
      },
      error: (err: any) => this.notificationService.notify('Failed to update client: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  isGroupSelected(groupId: number): boolean {
    return this.selectedGroupIds.has(groupId);
  }

  toggleGroup(groupId: number): void {
    if (this.selectedGroupIds.has(groupId)) {
      this.selectedGroupIds.delete(groupId);
    } else {
      this.selectedGroupIds.add(groupId);
    }
  }

  saveGroups(): void {
    this.apiService.updateClient(this.clientId, {
      group_ids: Array.from(this.selectedGroupIds)
    }).subscribe({
      next: (updated: Client) => {
        this.client = updated;
        this.notificationService.notify('Groups updated', 'success');
      },
      error: (err: any) => this.notificationService.notify('Failed to update groups: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  isRulesetSelected(rulesetId: number): boolean {
    return this.selectedRulesetIds.has(rulesetId);
  }

  toggleRuleset(rulesetId: number): void {
    if (this.selectedRulesetIds.has(rulesetId)) {
      this.selectedRulesetIds.delete(rulesetId);
    } else {
      this.selectedRulesetIds.add(rulesetId);
    }
  }

  saveRulesets(): void {
    this.apiService.updateClient(this.clientId, {
      firewall_ruleset_ids: Array.from(this.selectedRulesetIds)
    }).subscribe({
      next: (updated: Client) => {
        this.client = updated;
        this.notificationService.notify('Firewall rulesets updated', 'success');
      },
      error: (err: any) => this.notificationService.notify('Failed to update rulesets: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  isValidCert(cert: ClientCertificate): boolean {
    const now = new Date();
    const notAfter = new Date(cert.not_after);
    return notAfter > now;
  }

  reissueCertificate(): void {
    if (!confirm('Are you sure you want to reissue the certificate? The client will need to download the new config.')) {
      return;
    }
    
    this.apiService.reissueClientCertificate(this.clientId).subscribe({
      next: (response: { status: string; message: string }) => {
        this.notificationService.notify(response.message, 'success');
        this.loadCertificates();
      },
      error: (err: any) => this.notificationService.notify('Failed to reissue certificate: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  revokeCertificate(certId: number): void {
    if (!confirm('Are you sure you want to revoke this certificate? This cannot be undone.')) {
      return;
    }
    
    this.apiService.revokeClientCertificate(this.clientId, certId).subscribe({
      next: (response: { status: string; certificate_id: number; revoked_at: string }) => {
        this.notificationService.notify('Certificate revoked', 'success');
        this.loadCertificates();
      },
      error: (err: any) => this.notificationService.notify('Failed to revoke certificate: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  downloadConfig(): void {
    this.apiService.downloadClientConfig(this.clientId).subscribe({
      next: (config: ClientConfigDownload) => {
        // Download only the compiled config.yml (cert and CA are embedded inline)
        const configBlob = new Blob([config.config_yaml], { type: 'text/yaml' });
        this.downloadFile(configBlob, `${this.client?.name || 'client'}-config.yml`);
        
        this.notificationService.notify('Config file downloaded', 'success');
      },
      error: (err: any) => this.notificationService.notify('Failed to download config: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  downloadDockerCompose(): void {
    this.apiService.downloadClientDockerCompose(this.clientId).subscribe({
      next: (blob: Blob) => {
        this.downloadFile(blob, `${this.client?.name || 'client'}-docker-compose.yml`);
        this.notificationService.notify('Docker Compose file downloaded', 'success');
      },
      error: (err: any) => this.notificationService.notify('Failed to download docker-compose: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  private downloadFile(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }

  // IP Management methods
  loadIPPools(): void {
    this.apiService.getIPPools().subscribe({
      next: (pools: any[]) => {
        this.allIPPools = pools;
      },
      error: (err: any) => this.notificationService.notify('Failed to load IP pools')
    });
  }

  loadIPGroups(poolId?: number): void {
    this.apiService.getIPGroups(poolId).subscribe({
      next: (groups: any[]) => {
        this.allIPGroups = groups;
      },
      error: (err: any) => this.notificationService.notify('Failed to load IP groups')
    });
  }

  onPoolChange(): void {
    if (this.selectedPoolId) {
      this.loadIPGroups(this.selectedPoolId);
      this.loadAvailableIPs();
    } else {
      this.allIPGroups = [];
      this.availableIPs = [];
      this.selectedIPGroupId = null;
    }
  }

  onIPGroupChange(): void {
    this.loadAvailableIPs();
  }

  loadAvailableIPs(): void {
    if (!this.selectedPoolId) return;
    this.apiService.getAvailableIPs(this.selectedPoolId, this.selectedIPGroupId || undefined)
      .subscribe({ 
        next: (ips: any[]) => this.availableIPs = ips,
        error: (err: any) => this.notificationService.notify('Failed to load available IPs')
      });
  }

  saveIPAddress(): void {
    if (!this.client || !this.newIPAddress) return;
    
    const payload: any = {
      ip_address: this.newIPAddress
    };
    
    if (this.selectedPoolId) {
      payload.pool_id = this.selectedPoolId;
    }
    
    if (this.selectedIPGroupId) {
      payload.ip_group_id = this.selectedIPGroupId;
    }
    
    this.apiService.updateClient(this.clientId, payload).subscribe({
      next: (updated: Client) => {
        this.client = updated;
        this.newIPAddress = updated.ip_address || '';
        this.notificationService.notify('IP address updated successfully', 'success');
      },
      error: (err: any) => this.notificationService.notify('Failed to update IP address: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  goBack(): void {
    this.router.navigate(['/clients']);
  }

  // Ownership & Permissions methods
  loadUsers(): void {
    this.apiService.getUsers().subscribe({
      next: (users: any[]) => {
        this.allUsers = users.filter(u => u.id !== this.client?.owner?.id);
      },
      error: (err: any) => this.notificationService.notify('Failed to load users')
    });
  }

  loadPermissions(): void {
    this.apiService.getClientPermissions(this.clientId).subscribe({
      next: (permissions: any[]) => {
        this.clientPermissions = permissions;
      },
      error: (err: any) => this.notificationService.notify('Failed to load permissions')
    });
  }

  reassignOwner(): void {
    if (!this.selectedOwnerId || !this.client) return;
    
    this.apiService.updateClientOwner(this.clientId, this.selectedOwnerId).subscribe({
      next: (updatedClient: Client) => {
        this.client = updatedClient;
        this.notificationService.notify('Owner reassigned successfully', 'success');
        this.loadUsers(); // Refresh user list
      },
      error: (err: any) => this.notificationService.notify('Failed to reassign owner: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  grantPermission(): void {
    if (!this.newPermission.userId) return;

    this.apiService.grantClientPermission(
      this.clientId,
      this.newPermission.userId,
      {
        can_view: this.newPermission.canView,
        can_update: this.newPermission.canUpdate,
        can_download_config: this.newPermission.canDownload,
        can_view_token: this.newPermission.canViewToken,
        can_download_docker_config: this.newPermission.canDownloadDocker
      }
    ).subscribe({
      next: () => {
        this.notificationService.notify('Permission granted successfully', 'success');
        this.loadPermissions();
        // Reset form
        this.newPermission = {
          userId: null,
          canView: false,
          canUpdate: false,
          canDownload: false,
          canViewToken: false,
          canDownloadDocker: false
        };
      },
      error: (err: any) => this.notificationService.notify('Failed to grant permission: ' + (err.error?.detail || 'Unknown error'))
    });
  }

  revokePermission(permissionId: number): void {
    if (!confirm('Are you sure you want to revoke this permission?')) return;

    this.apiService.revokeClientPermission(this.clientId, permissionId).subscribe({
      next: () => {
        this.notificationService.notify('Permission revoked successfully', 'success');
        this.loadPermissions();
      },
      error: (err: any) => this.notificationService.notify('Failed to revoke permission: ' + (err.error?.detail || 'Unknown error'))
    });
  }
}
