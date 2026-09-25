import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AppPermission } from '../users.model';
import { UsersService } from '../users.service';

@Component({
  selector: 'app-roles-list',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './roles-list.component.html',
})
export class RolesListComponent implements OnInit {
  private usersService = inject(UsersService);

  permissionsByApp: Record<string, AppPermission[]> = {};

  ngOnInit(): void {
    this.usersService.listPermissions().subscribe((permissions) => {
      this.permissionsByApp = permissions.reduce((acc, permission) => {
        (acc[permission.app_label] ||= []).push(permission);
        return acc;
      }, {} as Record<string, AppPermission[]>);
    });
  }

  get appLabels(): string[] {
    return Object.keys(this.permissionsByApp).sort();
  }
}
