import { Component, Input } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * Reusable navigation bar component for consistent navigation across all pages.
 */
@Component({
  selector: 'app-navbar',
  template: `
    <nav class="navbar">
      <h1>Managed Nebula</h1>
      <div class="nav-links">
        <a routerLink="/dashboard" routerLinkActive="active">Dashboard</a>
        <a routerLink="/clients" routerLinkActive="active">Clients</a>
        <a routerLink="/groups" routerLinkActive="active">Groups</a>
        <a routerLink="/firewall-rules" routerLinkActive="active">Firewall Rules</a>
        <a routerLink="/ip-pools" routerLinkActive="active">IP Pools</a>
        <a routerLink="/ip-groups" routerLinkActive="active">IP Groups</a>
        <a routerLink="/ca" routerLinkActive="active">CA</a>
        <a routerLink="/users" routerLinkActive="active" *ngIf="isAdmin">Users</a>
        <a routerLink="/user-groups" routerLinkActive="active">User Groups</a>
        <a routerLink="/settings" routerLinkActive="active" *ngIf="isAdmin">Settings</a>
        <span class="user-info">{{ currentUser?.email }}</span>
        <button (click)="logout()" class="btn btn-secondary">Logout</button>
      </div>
    </nav>
  `,
  styles: [`
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
      font-size: 1.5rem;
    }
    
    .nav-links {
      display: flex;
      gap: 0.5rem;
      align-items: center;
      flex-wrap: wrap;
    }
    
    .nav-links a {
      color: #666;
      text-decoration: none;
      padding: 0.5rem 0.75rem;
      border-radius: 4px;
      transition: background 0.3s;
      font-size: 0.9rem;
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
      font-size: 0.9rem;
    }
    
    .btn {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.3s;
      font-size: 0.9rem;
    }
    
    .btn-secondary {
      background: #6c757d;
      color: white;
    }
    
    .btn-secondary:hover {
      background: #5a6268;
    }
  `]
})
export class NavbarComponent {
  currentUser = this.authService.getCurrentUser();
  isAdmin = this.authService.isAdmin();

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  logout(): void {
    this.authService.logout().subscribe();
  }
}
