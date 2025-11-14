import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export interface ErrorMessage {
  message: string;
  type: 'error' | 'warning' | 'info' | 'success';
  timestamp: number;
}

/**
 * Centralized error notification service to display user-friendly error messages.
 * Components can call notify() to display alerts, and subscribe to errors$ to show banners.
 */
@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private errorsSubject = new Subject<ErrorMessage>();
  public errors$ = this.errorsSubject.asObservable();

  /**
   * Display an error notification (typically from HTTP error responses).
   * @param message The error message or detail string.
   * @param type The severity level (default 'error').
   */
  notify(message: string, type: 'error' | 'warning' | 'info' | 'success' = 'error'): void {
    this.errorsSubject.next({ message, type, timestamp: Date.now() });
  }

  /**
   * Helper to extract error detail from HTTP error response.
   * @param error The HTTP error object (typically from catchError).
   * @returns User-friendly error message string.
   */
  extractError(error: any): string {
    if (error?.error?.detail) {
      return Array.isArray(error.error.detail)
        ? error.error.detail.map((d: any) => d.msg || d).join(', ')
        : error.error.detail;
    }
    if (error?.message) return error.message;
    if (error?.statusText) return error.statusText;
    return 'Unknown error occurred';
  }

  /**
   * Display HTTP error as notification and optionally log to console.
   * @param error The HTTP error object.
   * @param context Optional context string (e.g., "Failed to create group").
   */
  notifyHttpError(error: any, context?: string): void {
    const detail = this.extractError(error);
    const message = context ? `${context}: ${detail}` : detail;
    console.error(context || 'HTTP Error', error);
    this.notify(message, 'error');
  }

  /**
   * Convenience method to show error messages.
   * @param message The error message to display.
   */
  showError(message: string): void {
    this.notify(message, 'error');
  }

  /**
   * Convenience method to show success messages.
   * @param message The success message to display.
   */
  showSuccess(message: string): void {
    this.notify(message, 'success');
  }

  /**
   * Convenience method to show warning messages.
   * @param message The warning message to display.
   */
  showWarning(message: string): void {
    this.notify(message, 'warning');
  }

  /**
   * Convenience method to show info messages.
   * @param message The info message to display.
   */
  showInfo(message: string): void {
    this.notify(message, 'info');
  }
}
