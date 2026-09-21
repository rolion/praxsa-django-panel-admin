import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AutheticationService } from '../service/pybackend/authentication/authetication.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate {
  constructor(private auth: AutheticationService, private router: Router) {}

  canActivate(): boolean {
    if (this.auth.getUser()) {
      return true;
    }
    this.router.navigate(['/login']);
    return false;
  }
}
