---
applies_to:
  - frontend/**/*
  - "**/*.ts"
  - "**/*.html"
  - "**/*.scss"
  - "**/*.css"
---

# Frontend (Angular) Instructions

## Overview
The frontend is an Angular 17 Single Page Application (SPA) that provides a web-based management interface for the Nebula VPN platform. It communicates with the FastAPI backend via REST API.

## Tech Stack
- **Framework**: Angular 17 with standalone components
- **UI Library**: Angular Material
- **State Management**: RxJS + Services
- **HTTP Client**: Angular HttpClient with interceptors
- **Build Tool**: Angular CLI
- **Authentication**: Session-based (cookies)

## Development Commands

### Setup and Installation
```bash
cd frontend
npm install
```

### Development Server
```bash
npm start
# Opens at http://localhost:4200
# Proxies API requests to http://localhost:8080
```

### Building
```bash
# Development build
npm run build

# Production build (minified, optimized)
npm run build:prod

# Output will be in dist/ directory
```

### Testing
```bash
# Run unit tests
npm test

# Run tests with coverage
npm run test:coverage

# Run e2e tests (if configured)
npm run e2e
```

### Linting and Formatting
```bash
# Lint TypeScript
npm run lint

# Format code (if prettier is configured)
npm run format
```

## Key Patterns and Conventions

### Component Architecture
- **Standalone components**: Use Angular 17+ standalone component pattern
- **Smart vs Presentational**: Separate container (smart) components from presentational components
- **Component communication**: Use `@Input()` and `@Output()` for parent-child, services for sibling communication

### API Communication
- **HttpClient**: Always use Angular's HttpClient service
- **Services**: API calls should be in dedicated service classes
- **Error Handling**: Use RxJS catchError and proper error propagation
- **Loading States**: Show loading indicators during async operations
- **Authentication**: Sessions managed via cookies, automatically sent by browser

Example service:
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ClientService {
  private apiUrl = '/api/v1/clients';

  constructor(private http: HttpClient) {}

  getClients(): Observable<Client[]> {
    return this.http.get<Client[]>(this.apiUrl);
  }

  getClient(id: number): Observable<Client> {
    return this.http.get<Client>(`${this.apiUrl}/${id}`);
  }

  updateClient(id: number, data: Partial<Client>): Observable<Client> {
    return this.http.put<Client>(`${this.apiUrl}/${id}`, data);
  }
}
```

### Routing
- **Lazy Loading**: Use lazy loading for feature modules
- **Route Guards**: Implement auth guards for protected routes
- **Navigation**: Use Angular Router service, not direct URL manipulation

### Forms
- **Reactive Forms**: Prefer Reactive Forms over Template-driven forms
- **Validation**: Use built-in validators and custom validators
- **Form State**: Handle pristine, dirty, valid, invalid states properly

Example:
```typescript
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

export class ClientFormComponent {
  clientForm: FormGroup;

  constructor(private fb: FormBuilder) {
    this.clientForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(3)]],
      is_lighthouse: [false],
      public_ip: ['', [Validators.pattern(/^\d+\.\d+\.\d+\.\d+$/)]],
      groups: [[]],
    });
  }

  onSubmit() {
    if (this.clientForm.valid) {
      // Handle submission
    }
  }
}
```

### Material Design
- **Consistent UI**: Use Angular Material components throughout
- **Theme**: Follow the configured theme colors
- **Responsive**: Use Material Layout (flex-layout) or CSS Grid for responsive designs
- **Accessibility**: Follow Material's a11y guidelines

### State Management
- **Services**: Use singleton services for shared state
- **RxJS**: Use BehaviorSubject or ReplaySubject for state streams
- **Observables**: Subscribe in templates with async pipe when possible

Example:
```typescript
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class StateService {
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  public currentUser$: Observable<User | null> = this.currentUserSubject.asObservable();

  setCurrentUser(user: User | null) {
    this.currentUserSubject.next(user);
  }
}
```

### TypeScript Best Practices
- **Strict Mode**: Enable strict TypeScript checking
- **Interfaces**: Define interfaces for all API response/request types
- **Type Safety**: Avoid `any` type - use proper types or `unknown`
- **Null Safety**: Handle null/undefined properly with optional chaining

### Common Pitfalls to Avoid
- ❌ Don't forget to unsubscribe from observables (use `takeUntil`, async pipe, or `take(1)`)
- ❌ Don't mutate state directly - create new objects
- ❌ Don't use jQuery or direct DOM manipulation - use Angular directives
- ❌ Don't make API calls in constructors - use `ngOnInit` lifecycle hook
- ❌ Don't forget error handling in HTTP requests
- ❌ Don't put business logic in templates - keep it in components/services
- ❌ Don't skip accessibility attributes (aria-labels, alt text, etc.)

### File Structure
```
frontend/
├── src/
│   ├── app/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # Page/route components
│   │   ├── services/        # API and state services
│   │   ├── guards/          # Route guards
│   │   ├── interceptors/    # HTTP interceptors
│   │   ├── models/          # TypeScript interfaces
│   │   └── app.component.ts # Root component
│   ├── assets/              # Static assets
│   └── styles/              # Global styles
├── angular.json             # Angular CLI configuration
├── tsconfig.json            # TypeScript configuration
└── package.json             # Dependencies
```

## Adding New Features

### Adding a New Page/Route
1. Create component: `ng generate component pages/my-page`
2. Add route in routing module
3. Add navigation link in menu/navbar
4. Create corresponding service if API calls needed
5. Add route guard if authentication required

### Adding a New Service
1. Create service: `ng generate service services/my-service`
2. Implement API methods using HttpClient
3. Add error handling
4. Provide in root or feature module
5. Test the service

### Adding a Form
1. Create form component with Reactive Forms
2. Define FormGroup with validators
3. Add Material Form controls in template
4. Handle form submission
5. Show validation errors
6. Add loading state during submission

### Adding Material Components
1. Import component module (if not already imported)
2. Add component in template
3. Follow Material Design guidelines
4. Ensure accessibility
5. Test responsive behavior

## Environment Configuration
- Development: API proxied to localhost:8080
- Production: API URL from environment variable
- Configure in `src/environments/`

## Authentication Flow
1. User logs in via `/api/v1/auth/login`
2. Backend sets session cookie
3. Cookie automatically sent with all requests
4. Frontend checks auth state on init
5. Logout via `/api/v1/auth/logout`
6. Redirect to login on 401 errors

## Styling Guidelines
- Use SCSS for styling
- Follow BEM naming convention for classes
- Use Material theme colors
- Make responsive (mobile-first)
- Test in multiple browsers

## Accessibility
- Add proper ARIA labels
- Ensure keyboard navigation works
- Test with screen readers
- Maintain good contrast ratios
- Provide alternative text for images
