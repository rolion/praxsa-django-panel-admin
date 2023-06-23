import {Component, NgModule, OnDestroy, OnInit} from '@angular/core';
import { faPen, faFilePdf } from '@fortawesome/free-solid-svg-icons';
import { faWhatsapp } from '@fortawesome/free-brands-svg-icons';
import {DataService} from '../../service/data.service';
import {Modelo} from '../../model/modelo';
import {CarPartItem} from '../../model/item';
// import {Lamina} from '../../model/lamina';
import {ReportItem} from '../../model/report';
import {Marca} from '../../model/marca';
import {PdfBuilderService} from '../../service/pdf/pdf-builder.service';
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import {NgModalContentComponent} from '../../components/ng-modal-content/ng-modal-content.component';
import {ProformaCollection, CarPartFilmItem, Invoice} from '../../model/proformaCollection';
import { formatDate } from "@angular/common";
import {Subscription} from "rxjs";
import {HttpClient} from "@angular/common/http";
import { Car_Part_Film_Price, Film } from 'src/app/model/lamina';
import { iDB } from './data'


@Component({
  selector: 'app-formulario',
  templateUrl: './formulario.component.html',
  styleUrls: ['./formulario.component.css']
})
export class FormularioComponent implements OnInit, OnDestroy {
  faPen = faPen;
  faFilePdf = faFilePdf;
  faWhatsapp = faWhatsapp;
  marcasArray: Marca[] = [];
  modelosByMarca: Modelo[] = [];
  laminaArray: Film[] = [];
  laminaPricesArray: Car_Part_Film_Price[] = [];
  all_car_model_parts: CarPartItem[] = [];
  allModels: Modelo[] = [];
  cantidad: number = 0;
  selectedModelId = -1 ;
  selectedItemId = -1 ;
  report: ReportItem[] = [];
  invoiceItem: CarPartFilmItem[] = [];
  total = 0;
  selectedMarcaId = -1;
  currentDate: string | null ;
  proforma: ProformaCollection | null = null;
  modalSubscription: Subscription | null = null;
  httpSubcription: Subscription | null = null;
  pdfLogoImg: any;
  dao: iDB;
  ngOnInit(): void {

    this.dataService.getCalculatorInfo().subscribe(data => {
      this.dao.films = data.lamina;
      this.dao.model = data.modelos;
      this.dao.marcas = data.marca;
      this.dao.prices = data.lamina_price;
      console.log('lamina prices', this.dao.prices);
      this.dao.carParts = data.model_parts;
      return true
    })
    this.httpSubcription=this.http.get('/assets/img/praxsa-form-logo.jpeg', { responseType: 'blob' })
      .subscribe(res => {
        const reader = new FileReader();
        reader.onloadend = () => {
          this.pdfLogoImg = reader.result;
        }
        reader.readAsDataURL(res);
      });
  }
  constructor(private dataService: DataService, private modalService: NgbModal, private http: HttpClient){
    this.currentDate = formatDate(new Date(), 'dd/MM/YYYY', 'en-US');
    this.dao = new iDB();

  }

  getModelos(): void{
    this.modelosByMarca = this.dao.getModelByMarca(this.selectedMarcaId)
  }

  getSelectedModelParts(): CarPartItem[]{
    return this.dao.getModelParts(this.selectedModelId);
  }
  
  loadTable(): void{
    const selectedModel = this.modelosByMarca.find(item => item.id === +this.selectedModelId);
    if(selectedModel){
      const modelParts = this.getSelectedModelParts();
      modelParts.forEach(carPart => {
        let {
          part_name: car_part_name, 
          width, 
          quantity, 
          part_id: car_part_id,
          installation_price,
        } = carPart;
        let length = 0;
        let price = 0;
        let window_film_id= 0;
        let window_film_name= "";
        let window_film_price = 0
        let proformaItem = new CarPartFilmItem(
          car_part_id,
          car_part_name,
          width ,
          length,
          price,
          quantity,
          window_film_id,
          // window_film_name,
          installation_price,
          window_film_price,
        )
        this.invoiceItem.push(proformaItem);
      });
    }
  }

  removeReportItem(reportIndex: number): void{
    if (reportIndex !== -1){
      this.invoiceItem.splice(reportIndex, 1);
      this.total = 0;
      this.invoiceItem.forEach(item => this.total += item.price);
    }
  }

  addLamina($event: any, indexReport: number): void {
    const laminaIndex = $event.target.options.selectedIndex;
    if ( laminaIndex > 0 ){
      const lamina = this.dao.films[laminaIndex - 1];
      let carPartFilmItem = this.invoiceItem[indexReport];
      let {
        quantity, width ,installation_price,
      } = carPartFilmItem
      let {
        filmPrice, totalPrice
      } = this.getLaminaItemPrice(lamina, width, quantity, installation_price);
      this.invoiceItem[indexReport].price = totalPrice;
      this.invoiceItem[indexReport].window_film_price = filmPrice;
      this.invoiceItem[indexReport].window_film_id = lamina.id
      this.calculateTotal();
    }else{
      this.invoiceItem[indexReport].price = 0;
      this.invoiceItem[indexReport].window_film_price = 0;
      this.invoiceItem[indexReport].window_film_id = 0
    }
    this.calculateTotal();
  }

  getLaminaItemPrice(lamina: Film, carPartWidth: number, filmQuantity: number, carPartInstallationPrice: number){
    let filmPrice = this.dao.getLamninaPriceByWidth(lamina.id, carPartWidth);
    let totalPrice = filmPrice.price === 0? 0 :(carPartInstallationPrice + filmPrice.price) * filmQuantity;
    return {'filmPrice': filmPrice.price, totalPrice}
  }

  calculateTotal(): void{
    this.total = this.invoiceItem.reduce((acc, current) =>acc+=current.price,0)
  }

  getInvoice(): Invoice{
    let marca = this.getMarca();
    let marcaName = marca? marca.nombre: '';
    let marcaId = marca? marca.id: 0;
    let modelo = this.getModelo();
    let modeloName = modelo? modelo.nombre: '';
    let modelId = modelo? modelo.id: 0;
    let invoice = new Invoice(
      this.invoiceItem,
      modelId,
      modeloName,
      marcaId,
      marcaName,
      this.total
    )
    return invoice;
  }

  getMarca(): Marca | undefined{
    return this.marcasArray.find(arrayItem => arrayItem.id === +this.selectedMarcaId);
  }
  getModelo(): Modelo | undefined{
    return this.modelosByMarca.find(arrayItem => arrayItem.id === +this.selectedModelId);
}
  openModal(): void{
    const modalRef = this.modalService.open(NgModalContentComponent);
    modalRef.componentInstance.invoice = this.getInvoice();
  }

  ngOnDestroy(): void {
    this.modalSubscription?.unsubscribe();
    this.httpSubcription?.unsubscribe();
  }
}
