import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api.service';
import { NotificationService } from '../services/notification.service';
import { EnrollmentCode, EnrollmentCodeCreateRequest, Client } from '../models';
import { QRCodeModule } from 'angularx-qrcode';

@Component({
  selector: 'app-enrollment-codes',
  standalone: true,
  imports: [CommonModule, FormsModule, QRCodeModule],
  template: `
    <div class="container mt-4">
      <h2>Mobile Enrollment Codes</h2>
      <p class="text-muted">
        Generate enrollment codes for Mobile Nebula devices. Users can scan the QR code or use the enrollment URL to configure their devices.
      </p>

      <!-- Generate Code Button -->
      <div class="mb-4">
        <button class="btn btn-primary" (click)="showCreateModal = true">
          <i class="bi bi-plus-circle"></i> Generate Enrollment Code
        </button>
      </div>

      <!-- Enrollment Codes List -->
      <div class="card">
        <div class="card-header">
          <h5 class="mb-0">Enrollment Codes</h5>
        </div>
        <div class="card-body">
          <div *ngIf="loading" class="text-center py-4">
            <div class="spinner-border" role="status">
              <span class="visually-hidden">Loading...</span>
            </div>
          </div>

          <div *ngIf="!loading && enrollmentCodes.length === 0" class="alert alert-info">
            No enrollment codes found. Click "Generate Enrollment Code" to create one.
          </div>

          <div *ngIf="!loading && enrollmentCodes.length > 0" class="table-responsive">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>Client</th>
                  <th>Device Info</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Expires</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let code of enrollmentCodes">
                  <td>
                    <strong>{{ code.client_name }}</strong>
                  </td>
                  <td>
                    <span *ngIf="code.device_name">{{ code.device_name }}</span>
                    <span *ngIf="code.platform" class="badge bg-info ms-1">{{ code.platform }}</span>
                    <span *ngIf="!code.device_name && !code.is_used" class="text-muted">Not enrolled yet</span>
                  </td>
                  <td>
                    <span class="badge" [ngClass]="{
                      'bg-success': code.is_used,
                      'bg-warning': !code.is_used && !isExpired(code),
                      'bg-danger': isExpired(code)
                    }">
                      {{ getStatusText(code) }}
                    </span>
                  </td>
                  <td>{{ formatDate(code.created_at) }}</td>
                  <td>
                    {{ formatDate(code.expires_at) }}
                    <span *ngIf="!code.is_used && !isExpired(code)" class="text-muted small d-block">
                      {{ getTimeRemaining(code) }}
                    </span>
                  </td>
                  <td>
                    <button class="btn btn-sm btn-info me-1" 
                            (click)="showCodeDetails(code)"
                            [disabled]="code.is_used">
                      <i class="bi bi-qr-code"></i> QR Code
                    </button>
                    <button class="btn btn-sm btn-outline-secondary me-1"
                            (click)="copyToClipboard(code.enrollment_url, 'URL')"
                            [disabled]="code.is_used">
                      <i class="bi bi-link-45deg"></i> Copy URL
                    </button>
                    <button class="btn btn-sm btn-outline-danger"
                            (click)="deleteCode(code)"
                            [disabled]="code.is_used">
                      <i class="bi bi-trash"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Create Modal -->
      <div class="modal" [class.show]="showCreateModal" [style.display]="showCreateModal ? 'block' : 'none'" 
           tabindex="-1" *ngIf="showCreateModal">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Generate Enrollment Code</h5>
              <button type="button" class="btn-close" (click)="closeCreateModal()"></button>
            </div>
            <div class="modal-body">
              <form>
                <div class="mb-3">
                  <label for="clientSelect" class="form-label">Client *</label>
                  <select class="form-select" id="clientSelect" [(ngModel)]="newCode.client_id" name="client_id" required>
                    <option [value]="undefined">Select a client...</option>
                    <option *ngFor="let client of clients" [value]="client.id">
                      {{ client.name }} ({{ client.ip_address }})
                    </option>
                  </select>
                </div>
                <div class="mb-3">
                  <label for="validityHours" class="form-label">
                    Validity Period (hours) *
                    <small class="text-muted">1-168 hours (7 days max)</small>
                  </label>
                  <input type="number" class="form-control" id="validityHours" 
                         [(ngModel)]="newCode.validity_hours" name="validity_hours"
                         min="1" max="168" required>
                </div>
                <div class="mb-3">
                  <label for="deviceName" class="form-label">
                    Device Name/Notes
                    <small class="text-muted">(optional)</small>
                  </label>
                  <input type="text" class="form-control" id="deviceName" 
                         [(ngModel)]="newCode.device_name" name="device_name"
                         placeholder="e.g., John's iPhone">
                </div>
              </form>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" (click)="closeCreateModal()">Cancel</button>
              <button type="button" class="btn btn-primary" 
                      (click)="createCode()"
                      [disabled]="!newCode.client_id || !newCode.validity_hours || creating">
                {{ creating ? 'Generating...' : 'Generate Code' }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-backdrop fade" [class.show]="showCreateModal" *ngIf="showCreateModal"></div>

      <!-- QR Code Display Modal -->
      <div class="modal" [class.show]="showQRModal" [style.display]="showQRModal ? 'block' : 'none'" 
           tabindex="-1" *ngIf="showQRModal && selectedCode">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Enrollment Code for {{ selectedCode.client_name }}</h5>
              <button type="button" class="btn-close" (click)="showQRModal = false"></button>
            </div>
            <div class="modal-body text-center">
              <div class="mb-4">
                <h6>Scan with Mobile Nebula App</h6>
                <div class="d-flex justify-content-center">
                  <qrcode [qrdata]="selectedCode.enrollment_url" 
                          [width]="300" 
                          [errorCorrectionLevel]="'M'"
                          [colorDark]="'#000000'"
                          [colorLight]="'#ffffff'"></qrcode>
                </div>
              </div>
              
              <div class="mb-3">
                <h6>Enrollment URL</h6>
                <div class="input-group">
                  <input type="text" class="form-control" [value]="selectedCode.enrollment_url" readonly>
                  <button class="btn btn-outline-secondary" type="button" 
                          (click)="copyToClipboard(selectedCode.enrollment_url, 'URL')">
                    <i class="bi bi-clipboard"></i> Copy
                  </button>
                </div>
              </div>

              <div class="mb-3">
                <h6>Enrollment Code</h6>
                <div class="input-group">
                  <input type="text" class="form-control font-monospace" [value]="selectedCode.code" readonly>
                  <button class="btn btn-outline-secondary" type="button" 
                          (click)="copyToClipboard(selectedCode.code, 'Code')">
                    <i class="bi bi-clipboard"></i> Copy
                  </button>
                </div>
              </div>

              <div class="alert alert-info">
                <i class="bi bi-info-circle"></i> 
                This code expires {{ formatDate(selectedCode.expires_at) }} ({{ getTimeRemaining(selectedCode) }})
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" (click)="showQRModal = false">Close</button>
            </div>
          </div>
        </div>
      </div>
      <div class="modal-backdrop fade" [class.show]="showQRModal" *ngIf="showQRModal"></div>
    </div>
  `,
  styles: [`
    .modal.show {
      display: block !important;
    }
    .modal-backdrop.show {
      opacity: 0.5;
    }
    .font-monospace {
      font-family: monospace;
      font-size: 0.9rem;
    }
  `]
})
export class EnrollmentCodesComponent implements OnInit {
  enrollmentCodes: EnrollmentCode[] = [];
  clients: Client[] = [];
  loading = false;
  creating = false;
  showCreateModal = false;
  showQRModal = false;
  selectedCode: EnrollmentCode | null = null;

