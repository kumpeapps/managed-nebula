import { Component } from '@angular/core';

@Component({
    selector: 'app-root',
    template: `
    <app-notifications></app-notifications>
    <router-outlet></router-outlet>
  `,
    styles: [],
    standalone: false
})
export class AppComponent {
  title = 'managed-nebula-frontend';
}
