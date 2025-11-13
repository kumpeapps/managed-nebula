import { Component, OnInit } from '@angular/core';
import { AuthService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { NotificationService } from '../services/notification.service';
import { Settings } from '../models';

@Component({
    selector: 'app-settings',
    template: `
    <div class="dashboard">
      <app-navbar></app-navbar>
      
      <div class="container">
        <h2>Settings</h2>
        
        <div class="settings-container">
          <div class="setting-section">
            <h3>Nebula Configuration</h3>
            <p class="help-text">Global settings that affect all Nebula client configurations</p>
            
            <div class="setting-item">
              <label class="toggle-label">
                <input 
                  type="checkbox" 
                  [(ngModel)]="settings.punchy_enabled"
                  (change)="saveSettings()"
                  class="toggle-checkbox">
                <span class="toggle-text">
                  <strong>Enable Punchy</strong>
                  <span class="description">
                    Nebula "punchy" helps peers behind NAT maintain connectivity by sending periodic packets. 
                    Enables punch_back and respond when active.
                  </span>
                </span>
              </label>
            </div>
            
            <div class="info-box" *ngIf="settings.punchy_enabled">
              <p><strong>ℹ️ Punchy Enabled</strong></p>
              <p>New client configs will include punchy settings with punch_back and respond set to true.</p>
            </div>
          </div>
          
          <div class="setting-section">
            <h3>Client Docker Configuration</h3>
            <p class="help-text">Default Docker image and server URL used in generated docker-compose files for clients</p>
            
            <div class="setting-item">
              <label class="input-label">
                <strong>Client Docker Image</strong>
                <span class="description">
                  Full Docker image path (e.g., ghcr.io/kumpeapps/managed-nebula-client:latest)
                </span>
                <input 
                  type="text" 
                  [(ngModel)]="settings.client_docker_image"
                  (blur)="saveSettings()"
                  class="text-input"
                  placeholder="ghcr.io/kumpeapps/managed-nebula-client:latest">
              </label>
            </div>
            
            <div class="setting-item">
              <label class="input-label">
                <strong>Server URL</strong>
                <span class="description">
                  URL that clients will use to connect to this server (e.g., https://your-server.com or http://localhost:8080)
                </span>
                <input 
                  type="text" 
                  [(ngModel)]="settings.server_url"
                  (blur)="saveSettings()"
                  class="text-input"
                  placeholder="http://localhost:8080">
              </label>
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
    
    h2 {
      margin-bottom: 2rem;
      color: #333;
    }
    
    .settings-container {
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      padding: 2rem;
    }
    
    .setting-section {
      margin-bottom: 2rem;
    }
    
    .setting-section:last-child {
      margin-bottom: 0;
    }
    
    .setting-section h3 {
      margin: 0 0 0.5rem 0;
      color: #333;
      border-bottom: 2px solid #4CAF50;
      padding-bottom: 0.5rem;
    }
    
    .help-text {
      margin: 0 0 1.5rem 0;
      font-size: 0.9rem;
      color: #666;
    }
    
    .setting-item {
      padding: 1.5rem;
      background: #f9f9f9;
      border-radius: 4px;
      border: 1px solid #e0e0e0;
      margin-bottom: 1rem;
    }
    
    .toggle-label {
      display: flex;
      align-items: flex-start;
      gap: 1rem;
      cursor: pointer;
    }
    
    .toggle-checkbox {
      margin-top: 0.25rem;
      width: 20px;
      height: 20px;
      cursor: pointer;
    }
    
    .toggle-text {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .toggle-text strong {
      color: #333;
      font-size: 1.1rem;
    }
    
    .description {
      font-size: 0.9rem;
      color: #666;
      line-height: 1.5;
    }
    
    .info-box {
      background: #d1ecf1;
      border: 1px solid #bee5eb;
      border-radius: 4px;
      padding: 1rem;
      margin-top: 1rem;
    }
    
    .info-box p {
      margin: 0 0 0.5rem 0;
      color: #0c5460;
    }
    
    .info-box p:last-child {
      margin-bottom: 0;
    }
    
    .input-label {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .input-label strong {
      color: #333;
      font-size: 1.1rem;
    }
    
    .text-input {
      width: 100%;
      padding: 0.75rem;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 1rem;
      font-family: monospace;
    }
    
    .text-input:focus {
      outline: none;
      border-color: #4CAF50;
    }
    
    @media (max-width: 768px) {
      .container {
        padding: 1rem;
      }
      
      .settings-grid {
        grid-template-columns: 1fr;
      }
      
      .form-actions {
        flex-direction: column;
      }
      
      .form-actions button {
        width: 100%;
      }
    }
  `],
    standalone: false
})
export class SettingsComponent implements OnInit {
  settings: Settings = {
    punchy_enabled: false,
    client_docker_image: 'ghcr.io/kumpeapps/managed-nebula-client:latest',
    server_url: 'http://localhost:8080'
  };
  isAdmin = this.authService.isAdmin();

  constructor(
    private authService: AuthService,
    private apiService: ApiService,
    private notificationService: NotificationService
  ) {}

  ngOnInit(): void {
    if (!this.isAdmin) {
      this.notificationService.notify('Admin access required', 'error');
      return;
    }
    this.loadSettings();
  }

  loadSettings(): void {
    this.apiService.getSettings().subscribe({
      next: (settings: Settings) => {
        this.settings = settings;
      },
      error: (err: any) => {
        console.error('Failed to load settings:', err);
        this.notificationService.notify('Failed to load settings');
      }
    });
  }

  saveSettings(): void {
    this.apiService.updateSettings({
      punchy_enabled: this.settings.punchy_enabled,
      client_docker_image: this.settings.client_docker_image,
      server_url: this.settings.server_url
    }).subscribe({
      next: (updated: Settings) => {
        this.settings = updated;
        this.notificationService.notify('Settings saved successfully', 'success');
      },
      error: (err: any) => {
        console.error('Failed to save settings:', err);
        this.notificationService.notify('Failed to save settings: ' + (err.error?.detail || 'Unknown error'));
        // Reload settings to revert UI
        this.loadSettings();
      }
    });
  }
}
