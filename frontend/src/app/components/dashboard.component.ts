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
        </div>
        
        <div class="recent-clients">
          <h3>Recent Clients</h3>
          <table *ngIf="recentClients.length > 0">
            <thead>
              <tr>
                <th>Name</th>
                <th>IP Address</th>
                <th>Status</th>
                <th>Last Config</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let client of recentClients">
                <td>{{ client.name }}</td>
                <td>{{ client.ip_address || 'N/A' }}</td>
                <td>
                  <span *ngIf="client.is_blocked" class="badge badge-danger">Blocked</span>
                  <span *ngIf="!client.is_blocked" class="badge badge-success">OK</span>
                </td>
                <td>{{ client.last_config_download_at ? (client.last_config_download_at | date:'short') : 'Never' }}</td>
              </tr>
            </tbody>
          </table>
          <p *ngIf="recentClients.length === 0">No clients found.</p>
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
  `]
})
export class DashboardComponent implements OnInit {
  currentUser: User | null = null;
  totalClients = 0;
  lighthouses = 0;
  blockedClients = 0;
  recentClients: Client[] = [];

  constructor(
    private authService: AuthService,
    private apiService: ApiService
  ) {}

  ngOnInit(): void {
    this.currentUser = this.authService.getCurrentUser();
    this.loadDashboardData();
  }

  loadDashboardData(): void {
    this.apiService.getClients().subscribe({
      next: (clients: Client[]) => {
        this.totalClients = clients.length;
        this.lighthouses = clients.filter(c => c.is_lighthouse).length;
        this.blockedClients = clients.filter(c => c.is_blocked).length;
        this.recentClients = clients.slice(0, 10);
      },
      error: (error: unknown) => {
        console.error('Failed to load dashboard data:', error);
      }
    });
  }

}
