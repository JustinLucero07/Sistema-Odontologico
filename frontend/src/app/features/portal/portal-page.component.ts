import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import { formatMoney } from '../../core/models/finance.models';
import { PortalView } from '../../core/models/communication.models';
import { CommunicationService } from '../../core/services/communication.service';
import { ToothMarkComponent } from '../../shared/brand/tooth-mark.component';

@Component({
  selector: 'app-portal-page',
  standalone: true,
  imports: [DatePipe, MatIconModule, ToothMarkComponent],
  templateUrl: './portal-page.component.html',
  styleUrl: './portal-page.component.scss',
})
export class PortalPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly comms = inject(CommunicationService);

  readonly view = signal<PortalView | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly money = formatMoney;

  async ngOnInit(): Promise<void> {
    const token = this.route.snapshot.paramMap.get('token');
    if (!token) {
      this.error.set('El enlace está incompleto.');
      this.loading.set(false);
      return;
    }
    try {
      this.view.set(await firstValueFrom(this.comms.getPortalView(token)));
    } catch (err) {
      // The server gives the same answer for unknown, expired and revoked, so
      // this page repeats it verbatim rather than guessing which it was.
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(
        typeof detail === 'string'
          ? detail
          : 'No se pudo abrir el enlace. Solicite uno nuevo a su clínica.',
      );
    } finally {
      this.loading.set(false);
    }
  }

  balanceTone(balance: string): 'owed' | 'credit' | 'settled' {
    const n = Number(balance);
    return n > 0 ? 'owed' : n < 0 ? 'credit' : 'settled';
  }
}
