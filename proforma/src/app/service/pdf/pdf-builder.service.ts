import { Injectable } from '@angular/core';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import {HttpClient} from "@angular/common/http";

@Injectable({
  providedIn: 'root'
})
export class PdfBuilderService {
  doc: jsPDF;
  head = [];
  body = [];
  foot = [];
  subTotal: number= 0.0;
  xPosition : number;
  increment: number = 5;
  logo: any;
  mainColor: string;
  blackColor: string;
  logoBase64: any;
  constructor(private http: HttpClient) {
    this.doc = new jsPDF();
    this.xPosition = 14;
    this.mainColor = '#2a3181';
    this.blackColor = '#000000';
  }
  resetPdf(){
    this.doc= new jsPDF();
  }
  setLogoBase64(logo : any){
    let  img = new Image();
    img.src = '/assets/img/praxsa-image.jpeg'
    this.logoBase64= img;
  }
  setSubTotal(subTotal: number){
    this.subTotal = subTotal;
  }
  setHeader(head: any): void{
    this.head = head;
  }
  setBody(body: any): void{
    this.body = body;
  }
  setFoot(footer: any): void{
    this.foot = footer;
  }


  setCompanyName(companyName: string){
    this.doc.setFontSize(15);
    this.doc.setTextColor(this.mainColor);
    this.doc.text(companyName, this.xPosition, 22);
    this.doc.addImage(this.logoBase64,'JPEG', 160,18,30,20);

  }
  setCompanyAddress(address: string, city: string, phoneNumber: string){
    this.doc.setFontSize(9);
    this.doc.setTextColor(this.blackColor);
    this.doc.text(address, this.xPosition, 26);
    this.doc.text(city, this.xPosition, 30);
    this.doc.text(phoneNumber, this.xPosition, 34);
  }
  setTitle(title: any): void{
    this.doc.setFontSize(22);
    this.doc.setTextColor(this.mainColor);
    this.doc.setFont('', 'bold');
    this.doc.text(title, 14, 42);

  }

  setProformaDetail(fecha:string, nombre:string, ci:string, email:string, celular:string, marca:string, modelo:string, placa:string){
      let columnSeparation = 75;
      let fontSizeTitles = 12;
      let fontSizeNormal = 11;
      let fontSizeName = 14;
      this.doc.setTextColor(this.blackColor);
      this.doc.setFont('', 'bold').setFontSize(fontSizeTitles).text('Fecha', this.xPosition,  50);
      this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(fecha, this.xPosition, 55);
      this.doc.setFont('', 'bold').setFontSize(fontSizeTitles).text('Cod. Proforma', this.xPosition  +columnSeparation,  50);
      this.doc.setFont('','bold').setFontSize(fontSizeNormal).text('Datos personales para la garantía', this.xPosition, 60);
      this.doc.setFont('','bold').setFontSize(fontSizeName).text(nombre.toUpperCase(), this.xPosition, 67);
      this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(`C.I.: ${ci}`, this.xPosition, 75);
      this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(`Nro. Celular: ${celular}`, this.xPosition, 80);
      this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(`Correo: ${email}`, this.xPosition, 85);
      this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(`Nro. Garantia:`, this.xPosition +columnSeparation, 75)
      this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(`Marca: ${marca}`, this.xPosition +columnSeparation, 80);
      this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(`Modelo: ${modelo}`, this.xPosition +columnSeparation, 85);
    this.doc.setFont('', 'normal').setFontSize(fontSizeNormal).text(`Placa: ${placa}`, this.xPosition +columnSeparation, 90);
  }
  setCustomText(customText: any): void{
    this.doc.setFontSize(11);
    const pageSize = this.doc.internal.pageSize;
    const pageWidth = pageSize.width ? pageSize.width : pageSize.getWidth();
    const text = this.doc.splitTextToSize( customText, pageWidth - 35, {});
    this.doc.text(text, 14, 50);
  }
  build(): void{

    autoTable(this.doc, { head: [this.head], body: this.body , startY: 95} );
    // @ts-ignore
    let finalY = (this.doc as any).lastAutoTable.finalY;
    this.doc.setFontSize(12).setFont('', 'bold').text(`SubTotal:`, 100, finalY+5);
    this.doc.setFontSize(12).setFont('', 'normal').text(`${this.subTotal.toFixed(2)}Bs`, 140, finalY+5);
    this.doc.setFontSize(12).setFont('', 'bold').text(`Descuento:`, 100, finalY+10);
    this.doc.setFontSize(12).setFont('', 'normal').text(`0Bs`, 150, finalY+10);
    this.doc.setFontSize(14).setFont('', 'normal').text(`${this.subTotal.toFixed(2)}Bs`, 140, finalY+15);
    this.doc.setFontSize(11).setFont('', 'bold').text("El precio final se contempla el I.V.A. y la instalación de la lamina", 14, finalY+20);
  }
  download(): void{
    this.doc.save('proforma.pdf');
  }
}
