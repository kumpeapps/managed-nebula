import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './components/login.component';
import { DashboardComponent } from './components/dashboard.component';
import { ClientsComponent } from './components/clients.component';
import { ClientDetailComponent } from './components/client-detail.component';
import { GroupsComponent } from './components/groups.component';
import { AuthGuard } from './guards/auth.guard';
import { FirewallRulesComponent } from './components/firewall-rulesets.component';
import { IPPoolsComponent } from './components/ip-pools.component';
import { IPGroupsComponent } from './components/ip-groups.component';
import { CAComponent } from './components/ca.component';
import { UsersComponent } from './components/users.component';
import { UserGroupsComponent } from './components/user-groups.component';
import { SettingsComponent } from './components/settings.component';
import { EnrollmentCodesComponent } from './components/enrollment-codes.component';

const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
  { path: 'clients', component: ClientsComponent, canActivate: [AuthGuard] },
  { path: 'clients/:id', component: ClientDetailComponent, canActivate: [AuthGuard] },
  { path: 'groups', component: GroupsComponent, canActivate: [AuthGuard] },
  { path: 'firewall-rules', component: FirewallRulesComponent, canActivate: [AuthGuard] },
  { path: 'ip-pools', component: IPPoolsComponent, canActivate: [AuthGuard] },
  { path: 'ip-groups', component: IPGroupsComponent, canActivate: [AuthGuard] },
  { path: 'ca', component: CAComponent, canActivate: [AuthGuard] },
  { path: 'users', component: UsersComponent, canActivate: [AuthGuard] },
  { path: 'user-groups', component: UserGroupsComponent, canActivate: [AuthGuard] },
  { path: 'settings', component: SettingsComponent, canActivate: [AuthGuard] },
  { path: 'enrollment', component: EnrollmentCodesComponent, canActivate: [AuthGuard] },
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
