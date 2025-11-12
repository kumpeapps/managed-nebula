import { Component, OnInit } from '@angular/core';
import { ApiService } from '../services/api.service';
import { AuthService } from '../services/auth.service';
import { FirewallRuleset, FirewallRule, Group, GroupRef } from '../models';

@Component({
  selector: 'app-firewall-rulesets',
  template: `
    <app-navbar></app-navbar>
    <div class="resource-page">
      <h2>Firewall Rulesets</h2>
      <div class="actions">
        <button class="btn btn-primary" (click)="startCreate()">New Ruleset</button>
      </div>

      <!-- Ruleset Editor Modal -->
      <div *ngIf="showForm" class="modal">
        <div class="modal-content">
          <h3>{{ editingRuleset ? 'Edit' : 'Create' }} Firewall Ruleset</h3>
          <form (ngSubmit)="saveRuleset()" #rulesetForm="ngForm">
            <div class="form-group">
              <label>Name *</label>
              <input class="form-control" name="name" [(ngModel)]="formData.name" required />
            </div>
            <div class="form-group">
              <label>Description</label>
              <textarea class="form-control" rows="2" name="description" [(ngModel)]="formData.description"></textarea>
            </div>

            <h4>Rules</h4>
            <div class="rules-list">
              <div class="rule-card" *ngFor="let rule of formData.rules; let i = index">
                <div class="rule-header">
                  <span>Rule {{i + 1}}</span>
                  <button type="button" class="btn btn-sm btn-danger" (click)="removeRule(i)">✕</button>
                </div>
                <div class="rule-fields">
                  <div class="form-row">
                    <div class="form-group">
                      <label>Direction *</label>
                      <select class="form-control" [(ngModel)]="rule.direction" name="direction{{i}}" required>
                        <option value="inbound">Inbound</option>
                        <option value="outbound">Outbound</option>
                      </select>
                    </div>
                    <div class="form-group">
                      <label>Port *</label>
                      <input class="form-control" placeholder="any, 80, 200-901, fragment" [(ngModel)]="rule.port" name="port{{i}}" required />
                    </div>
                    <div class="form-group">
                      <label>Protocol *</label>
                      <select class="form-control" [(ngModel)]="rule.proto" name="proto{{i}}" required>
                        <option value="any">any</option>
                        <option value="tcp">tcp</option>
                        <option value="udp">udp</option>
                        <option value="icmp">icmp</option>
                      </select>
                    </div>
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>Host</label>
                      <input class="form-control" placeholder="any or hostname" [(ngModel)]="rule.host" name="host{{i}}" />
                    </div>
                    <div class="form-group">
                      <label>CIDR</label>
                      <input class="form-control" placeholder="0.0.0.0/0 or specific" [(ngModel)]="rule.cidr" name="cidr{{i}}" />
                    </div>
                    <div class="form-group">
                      <label>Local CIDR</label>
                      <input class="form-control" placeholder="for unsafe_routes" [(ngModel)]="rule.local_cidr" name="local_cidr{{i}}" />
                    </div>
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>CA Name</label>
                      <input class="form-control" placeholder="issuing CA name" [(ngModel)]="rule.ca_name" name="ca_name{{i}}" />
                    </div>
                    <div class="form-group">
                      <label>CA SHA</label>
                      <input class="form-control" placeholder="issuing CA shasum" [(ngModel)]="rule.ca_sha" name="ca_sha{{i}}" />
                    </div>
                  </div>
                  <div class="form-group">
                    <label>Groups (AND'd together)</label>
                    <select multiple class="form-control" [(ngModel)]="rule.group_ids" name="groups{{i}}">
                      <option *ngFor="let g of allGroups" [value]="g.id">{{ g.name }}</option>
                    </select>
                  </div>
                </div>
              </div>
              <button type="button" class="btn btn-secondary" (click)="addRule()">+ Add Rule</button>
            </div>

            <div class="form-actions">
              <button type="button" (click)="cancelForm()" class="btn btn-secondary">Cancel</button>
              <button type="submit" class="btn btn-primary" [disabled]="saving || rulesetForm.invalid">{{ saving ? 'Saving...' : 'Save' }}</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Rulesets Table -->
      <table *ngIf="rulesets.length" class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Rules</th>
            <th>Clients</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let rs of rulesets">
            <td>{{ rs.name }}</td>
            <td>{{ rs.description || '—' }}</td>
            <td>{{ rs.rules.length }}</td>
            <td>{{ rs.client_count }}</td>
            <td>
              <button class="btn btn-sm btn-primary" (click)="startEdit(rs)">Edit</button>
              <button class="btn btn-sm btn-danger" (click)="deleteRuleset(rs.id)">Delete</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p *ngIf="!rulesets.length">No firewall rulesets defined.</p>
    </div>
  `,
  styles: [`
    .resource-page {
      padding: 1.5rem;
      background: #f5f5f5;
      min-height: 100vh;
    }
    h2 { color: #333; margin-bottom: 1rem; }
    h4 { margin-top: 1.5rem; color: #555; }
    .actions { margin-bottom: 1rem; }
    .table { width: 100%; border-collapse: collapse; background: white; }
    th, td { padding: 0.75rem; border-bottom: 1px solid #eee; text-align: left; }
    th { background: #f9f9f9; font-weight: 600; color: #666; }
    .form-control { width: 100%; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; }
    .modal {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
      overflow-y: auto;
    }
    .modal-content {
      background: #fff;
      padding: 2rem;
      width: 800px;
      max-width: 95%;
      border-radius: 8px;
      max-height: 90vh;
      overflow-y: auto;
    }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; margin-bottom: 0.25rem; font-weight: 500; color: #333; }
    .form-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
    .form-actions { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 1.5rem; }
    .rules-list { margin-top: 1rem; }
    .rule-card {
      border: 1px solid #ddd;
      border-radius: 6px;
      padding: 1rem;
      margin-bottom: 1rem;
      background: #fafafa;
    }
    .rule-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      font-weight: 600;
      color: #555;
    }
    .rule-fields { display: flex; flex-direction: column; gap: 0.5rem; }
    .btn {
      padding: 0.5rem 1rem;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      font-size: 0.9rem;
      transition: background 0.2s;
    }
    .btn-primary { background: #4CAF50; color: white; }
    .btn-primary:hover { background: #45a049; }
    .btn-secondary { background: #6c757d; color: white; }
    .btn-secondary:hover { background: #5a6268; }
    .btn-danger { background: #dc3545; color: white; }
    .btn-danger:hover { background: #c82333; }
    .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.85rem; }
    .btn:disabled { opacity: 0.6; cursor: not-allowed; }
    
    @media (max-width: 768px) {
      .resource-page {
        padding: 1rem;
      }
      
      .modal-content {
        padding: 1rem;
        width: 95%;
      }
      
      .form-row {
        grid-template-columns: 1fr;
      }
      
      .form-actions {
        flex-direction: column;
      }
      
      .form-actions button {
        width: 100%;
      }
      
      .table-responsive {
        overflow-x: auto;
      }
    }
  `]
})
export class FirewallRulesComponent implements OnInit {
  rulesets: FirewallRuleset[] = [];
  allGroups: Group[] = [];
  showForm = false;
  saving = false;
  editingRuleset: FirewallRuleset | null = null;
  formData: {
    name: string;
    description: string;
    rules: Array<{
      direction: string;
      port: string;
      proto: string;
      host?: string;
      cidr?: string;
      local_cidr?: string;
      ca_name?: string;
      ca_sha?: string;
      group_ids?: number[];
    }>;
  } = this.getEmptyForm();