  newCode: EnrollmentCodeCreateRequest = {
    client_id: undefined as any,
    validity_hours: 24,
    device_name: null
  };

  constructor(
    private apiService: ApiService,
    private notificationService: NotificationService
  ) {}

  ngOnInit() {
    this.loadEnrollmentCodes();
    this.loadClients();
  }

  loadEnrollmentCodes() {
    this.loading = true;
    this.apiService.getEnrollmentCodes().subscribe({
      next: (codes) => {
        this.enrollmentCodes = codes;
        this.loading = false;
      },
      error: (err) => {
        this.notificationService.showError('Failed to load enrollment codes: ' + (err.error?.detail || err.message));
        this.loading = false;
      }
    });
  }

  loadClients() {
    this.apiService.getClients().subscribe({
      next: (clients) => {
        this.clients = clients.filter(c => !c.is_blocked && c.ip_address);
      },
      error: (err) => {
        this.notificationService.showError('Failed to load clients: ' + (err.error?.detail || err.message));
      }
    });
  }

  createCode() {
    if (!this.newCode.client_id || !this.newCode.validity_hours) {
      this.notificationService.showError('Please fill in all required fields');
      return;
    }

    this.creating = true;
    this.apiService.createEnrollmentCode(this.newCode).subscribe({
      next: (code) => {
        this.notificationService.showSuccess('Enrollment code generated successfully');
        this.enrollmentCodes.unshift(code); // Add to top of list
        this.closeCreateModal();
        this.creating = false;
        
        // Show QR code immediately
        this.showCodeDetails(code);
      },
      error: (err) => {
        this.notificationService.showError('Failed to generate code: ' + (err.error?.detail || err.message));
        this.creating = false;
      }
    });
  }

  deleteCode(code: EnrollmentCode) {
    if (code.is_used) {
      this.notificationService.showError('Cannot delete used enrollment code');
      return;
    }

    if (!confirm(`Delete enrollment code for ${code.client_name}?`)) {
      return;
    }

    this.apiService.deleteEnrollmentCode(code.id).subscribe({
      next: () => {
        this.notificationService.showSuccess('Enrollment code deleted');
        this.enrollmentCodes = this.enrollmentCodes.filter(c => c.id !== code.id);
      },
      error: (err) => {
        this.notificationService.showError('Failed to delete code: ' + (err.error?.detail || err.message));
      }
    });
  }

  showCodeDetails(code: EnrollmentCode) {
    this.selectedCode = code;
    this.showQRModal = true;
  }

  closeCreateModal() {
    this.showCreateModal = false;
    this.newCode = {
      client_id: undefined as any,
      validity_hours: 24,
      device_name: null
    };
  }

  copyToClipboard(text: string, label: string) {
    navigator.clipboard.writeText(text).then(() => {
      this.notificationService.showSuccess(`${label} copied to clipboard`);
    }).catch(() => {
      this.notificationService.showError('Failed to copy to clipboard');
    });
  }

  isExpired(code: EnrollmentCode): boolean {
    return new Date(code.expires_at) < new Date();
  }

  getStatusText(code: EnrollmentCode): string {
    if (code.is_used) return 'Used';
    if (this.isExpired(code)) return 'Expired';
    return 'Active';
  }

  formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleString();
  }

  getTimeRemaining(code: EnrollmentCode): string {
    const now = new Date();
    const expires = new Date(code.expires_at);
    const diff = expires.getTime() - now.getTime();

    if (diff <= 0) return 'Expired';

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${days} day${days !== 1 ? 's' : ''} remaining`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m remaining`;
    } else {
      return `${minutes}m remaining`;
    }
  }
}
