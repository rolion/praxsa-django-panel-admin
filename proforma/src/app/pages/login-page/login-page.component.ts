import { Component, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { User } from 'src/app/model/user';
import { AutheticationService } from 'src/app/service/pybackend/authentication/authetication.service';

@Component({
  selector: 'app-login-page',
  templateUrl: './login-page.component.html',
  styleUrls: ['./login-page.component.css']
})
export class LoginPageComponent implements OnInit, OnDestroy {

  currentUser: User | null;
  loginSubscription: any;
  constructor(private auth: AutheticationService, private router: Router) {
    this.currentUser = null;
    this.loginSubscription = this.auth.isUserLoged.subscribe({
      next: (user) => {
        if(user){
          this.router.navigateByUrl('/')
        }
      },
      error: (error) => console.log('error')//console.log('error',error)
    })
   }
  ngOnDestroy(): void {
    this.loginSubscription.unsubscribe()
  }

  ngOnInit(): void {
      this.currentUser = this.auth.getUser();
      if(this.currentUser){
        this.router.navigateByUrl('/')
      }
  }

  moveToCreateUser(createUser: boolean){
    if(createUser){
      this.router.navigateByUrl('/create-user')
    }
  }


}
