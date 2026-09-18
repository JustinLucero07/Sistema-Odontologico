import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  Budget,
  BudgetCreate,
  BudgetStatus,
  Diagnosis,
  DiagnosisCreate,
  TreatmentPlan,
  TreatmentPlanCreate,
  TreatmentPlanItemCreate,
  TreatmentPlanItemStatus,
} from '../models/treatment.models';

@Injectable({ providedIn: 'root' })
export class TreatmentPlansService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  listDiagnoses(patientId: string): Observable<Diagnosis[]> {
    return this.http.get<Diagnosis[]>(`${this.api}/patients/${patientId}/diagnoses`);
  }

  createDiagnosis(patientId: string, payload: DiagnosisCreate): Observable<Diagnosis> {
    return this.http.post<Diagnosis>(`${this.api}/patients/${patientId}/diagnoses`, payload);
  }

  listPlans(patientId: string): Observable<TreatmentPlan[]> {
    return this.http.get<TreatmentPlan[]>(`${this.api}/patients/${patientId}/treatment-plans`);
  }

  createPlan(patientId: string, payload: TreatmentPlanCreate): Observable<TreatmentPlan> {
    return this.http.post<TreatmentPlan>(`${this.api}/patients/${patientId}/treatment-plans`, payload);
  }

  addItem(planId: string, payload: TreatmentPlanItemCreate): Observable<TreatmentPlan> {
    return this.http.post<TreatmentPlan>(`${this.api}/treatment-plans/${planId}/items`, payload);
  }

  updateItemStatus(
    planId: string,
    itemId: string,
    status: TreatmentPlanItemStatus,
  ): Observable<TreatmentPlan> {
    return this.http.put<TreatmentPlan>(`${this.api}/treatment-plans/${planId}/items/${itemId}`, { status });
  }

  listBudgets(patientId: string): Observable<Budget[]> {
    return this.http.get<Budget[]>(`${this.api}/patients/${patientId}/budgets`);
  }

  createBudget(patientId: string, payload: BudgetCreate): Observable<Budget> {
    return this.http.post<Budget>(`${this.api}/patients/${patientId}/budgets`, payload);
  }

  updateBudgetStatus(budgetId: string, status: BudgetStatus): Observable<Budget> {
    return this.http.put<Budget>(`${this.api}/budgets/${budgetId}/status`, { status });
  }
}
