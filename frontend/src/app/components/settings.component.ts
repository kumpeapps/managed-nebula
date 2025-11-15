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
            <h3>Mobile Enrollment</h3>
            <p class="help-text">Enable or disable mobile device enrollment via one-time codes and QR codes</p>
            
            <div class="setting-item">
              <label class="toggle-label">
                <input 
                  type="checkbox" 
                  [(ngModel)]="settings.mobile_enrollment_enabled"
                  (change)="saveSettings()"
                  class="toggle-checkbox">
                <span class="toggle-text">
                  <strong>Enable Mobile Enrollment</strong>
                  <span class="description">
                    Allow administrators to generate enrollment codes and QR codes for mobile devices.
                    When disabled, the Mobile Enrollment menu will be hidden.
                  </span>
                </span>
              </label>
            </div>
            
            <div class="info-box" *ngIf="settings.mobile_enrollment_enabled">
              <p><strong>ℹ️ Mobile Enrollment Enabled</strong></p>
              <p>Users can now access the Mobile Enrollment page to generate one-time enrollment codes.</p>
              <p class="text-muted small mt-2">Note: This feature is designed for a future Managed Nebula mobile app. Standard Mobile Nebula app from Defined Networking will not work with these enrollment codes.</p>
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
          
          <div class="setting-section">
            <h3>Docker Compose Template</h3>
            <p class="help-text">Customize the docker-compose.yml template generated for clients using dynamic placeholders</p>
            
            <div class="template-editor-container">
              <div class="editor-section">
                <div class="editor-header">
                  <strong>Template Editor</strong>
                  <button class="reset-btn" (click)="resetTemplate()">Reset to Default</button>
                </div>
                <textarea 
                  [(ngModel)]="settings.docker_compose_template"
                  (input)="onTemplateChange()"
                  class="template-textarea"
                  placeholder="Enter docker-compose template with placeholders..."></textarea>
              </div>
              
              <div class="placeholders-section">
                <strong>Available Placeholders</strong>
                <table class="placeholders-table">
                  <thead>
                    <tr>
                      <th>Placeholder</th>
                      <th>Description</th>
                      <th>Example</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr *ngFor="let ph of placeholders">
                      <td><code>{{ph.name}}</code></td>
                      <td>{{ph.description}}</td>
                      <td><code>{{ph.example}}</code></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <div class="preview-section">
                <strong>Preview (with sample data)</strong>
                <pre class="preview-content">{{previewTemplate}}</pre>
              </div>
            </div>
            
            <div class="form-actions">
              <button class="save-btn" (click)="saveSettings()">Save Changes</button>
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
    
    .template-editor-container {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      margin-top: 1rem;
    }
    
    .editor-section {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .editor-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem;
      background: #f0f0f0;
      border-radius: 4px 4px 0 0;
    }
    
    .editor-header strong {
      color: #333;
      font-size: 1rem;
    }
    
    .reset-btn {
      padding: 0.5rem 1rem;
      background: #ff9800;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: background 0.3s;
    }
    
    .reset-btn:hover {
      background: #f57c00;
    }
    
    .template-textarea {
      width: 100%;
      min-height: 300px;
      padding: 1rem;
      border: 1px solid #ddd;
      border-radius: 0 0 4px 4px;
      font-family: 'Courier New', monospace;
      font-size: 0.9rem;
      line-height: 1.5;
      resize: vertical;
    }
    
    .template-textarea:focus {
      outline: none;
      border-color: #4CAF50;
    }
    
    .placeholders-section {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .placeholders-section strong {
      color: #333;
      font-size: 1rem;
      padding: 0.75rem;
      background: #f0f0f0;
      border-radius: 4px;
    }
    
    .placeholders-table {
      width: 100%;
      border-collapse: collapse;
      border: 1px solid #ddd;
      border-radius: 4px;
      overflow: hidden;
    }
    
    .placeholders-table th,
    .placeholders-table td {
      padding: 0.75rem;
      text-align: left;
      border-bottom: 1px solid #ddd;
    }
    
    .placeholders-table th {
      background: #f9f9f9;
      font-weight: 600;
      color: #333;
    }
    
    .placeholders-table tr:last-child td {
      border-bottom: none;
    }
    
    .placeholders-table code {
      background: #e8f5e9;
      padding: 0.2rem 0.4rem;
      border-radius: 3px;
      font-family: 'Courier New', monospace;
      font-size: 0.85rem;
      color: #2e7d32;
    }
    
    .preview-section {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    
    .preview-section strong {
      color: #333;
      font-size: 1rem;
      padding: 0.75rem;
      background: #f0f0f0;
      border-radius: 4px;
    }
    
    .preview-content {
      background: #f9f9f9;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 1rem;
      font-family: 'Courier New', monospace;
      font-size: 0.85rem;
      line-height: 1.5;
      overflow-x: auto;
      white-space: pre;
      color: #333;
    }
    
    .form-actions {
      display: flex;
      justify-content: flex-end;
      gap: 1rem;
      margin-top: 1rem;
    }
    
    .save-btn {
      padding: 0.75rem 2rem;
      background: #4CAF50;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 500;
      transition: background 0.3s;
    }
    
    .save-btn:hover {
      background: #45a049;
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
      
      .editor-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
      }
      
      .reset-btn {
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
    server_url: 'http://localhost:8080',
    docker_compose_template: ''
  };
  isAdmin = this.authService.isAdmin();
  placeholders: any[] = [];
  previewTemplate: string = '';
  templateOriginal: string = '';

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
    this.loadPlaceholders();
  }

  loadSettings(): void {
    this.apiService.getSettings().subscribe({
      next: (settings: Settings) => {
        this.settings = settings;
        this.templateOriginal = settings.docker_compose_template;
        this.updatePreview();
      },
      error: (err: any) => {
        console.error('Failed to load settings:', err);
        this.notificationService.notify('Failed to load settings');
      }
    });
  }

  loadPlaceholders(): void {
    this.apiService.getPlaceholders().subscribe({
      next: (response: any) => {
        this.placeholders = response.placeholders;
      },
      error: (err: any) => {
        console.error('Failed to load placeholders:', err);
      }
    });
  }

  saveSettings(): void {
    this.apiService.updateSettings({
      punchy_enabled: this.settings.punchy_enabled,
      client_docker_image: this.settings.client_docker_image,
      server_url: this.settings.server_url,
      docker_compose_template: this.settings.docker_compose_template
    }).subscribe({
      next: (updated: Settings) => {
        this.settings = updated;
        this.templateOriginal = updated.docker_compose_template;
        this.notificationService.notify('Settings saved successfully', 'success');
        this.updatePreview();
      },
      error: (err: any) => {
        console.error('Failed to save settings:', err);
        this.notificationService.notify('Failed to save settings: ' + (err.error?.detail || 'Unknown error'));
        // Reload settings to revert UI
        this.loadSettings();
      }
    });
  }

  resetTemplate(): void {
    if (confirm('Are you sure you want to reset the template to default? This will discard your current template.')) {
      const defaultTemplate = `services:
  nebula-client:
    image: {{CLIENT_DOCKER_IMAGE}}
    container_name: nebula-{{CLIENT_NAME}}
    restart: unless-stopped
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun
    environment:
      SERVER_URL: {{SERVER_URL}}
      CLIENT_TOKEN: {{CLIENT_TOKEN}}
      POLL_INTERVAL_HOURS: {{POLL_INTERVAL_HOURS}}
    volumes:
      - ./nebula-config:/etc/nebula
      - ./nebula-data:/var/lib/nebula
    network_mode: host`;
      this.settings.docker_compose_template = defaultTemplate;
      this.updatePreview();
    }
  }

  updatePreview(): void {
    // Replace placeholders with sample data for preview
    let preview = this.settings.docker_compose_template;
    preview = preview.replace(/\{\{CLIENT_NAME\}\}/g, 'example-client');
    preview = preview.replace(/\{\{CLIENT_TOKEN\}\}/g, 'abc123xyz789...');
    preview = preview.replace(/\{\{SERVER_URL\}\}/g, this.settings.server_url || 'http://localhost:8080');
    preview = preview.replace(/\{\{CLIENT_DOCKER_IMAGE\}\}/g, this.settings.client_docker_image || 'ghcr.io/kumpeapps/managed-nebula/client:latest');
    preview = preview.replace(/\{\{POLL_INTERVAL_HOURS\}\}/g, '24');
    this.previewTemplate = preview;
  }

  onTemplateChange(): void {
    this.updatePreview();
  }
}
