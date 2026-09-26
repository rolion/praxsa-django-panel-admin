import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../service/auth.service';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard {
  private authService = inject(AuthService);
  private router = inject(Router);

  canActivate() {
    const currentUser = this.authService.currentUserValue;
    if (currentUser && currentUser.token) {
      return true;
    }
    this.router.navigate(['/authentication/signin']);
    return false;
  }
}
