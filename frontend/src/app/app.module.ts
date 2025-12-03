import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { provideHttpClient, withInterceptorsFromDi, HTTP_INTERCEPTORS } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { CommonModule, DatePipe } from '@angular/common';
import { provideZoneChangeDetection } from '@angular/core';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { LoginComponent } from './components/login.component';
import { DashboardComponent } from './components/dashboard.component';
import { ClientsComponent } from './components/clients.component';
import { ClientDetailComponent } from './components/client-detail.component';
import { GroupsComponent } from './components/groups.component';
import { FirewallRulesComponent } from './components/firewall-rulesets.component';
import { IPPoolsComponent } from './components/ip-pools.component';
import { IPGroupsComponent } from './components/ip-groups.component';
import { CAComponent } from './components/ca.component';
import { UsersComponent } from './components/users.component';
import { UserGroupsComponent } from './components/user-groups.component';
import { PermissionsComponent } from './components/permissions.component';
import { SettingsComponent } from './components/settings.component';
import { ProfileComponent } from './components/profile.component';
import { NavbarComponent } from './components/navbar.component';
import { NotificationsComponent } from './components/notifications.component';

import { AuthService } from './services/auth.service';
import { ApiService } from './services/api.service';
import { NotificationService } from './services/notification.service';
import { AuthGuard } from './guards/auth.guard';
import { AuthInterceptor } from './interceptors/auth.interceptor';
import { LocalDatePipe } from './pipes/local-date.pipe';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    DashboardComponent,
    ClientsComponent,
    ClientDetailComponent,
    GroupsComponent,
    FirewallRulesComponent,
    IPPoolsComponent,
    IPGroupsComponent,
    CAComponent,
    UsersComponent,
    UserGroupsComponent,
    PermissionsComponent,
    SettingsComponent,
    ProfileComponent,
    NavbarComponent,
    NotificationsComponent,
    LocalDatePipe
  ],
  imports: [
    BrowserModule,
    CommonModule,
    AppRoutingModule,
    FormsModule
  ],
  providers: [
    provideZoneChangeDetection(),
    provideHttpClient(withInterceptorsFromDi()),
    {
      provide: HTTP_INTERCEPTORS,
      useClass: AuthInterceptor,
      multi: true
    },
    AuthService,
    ApiService,
    NotificationService,
    AuthGuard,
    DatePipe
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
