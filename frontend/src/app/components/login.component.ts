import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

@Component({
  selector: 'app-login',
  template: `
    <div class="login-container">
      <div class="login-card">
        <h1>Managed Nebula</h1>
        <h2>Login</h2>
        
        <form (ngSubmit)="onSubmit()" #loginForm="ngForm">
          <div class="form-group">
            <label for="email">Email</label>
            <input 
              type="email" 
              id="email" 
              name="email"
              [(ngModel)]="email" 
              required
              class="form-control"
            >
          </div>
          
          <div class="form-group">
            <label for="password">Password</label>
            <input 
              type="password" 
              id="password" 
              name="password"
              [(ngModel)]="password" 
              required
              class="form-control"
            >
          </div>
          
          <div *ngIf="errorMessage" class="alert alert-danger">
            {{ errorMessage }}
          </div>
          
          <button 
            type="submit" 
            [disabled]="!loginForm.valid || isLoading"
            class="btn btn-primary"
          >
            {{ isLoading ? 'Logging in...' : 'Login' }}
          </button>
        </form>
      </div>
    </div>
  `,
  styles: [`
    .login-container {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: #f5f5f5;
    }
    
    .login-card {
      background: white;
      padding: 2rem;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      width: 100%;
      max-width: 400px;
      margin: 1rem;
    }
    
    h1 {
      text-align: center;
      color: #333;
      margin-bottom: 0.5rem;
    }
    
    h2 {
      text-align: center;
      color: #666;
      margin-bottom: 2rem;
      font-size: 1.2rem;
    }
    
    .form-group {
      margin-bottom: 1.5rem;
    }
    
    label {
      display: block;
      margin-bottom: 0.5rem;
      color: #333;
      font-weight: 500;
    }
    
    .form-control {
      width: 100%;
      padding: 0.75rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 1rem;
    }
    
    .form-control:focus {
      outline: none;
      border-color: #4CAF50;
    }
    
    .alert {
      padding: 0.75rem;
      border-radius: 4px;
      margin-bottom: 1rem;
    }
    
    .alert-danger {
      background: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
    }
    
    .btn {
      width: 100%;
      padding: 0.75rem;
      border: none;
      border-radius: 4px;
      font-size: 1rem;
      cursor: pointer;
      transition: background 0.3s;
    }
    
    .btn-primary {
      background: #4CAF50;
      color: white;
    }
    
    .btn-primary:hover:not(:disabled) {
      background: #45a049;
    }
    
    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
    
    @media (max-width: 768px) {
      .login-card {
        padding: 1.5rem;
      }
      
      h1 {
        font-size: 1.5rem;
      }
      
      h2 {
        font-size: 1rem;
      }
    }
  `]
})
export class LoginComponent {
  email = '';
  password = '';
  errorMessage = '';
  isLoading = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  onSubmit(): void {
    this.isLoading = true;
    this.errorMessage = '';

  this.authService.login(this.email, this.password).subscribe({
      next: () => {
        this.router.navigate(['/dashboard']);
      },
      error: (error) => {
        this.isLoading = false;
        this.errorMessage = error.error?.detail || 'Login failed. Please try again.';
      },
      complete: () => {
        this.isLoading = false;
      }
    });
  }
}