  constructor(private api: ApiService, private auth: AuthService) {}

  ngOnInit(): void {
    this.loadRulesets();
    this.loadGroups();
  }

  getEmptyForm() {
    return {
      name: '',
      description: '',
      rules: [{ direction: 'inbound', port: 'any', proto: 'any', group_ids: [] }]
    };
  }

  loadRulesets(): void {
    this.api.getFirewallRulesets().subscribe({
      next: (rs: FirewallRuleset[]) => (this.rulesets = rs),
      error: (e: any) => console.error('Failed to load firewall rulesets', e)
    });
  }

  loadGroups(): void {
    this.api.getGroups().subscribe({
      next: (groups: Group[]) => (this.allGroups = groups),
      error: (e: any) => console.error('Failed to load groups', e)
    });
  }

  startCreate(): void {
    this.editingRuleset = null;
    this.formData = this.getEmptyForm();
    this.showForm = true;
  }

  startEdit(ruleset: FirewallRuleset): void {
    this.editingRuleset = ruleset;
    this.formData = {
      name: ruleset.name,
      description: ruleset.description || '',
      rules: ruleset.rules.map(r => ({
        direction: r.direction,
        port: r.port,
        proto: r.proto,
        host: r.host || undefined,
        cidr: r.cidr || undefined,
        local_cidr: r.local_cidr || undefined,
        ca_name: r.ca_name || undefined,
        ca_sha: r.ca_sha || undefined,
        group_ids: r.groups.map(g => g.id)
      }))
    };
    this.showForm = true;
  }

  addRule(): void {
    this.formData.rules.push({ direction: 'inbound', port: 'any', proto: 'any', group_ids: [] });
  }

  removeRule(idx: number): void {
    this.formData.rules.splice(idx, 1);
  }

  cancelForm(): void {
    this.showForm = false;
    this.editingRuleset = null;
  }

  saveRuleset(): void {
    if (!this.formData.name || this.formData.rules.length === 0) return;
    this.saving = true;

    const payload = {
      name: this.formData.name,
      description: this.formData.description || undefined,
      rules: this.formData.rules
    };

    const operation = this.editingRuleset
      ? this.api.updateFirewallRuleset(this.editingRuleset.id, payload)
      : this.api.createFirewallRuleset(payload);

    operation.subscribe({
      next: () => {
        this.loadRulesets();
        this.cancelForm();
        this.saving = false;
      },
      error: (e: any) => {
        alert('Save failed: ' + (e.error?.detail || 'Unknown error'));
        this.saving = false;
      }
    });
  }

  deleteRuleset(id: number): void {
    if (!confirm('Delete this ruleset?')) return;
    this.api.deleteFirewallRuleset(id).subscribe({
      next: () => this.loadRulesets(),
      error: (e: any) => alert('Delete failed: ' + (e.error?.detail || 'Unknown error'))
    });
  }
}
