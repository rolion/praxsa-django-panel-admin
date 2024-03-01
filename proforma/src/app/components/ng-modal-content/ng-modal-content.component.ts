import {Component, OnInit, Input, Output, EventEmitter} from '@angular/core';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import {Invoice, ProformaCollection} from '../../model/proformaCollection';
import { faCopy } from '@fortawesome/free-solid-svg-icons';
import {Person} from "../../model/person";
import {Router} from "@angular/router";
import { AutheticationService } from 'src/app/service/pybackend/authentication/authetication.service';
import { User } from 'src/app/model/user';
import { ProformaService } from 'src/app/service/pybackend/proforma/proforma.service';

@Component({
  selector: 'app-ng-modal-content',
  templateUrl: './ng-modal-content.component.html',
  styleUrls: ['./ng-modal-content.component.css']
})
export class NgModalContentComponent implements OnInit {
  @Input() proforma: ProformaCollection | null;
  @Input() invoice: Invoice | null;
  faCopy = faCopy;
  STATUS_VALIDANDO_USUARIO = 'Validando Usuario';
  STATUS_GUARDANDO_PROFORMA = 'Guardando Proforma';
  STATUS_RESERVAR_FACEBOOK = 'Proforma Guardada';
  STATUS_OBTENER_DATOS_USUARIO = 'Datos del Cliente'
  STATUS_CREATE_ACCOUNT = 'Crear Cuenta';
  STATUS_ERROR = 'Error';
  STATUS_INICIAR_SESSION = 'Iniciar Session';
  ERROR_MESSAGE: string | null;
  ERROR_MESSAGE_LOGIN = 'Iniciar Session con:';
  ERROR_MESSAGE_PROFORMA = 'Debe llenar la Proforma';
  estado = this.STATUS_VALIDANDO_USUARIO;
  id: any;
  currentUser: User | null;
  displayName: string;
  email: string | null;
  photoURL: string;
  emailVerified: boolean;
  uid: any;
  person: Person;

  constructor(public activeModal: NgbActiveModal,
              private router: Router, 
              //private local: LocalStorageService,
              private auth: AutheticationService,
              private be: ProformaService) {
    //let localName = `${this.local.getData('name')} ${this.local.getData('lastname')}`
    this.displayName = '';
    this.email = '';//this.local.getData('email')?this.local.getData('email'):'';
    this.photoURL = '';
    this.emailVerified = false;
    this.proforma = null;
    this.invoice = null;
    this.ERROR_MESSAGE = null;
    this.currentUser = null;
    this.person = new Person('','','','', '');
  }

  ngOnInit(): void {
    this.currentUser = this.auth.getUser()
    if (this.currentUser)
    {
      this.estado = this.STATUS_OBTENER_DATOS_USUARIO;
      this.person.name = `${this.currentUser.name} ${this.currentUser.lastname}`;
        this.person.email = this.currentUser.email;
        this.person.phonenumber = this.currentUser.phone_number;
        this.person.placa = '';
    }else{
      this.estado = this.STATUS_INICIAR_SESSION;
    }

  }

  onLogin(success: boolean){
    if(success){
      this.estado = this.STATUS_OBTENER_DATOS_USUARIO
      this.currentUser = this.auth.getUser()
      if (this.currentUser){
        this.person.name = `${this.currentUser.name} ${this.currentUser.lastname}`;
        this.person.email = this.currentUser.email;
        this.person.phonenumber = this.currentUser.phone_number;
        this.person.placa = '';
      }
    }
  }

  onMoveToCreateAccount(shouldMoveToCreateAccount: boolean){
      if(shouldMoveToCreateAccount){
        this.estado = this.STATUS_CREATE_ACCOUNT
      }
  }
  onUserCreated(isUserCreated: boolean){
    if(isUserCreated){
      this.estado = this.STATUS_INICIAR_SESSION
    }
  }

  generateProforma(){
    if(this.invoice){
      this.invoice.name = this.person.name || '';
      this.invoice.email = this.person.email || '';
      this.invoice.ci_nit = this.person.ci || '';
      this.invoice.phone_number = this.person.phonenumber;
      this.invoice.car_plate = this.person.placa || '';
    }
    this.estado = this.STATUS_GUARDANDO_PROFORMA;
    this.saveProforma();
  }

  async saveProforma(){
    try {
      if (this.currentUser == null){
        // todo debe iniciar seccion
        this.estado = this.STATUS_INICIAR_SESSION;
        return;
      }
      console.log('invoice ', this.invoice)
      if (this.invoice == null || this.invoice.carPartItems.length === 0){
        this.estado = this.STATUS_ERROR;
        this.ERROR_MESSAGE = this.ERROR_MESSAGE_PROFORMA;
        return;
      }
      this.estado = this.STATUS_GUARDANDO_PROFORMA;
      let invoiceClone = {...this.invoice};
      invoiceClone.carPartItems = this.invoice.carPartItems.filter(item => item.window_film != 0)
      if(invoiceClone){
        this.be.saveProforma(invoiceClone).subscribe({
          next: (res) =>{
            this.activeModal.close();
            this.router.navigate([`/proforma/${res.id}` ])
          },
          error: (error) => console.log('errors', error)
  
        })
      }
    }catch (e) {
      console.log(e);
    }
  }
  // logout(): void{
  // }

}
