export class Person {
  name: string | null;
  ci: string | null;
  email: string | null;
  phonenumber: string | null;
  placa:string | null;
  constructor(name: string, ci: string, email: string, phonenumber: string, placa: string){
    this.name = name;
    this.ci = ci;
    this.email = email;
    this.phonenumber = phonenumber;
    this.placa= placa;
  }
}
