import { Component, OnInit, Output, EventEmitter, OnDestroy } from '@angular/core';
import { UntypedFormGroup, UntypedFormControl, UntypedFormBuilder, Validators } from '@angular/forms';
import { Observable, Subscription } from 'rxjs';
import { Credentials } from 'src/app/model/credentials';
import { AutheticationService } from 'src/app/service/pybackend/authentication/authetication.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit, OnDestroy {

  credentialForm: UntypedFormGroup;
  username = '';
  password = '';
  errors: any[] = []
  @Output() userLogin = new EventEmitter<boolean>();
  @Output() newUser = new EventEmitter<boolean>();
  loginSubscription: Subscription | null = null;

  constructor(private formBuilder: UntypedFormBuilder, private authentication: AutheticationService) { 

    this.credentialForm = this.formBuilder.group({
      username: new UntypedFormControl(this.username, [Validators.required, /*Validators.email*/]) ,
      password: new UntypedFormControl(this.password, [Validators.required, Validators.minLength(4)]),
    });
  }

  ngOnInit(): void {
  }
  get myForm() {return this.credentialForm.controls}

  onSubmit(): void {
    if (this.credentialForm.valid)
    {
      let credentials = new Credentials(this.myForm['username'].value, this.myForm['password'].value)
      this.loginSubscription = this.authentication.login(credentials).subscribe({
        error: (error) => {
          if(error.status == 0){
            this.errors = ['Algo salió mal, inténtalo de nuevo más tarde']
          }
          else{
            this.errors = error.error
          }
          this.userLogin.emit(false)
        },
        next:(v) => this.userLogin.emit(true)
      })
    }
  }
  createAccout(){
    this.newUser.emit(true);
  }

  ngOnDestroy(): void {
    this.loginSubscription?.unsubscribe()
  }


}
