export class User {
    email = '';
    password = '';
    name = '';
    lastname = '';
    phone_number = '';
    ci_nit = '';
    constructor(email: string, password: string, name: string, lastname: string, phone_number: string, ci_nit: string){
        this.email = email;
        this.password = password;
        this.name = name;
        this.lastname = lastname;
        this.phone_number = phone_number;
        this.ci_nit = ci_nit;
    }
  }