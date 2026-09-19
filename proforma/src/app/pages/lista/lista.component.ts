import { Component, OnInit } from '@angular/core';
import { User } from 'src/app/model/user';
import { AutheticationService } from 'src/app/service/pybackend/authentication/authetication.service';

@Component({
  selector: 'app-lista',
  templateUrl: './lista.component.html',
  styleUrls: ['./lista.component.css']
})
export class ListaComponent implements OnInit {

  currentUser: User| null;

  constructor(private auth: AutheticationService) {
    this.currentUser = this.auth.getUser();
  }

  ngOnInit(): void {
  }

}
