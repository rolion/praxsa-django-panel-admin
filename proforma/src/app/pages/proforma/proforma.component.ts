import {Component, OnDestroy, OnInit} from '@angular/core';
import {ActivatedRoute, Router} from '@angular/router';
import { Invoice} from "../../model/proformaCollection";
import {PdfBuilderService} from "../../service/pdf/pdf-builder.service";
import {Subscription} from "rxjs";

import { faFilePdf } from '@fortawesome/free-solid-svg-icons';
import { faWhatsapp } from '@fortawesome/free-brands-svg-icons';
import { ProformaService } from 'src/app/service/pybackend/proforma/proforma.service';
import { AutheticationService } from 'src/app/service/pybackend/authentication/authetication.service';
import { User } from 'src/app/model/user';

@Component({
  selector: 'app-proforma',
  templateUrl: './proforma.component.html',
  styleUrls: ['./proforma.component.css']
})
export class ProformaComponent implements OnInit, OnDestroy {
  faFilePdf = faFilePdf;
  faWhatsapp = faWhatsapp;
  proforma : Invoice | null = null;
  currentUser: User | null = null;
  httpSubscription: Subscription| null = null;
  userStateSubscription: Subscription | null = null;
  pdfLogoImg: any;
  constructor( private route: ActivatedRoute,
               private navigate: Router,
               private pdf: PdfBuilderService,
               private proformaService: ProformaService,
               private auth: AutheticationService
               ) { }

  ngOnDestroy(): void {
        this.userStateSubscription?.unsubscribe();
        this.httpSubscription?.unsubscribe();
    }

  ngOnInit(): void {
    this.currentUser = this.auth.getUser();
    if(!this.currentUser){
      this.navigate.navigateByUrl('/login')
    }
    let id = this.route.snapshot.paramMap.get('id');
    if(this.currentUser && id){
      this.getProforma(id);
    }
  }
  
  getProforma(id: any): void{
    if (id !== null){
      this.proformaService.getProforma(parseInt(id)).subscribe({
        next: (res) => {
          this.proforma = res;
        },
        error: (error) => { console.log('error, ', error)}
      });
    }
  }
  downloadProforma(): void {
    if(this.proforma!=null){
      this.pdf.resetPdf();
      const marca = this.proforma.car_brand_name;
      const modelo = this.proforma.car_model_name;
      if (marca && modelo){
        const pdfHead = ['Item', 'Lamina', 'Precio Total'];
        const pdfBody: any[] = [];
        const pdfFoot = ['', 'Total', `${this.proforma.total_price.toFixed(2)} Bs`];
        this.proforma.carPartItems.forEach(object => {
          if(object != null){
            pdfBody.push([object.car_part_name, object.window_film_name,`${object.sub_total.toFixed(2)} Bs` ])
          }
        });
        this.pdf.setLogoBase64(this.pdfLogoImg);
        this.pdf.setSubTotal(this.proforma.total_price);
        this.pdf.setHeader(pdfHead);
        this.pdf.setBody(pdfBody);
        this.pdf.setFoot(pdfFoot);
        this.pdf.setCompanyName('Praxsa');
        this.pdf.setCompanyAddress('4to anillo, radial 26, calle #3', 'Santa Cruz de la Sierra', '3 352139');
        this.pdf.setTitle('Proforma');
        this.pdf.setProformaDetail(
          // '',
          this.proforma.proforma_created_on == null? '': this.proforma.proforma_created_on,
          this.proforma.name == null? '': this.proforma.name,
          this.proforma.ci_nit== null ? '': this.proforma.ci_nit,
          this.proforma.email== null ? '': this.proforma.email,
          this.proforma.phone_number== null ? '': this.proforma.phone_number,
          marca== null ? '': marca,
          modelo== null ? '': modelo,this.proforma.car_plate ==null? '': this.proforma.car_plate );
        this.pdf.build();
        this.pdf.download();
      }
    }
  }
}
