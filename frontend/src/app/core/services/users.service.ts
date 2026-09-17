import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { Permission, Role, RoleCreate, User, UserCreate } from '../models/rbac.models';

@Injectable({ providedIn: 'root' })
export class UsersService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}`;

  listUsers(): Observable<User[]> {
    return this.http.get<User[]>(`${this.base}/users`);
  }

  createUser(payload: UserCreate): Observable<User> {
    return this.http.post<User>(`${this.base}/users`, payload);
  }

  deactivateUser(userId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/users/${userId}`);
  }

  listRoles(): Observable<Role[]> {
    return this.http.get<Role[]>(`${this.base}/roles`);
  }

  createRole(payload: RoleCreate): Observable<Role> {
    return this.http.post<Role>(`${this.base}/roles`, payload);
  }

  updateRole(roleId: string, payload: Partial<RoleCreate>): Observable<Role> {
    return this.http.put<Role>(`${this.base}/roles/${roleId}`, payload);
  }

  deleteRole(roleId: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/roles/${roleId}`);
  }

  listPermissions(): Observable<Permission[]> {
    return this.http.get<Permission[]>(`${this.base}/permissions`);
  }
}
