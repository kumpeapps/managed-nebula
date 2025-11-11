import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject, ReplaySubject, tap, catchError, of, finalize } from 'rxjs';
import { Router } from '@angular/router';
import { User } from '../models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = '/api/v1';
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  
  // Observable that emits once when initial auth check is complete
  private authCheckedSubject = new ReplaySubject<boolean>(1);
  public authChecked$ = this.authCheckedSubject.asObservable();

  constructor(
    private http: HttpClient,
    private router: Router
  ) {
    this.checkAuth();
  }

  /**
   * Check if user is authenticated by fetching current user
   */
  private checkAuth(): void {
    this.http.get<User>(`${this.apiUrl}/auth/me`, { withCredentials: true })
      .pipe(
        catchError(() => of(null)),
        finalize(() => this.authCheckedSubject.next(true))
      )
      .subscribe((user: User | null) => {
        this.currentUserSubject.next(user);
      });
  }

  /**
   * Login with username and password
   */
  login(email: string, password: string): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/auth/login`, { email, password }, {
      withCredentials: true
    }).pipe(
      tap((user: User) => {
        this.currentUserSubject.next(user);
      })
    );
  }

  /**
   * Logout current user
   */
  logout(): Observable<any> {
    return this.http.post(`${this.apiUrl}/auth/logout`, {}, { withCredentials: true }).pipe(
      tap(() => {
        this.currentUserSubject.next(null);
        this.router.navigate(['/login']);
      })
    );
  }

  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return this.currentUserSubject.value !== null;
  }

  /**
   * Check if current user is admin
   */
  isAdmin(): boolean {
    const user = this.currentUserSubject.value;
    return user?.is_admin ?? false;
  }

  /**
   * Get current user
   */
  getCurrentUser(): User | null {
    return this.currentUserSubject.value;
  }
}
