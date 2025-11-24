import { Component, OnInit } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { User, Client } from '../models';

@Component({
    selector: 'app-dashboard',
    template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <h2>Dashboard</h2>
        
        <!-- Loading State -->
        <div *ngIf="isLoading" class="loading-container">
          <div class="spinner"></div>
          <p>Loading dashboard...</p>
        </div>

        <!-- Error State -->
        <div *ngIf="!isLoading && error" class="error-container">
          <p class="error-message">{{ error }}</p>
          <button (click)="loadDashboardData()" class="btn btn-secondary">Retry</button>
        </div>

        <!-- Dashboard Content -->
        <div *ngIf="!isLoading && !error">
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Total Clients</h3>
            <p class="stat-number">{{ totalClients }}</p>
          </div>
          
          <div class="stat-card">
            <h3>Lighthouses</h3>
            <p class="stat-number">{{ lighthouses }}</p>
          </div>
          
          <div class="stat-card">
            <h3>Blocked Clients</h3>
            <p class="stat-number">{{ blockedClients }}</p>
          </div>
          
          <div class="stat-card version-health">
            <h3>Version Health</h3>
            <div class="version-stats">
              <div class="version-stat">
                <span class="version-icon">🟢</span>
                <span class="version-count">{{ currentVersionClients }}</span>
                <span class="version-label">Current</span>
              </div>
              <div class="version-stat">
                <span class="version-icon">🟡</span>
                <span class="version-count">{{ outdatedClients }}</span>
                <span class="version-label">Outdated</span>
              </div>
              <div class="version-stat">
                <span class="version-icon">🔴</span>
                <span class="version-count">{{ vulnerableClients }}</span>
                <span class="version-label">Vulnerable</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="recent-clients">
          <h3>Recent Clients</h3>
          <div class="table-responsive">
            <table *ngIf="recentClients.length > 0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th class="hide-mobile">IP Address</th>
                  <th>Status</th>
                  <th class="hide-mobile">Last Config</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let client of recentClients">
                  <td>{{ client.name }}</td>
                  <td class="hide-mobile">{{ client.ip_address || 'N/A' }}</td>
                  <td>
                    <span *ngIf="client.is_blocked" class="badge badge-danger">Blocked</span>
                    <span *ngIf="!client.is_blocked" class="badge badge-success">OK</span>
                  </td>
                  <td class="hide-mobile">{{ client.last_config_download_at ? (client.last_config_download_at | localDate:'short') : 'Never' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p *ngIf="recentClients.length === 0">No clients found.</p>
        </div>
        </div>
        <!-- End Dashboard Content -->
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
    
    h2 {
      margin-bottom: 2rem;
      color: #333;
    }
    
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
      margin-bottom: 3rem;
    }
    
    .stat-card {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .stat-card h3 {
      margin: 0 0 1rem 0;
      color: #666;
      font-size: 0.9rem;
      text-transform: uppercase;
    }
    
    .stat-number {
      font-size: 2.5rem;
      font-weight: bold;
      color: #4CAF50;
      margin: 0;
    }
    
    .recent-clients {
      background: white;
      padding: 1.5rem;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .recent-clients h3 {
      margin-top: 0;
      color: #333;
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
    }
    
    .badge-success {
      background: #d4edda;
      color: #155724;
    }
    
    .badge-danger {
      background: #f8d7da;
      color: #721c24;
    }
    
    .version-health {
      grid-column: span 1;
    }
    
    .version-stats {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .version-stat {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.9rem;
    }
    
    .version-icon {
      font-size: 1.2rem;
    }
    
    .version-count {
      font-weight: bold;
      color: #333;
      min-width: 2rem;
    }
    
    .version-label {
      color: #666;
    }

    /* Loading and Error States */
    .loading-container {
      text-align: center;
      padding: 3rem;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .spinner {
      border: 4px solid #f3f3f3;
      border-top: 4px solid #4CAF50;
      border-radius: 50%;
      width: 40px;
      height: 40px;
      animation: spin 1s linear infinite;
      margin: 0 auto 1rem;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-container p {
      color: #666;
      margin: 0;
    }

    .error-container {
      background: #f8d7da;
      border: 1px solid #f5c6cb;
      border-radius: 8px;
      padding: 2rem;
      text-align: center;
    }

    .error-message {
      color: #721c24;
      margin: 0 0 1rem 0;
      font-weight: 500;
    }

    .btn {
      padding: 0.5rem 1.5rem;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 500;
    }

    .btn-secondary {
      background: #6c757d;
      color: white;
    }

    .btn-secondary:hover {
      background: #5a6268;
    }
  `],
    standalone: false
})
export class DashboardComponent implements OnInit {
  currentUser: User | null = null;
  totalClients = 0;
  lighthouses = 0;
  blockedClients = 0;
  recentClients: Client[] = [];
  currentVersionClients = 0;
  outdatedClients = 0;
  vulnerableClients = 0;
  isLoading = false;
  error = '';

  constructor(
    private authService: AuthService,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    this.loadDashboardData();
  }

  loadDashboardData(): void {
    this.isLoading = true;
    this.error = '';
    this.apiService.getClients().subscribe({
      next: (clients: Client[]) => {
        this.totalClients = clients.length;
        this.lighthouses = clients.filter(c => c.is_lighthouse).length;
        this.blockedClients = clients.filter(c => c.is_blocked).length;
        this.recentClients = clients.slice(0, 10);
        
        // Calculate version health statistics
        this.calculateVersionHealth(clients);
        this.isLoading = false;
      },
      error: (error: unknown) => {
        console.error('Failed to load dashboard data:', error);
        this.error = 'Failed to load dashboard data. Please try again.';
        this.isLoading = false;
      }
    });
  }

  calculateVersionHealth(clients: Client[]): void {
    this.currentVersionClients = 0;
    this.outdatedClients = 0;
    this.vulnerableClients = 0;
    
    for (const client of clients) {
      if (!client.version_status) {
        // Unknown status - don't count
        continue;
      }
      
      const clientStatus = client.version_status.client_version_status;
      const nebulaStatus = client.version_status.nebula_version_status;
      
      // Prioritize: vulnerable > outdated > current
      if (clientStatus === 'vulnerable' || nebulaStatus === 'vulnerable') {
        this.vulnerableClients++;
      } else if (clientStatus === 'outdated' || nebulaStatus === 'outdated') {
        this.outdatedClients++;
      } else if (clientStatus === 'current' && nebulaStatus === 'current') {
        this.currentVersionClients++;
      }
    }
  }

}
