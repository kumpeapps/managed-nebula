import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  template: `
    <app-notifications></app-notifications>
    <router-outlet></router-outlet>
  `,
  styles: []
})
export class AppComponent {
  title = 'managed-nebula-frontend';
}
