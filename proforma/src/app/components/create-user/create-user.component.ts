import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { User } from 'src/app/model/user';
import { AutheticationService } from 'src/app/service/pybackend/authentication/authetication.service';

@Component({
  selector: 'app-create-user',
  templateUrl: './create-user.component.html',
  styleUrls: ['./create-user.component.css']
})
export class CreateUserComponent implements OnInit {

  createUserForm: UntypedFormGroup;
  username = '';
  password = '';
  name = '';
  lastname = '';
  phoneNumber = '';
  ci_nit = '';
  errors = [];
  currentUser: User | null;
  @Output() userCreated = new EventEmitter<boolean>();
  constructor(
    private formBuilder: UntypedFormBuilder, 
    private authentication: AutheticationService,
    private router: Router) { 
    this.createUserForm = this.formBuilder.group({
      username: new UntypedFormControl(this.username, [Validators.required, Validators.email]) ,
      password: new UntypedFormControl(this.password, [Validators.required, Validators.minLength(4), Validators.maxLength(10)]),
      name: new UntypedFormControl(this.name, [Validators.required]),
      lastname: new UntypedFormControl(this.lastname, [Validators.required]),
      phoneNumber: new UntypedFormControl(this.phoneNumber, [Validators.required]),
      ci_nit: new UntypedFormControl(this.ci_nit),
    });
    this.currentUser = this.authentication.getUser();
  }

  get myForm() {return this.createUserForm.controls}

  ngOnInit(): void {
    if (this.currentUser){
        this.router.navigateByUrl('/')
    }
  }
  onSubmit(): void {
      if (this.createUserForm.valid)
      {
        let newUser = new User(this.myForm['username'].value, this.myForm['password'].value, this.myForm['name'].value, this.lastname= this.myForm['lastname'].value, this.myForm['phoneNumber'].value, this.ci_nit= this.myForm['ci_nit'].value)
        this.authentication.createUser(newUser).subscribe(
          {
            next: res=> { 
              this.userCreated.emit(true)
            }, 
            error: error =>{
                if (error.error){
                    this.errors = error.error
                }
              }
          }
        )
      }
  
      
  }

}
