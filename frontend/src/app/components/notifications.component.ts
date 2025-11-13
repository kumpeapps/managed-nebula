import { Component, OnInit, OnDestroy } from '@angular/core';
import { NotificationService, ErrorMessage } from '../services/notification.service';
import { Subscription } from 'rxjs';

/**
 * Global notification banner component to display error/success messages.
 * Place this component in the app root or layout to show notifications from any service.
 */
@Component({
    selector: 'app-notifications',
    template: `
    <div class="notification-container">
      <div *ngFor="let msg of messages" 
           class="notification" 
           [ngClass]="'notification-' + msg.type"
           (click)="dismiss(msg)">
        {{ msg.message }}
        <button class="close-btn" (click)="dismiss(msg); $event.stopPropagation()">×</button>
      </div>
    </div>
  `,
    styles: [`
    .notification-container {
      position: fixed;
      top: 1rem;
      right: 1rem;
      z-index: 9999;
      max-width: 400px;
    }
    
    .notification {
      background: white;
      padding: 1rem 2.5rem 1rem 1rem;
      margin-bottom: 0.5rem;
      border-radius: 4px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      cursor: pointer;
      position: relative;
      animation: slideIn 0.3s ease;
      border-left: 4px solid #ccc;
    }
    
    @keyframes slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to { transform: translateX(0); opacity: 1; }
    }
    
    .notification-error {
      border-left-color: #dc3545;
      background: #f8d7da;
      color: #721c24;
    }
    
    .notification-warning {
      border-left-color: #ffc107;
      background: #fff3cd;
      color: #856404;
    }
    
    .notification-info {
      border-left-color: #17a2b8;
      background: #d1ecf1;
      color: #0c5460;
    }
    
    .notification-success {
      border-left-color: #28a745;
      background: #d4edda;
      color: #155724;
    }
    
    .close-btn {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      background: transparent;
      border: none;
      font-size: 1.5rem;
      line-height: 1;
      cursor: pointer;
      color: inherit;
      opacity: 0.6;
    }
    
    .close-btn:hover {
      opacity: 1;
    }
  `],
    standalone: false
})
export class NotificationsComponent implements OnInit, OnDestroy {
  messages: ErrorMessage[] = [];
  private subscription?: Subscription;

  constructor(private notificationService: NotificationService) {}

  ngOnInit(): void {
    this.subscription = this.notificationService.errors$.subscribe((msg: ErrorMessage) => {
      this.messages.push(msg);
      // Auto-dismiss after 6 seconds
      setTimeout(() => this.dismiss(msg), 6000);
    });
  }

  ngOnDestroy(): void {
    this.subscription?.unsubscribe();
  }

  dismiss(msg: ErrorMessage): void {
    this.messages = this.messages.filter(m => m !== msg);
  }
}
