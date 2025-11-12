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
      <button class="mobile-menu-toggle" (click)="toggleMobileMenu()" [class.open]="mobileMenuOpen">
        <span></span>
        <span></span>
        <span></span>
      </button>
      <div class="nav-links" [class.mobile-open]="mobileMenuOpen">
        <a routerLink="/dashboard" routerLinkActive="active" (click)="closeMobileMenu()">Dashboard</a>
        <a routerLink="/clients" routerLinkActive="active" (click)="closeMobileMenu()">Clients</a>
        <a routerLink="/groups" routerLinkActive="active" (click)="closeMobileMenu()">Groups</a>
        <a routerLink="/firewall-rules" routerLinkActive="active" (click)="closeMobileMenu()">Firewall Rules</a>
        <a routerLink="/ip-pools" routerLinkActive="active" (click)="closeMobileMenu()">IP Pools</a>
        <a routerLink="/ip-groups" routerLinkActive="active" (click)="closeMobileMenu()">IP Groups</a>
        <a routerLink="/ca" routerLinkActive="active" (click)="closeMobileMenu()">CA</a>
        <a routerLink="/users" routerLinkActive="active" *ngIf="isAdmin" (click)="closeMobileMenu()">Users</a>
        <a routerLink="/user-groups" routerLinkActive="active" (click)="closeMobileMenu()">User Groups</a>
        <a routerLink="/settings" routerLinkActive="active" *ngIf="isAdmin" (click)="closeMobileMenu()">Settings</a>
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
      position: relative;
    }
    
    .navbar h1 {
      margin: 0;
      color: #333;
      font-size: 1.5rem;
    }
    
    .mobile-menu-toggle {
      display: none;
      flex-direction: column;
      justify-content: space-around;
      width: 30px;
      height: 25px;
      background: transparent;
      border: none;
      cursor: pointer;
      padding: 0;
      z-index: 10;
    }
    
    .mobile-menu-toggle span {
      width: 100%;
      height: 3px;
      background: #333;
      transition: all 0.3s;
    }
    
    .mobile-menu-toggle.open span:nth-child(1) {
      transform: rotate(45deg) translate(8px, 8px);
    }
    
    .mobile-menu-toggle.open span:nth-child(2) {
      opacity: 0;
    }
    
    .mobile-menu-toggle.open span:nth-child(3) {
      transform: rotate(-45deg) translate(7px, -7px);
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
    
    @media (max-width: 768px) {
      .navbar {
        padding: 1rem;
      }
      
      .navbar h1 {
        font-size: 1.2rem;
      }
      
      .mobile-menu-toggle {
        display: flex;
      }
      
      .nav-links {
        position: fixed;
        top: 60px;
        right: -100%;
        width: 70%;
        max-width: 300px;
        height: calc(100vh - 60px);
        background: white;
        flex-direction: column;
        align-items: flex-start;
        padding: 2rem 1rem;
        box-shadow: -2px 0 10px rgba(0,0,0,0.1);
        transition: right 0.3s ease;
        overflow-y: auto;
        gap: 0;
        z-index: 1000;
      }
      
      .nav-links.mobile-open {
        right: 0;
      }
      
      .nav-links a {
        width: 100%;
        padding: 1rem;
        border-radius: 0;
        border-bottom: 1px solid #eee;
      }
      
      .user-info {
        width: 100%;
        padding: 1rem;
        border-left: none;
        border-bottom: 1px solid #eee;
      }
      
      .btn {
        width: 100%;
        margin-top: 1rem;
      }
    }
  `]
})
export class NavbarComponent {
  currentUser = this.authService.getCurrentUser();
  isAdmin = this.authService.isAdmin();
  mobileMenuOpen = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  toggleMobileMenu(): void {
    this.mobileMenuOpen = !this.mobileMenuOpen;
  }

  closeMobileMenu(): void {
    this.mobileMenuOpen = false;
  }

  logout(): void {
    this.authService.logout().subscribe();
    this.closeMobileMenu();
  }
}
