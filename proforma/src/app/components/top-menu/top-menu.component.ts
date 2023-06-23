import { Component, OnDestroy, OnInit } from '@angular/core';
import { AutheticationService } from 'src/app/service/pybackend/authentication/authetication.service';
import { User } from 'src/app/model/user';
import { Router } from '@angular/router';

@Component({
  selector: 'app-top-menu',
  templateUrl: './top-menu.component.html',
  styleUrls: ['./top-menu.component.css']
})
export class TopMenuComponent implements OnInit, OnDestroy {

  public isCollapsed = true;
  displayName: string;
  img: string;
  currentUser: User | null;
  userSubscription: any;
  constructor(public auth: AutheticationService, private router: Router) {
    this.displayName = '';
    this.img = '';
    this.currentUser = null;
    this.userSubscription=this.auth.isUserLoged.subscribe({
      next: (user) => {
        this.currentUser = user
      },
      error: (error) => console.log(error)
    })
  }
   
  ngOnDestroy(): void {
    this.userSubscription.unsubscribe()
  }

  ngOnInit(): void {
    
  }
  logout(): void{
    if (this.currentUser !== null){
      this.auth.logout();
      this.router.navigateByUrl('/')
    }
  }
}
