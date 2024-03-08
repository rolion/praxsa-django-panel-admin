import { Injectable } from '@angular/core';
import jsPDF from 'jspdf';
import TextOptionsLight from 'jspdf'
import autoTable, { Styles } from 'jspdf-autotable';
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
  pageWidth:number;
  border: number
  constructor(private http: HttpClient) {
    this.doc = new jsPDF();
    this.xPosition = 14;
    this.mainColor = '#2a3181';
    this.blackColor = '#000000';
    this.pageWidth = this.doc.internal.pageSize.width ;
    this.border = 14

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
    this.doc.addImage(this.logoBase64,'JPEG', this.xPosition - 8,15,30,20);
    this.doc.setFontSize(15);
    this.doc.setTextColor(this.mainColor);
    this.doc.text(companyName.toUpperCase(), this.xPosition + 18, 22);
    // this.doc.addImage(this.logoBase64,'JPEG', 160,18,30,20);

  }
  setCompanyAddress(address: string, city: string, phoneNumber: string){
    this.doc.setFontSize(9);
    this.doc.setTextColor(this.blackColor);
    this.doc.text(address, this.xPosition + 18, 26);
    this.doc.text(city, this.xPosition + 18, 30);
    this.doc.text(phoneNumber, this.xPosition + 18, 34);
  }
  setTitle(title: any, id: number): void{
    this.doc.setFontSize(22);
    this.doc.setTextColor(this.mainColor);
    this.doc.setFont('Helvetica', 'bold');
    let center = this.pageWidth / 2
    this.doc.text(title, center, 42, { align: 'center' });
    this.doc.setFontSize(12);
    this.doc.setFont('Helvetica', 'normal');
    this.doc.text(`Nro. ${id}`, center, 47, { align: 'center' });
  }

  

  setProformaDetail(fecha:string, nombre:string, ci:string, email:string, celular:string, marca:string, modelo:string, placa:string, sucursal:string){
      let fontSizeTitles = 12;
      let fontSizeNormal = 11;
      let fontSizeName = 14;
      let center = this.pageWidth / 2
      this.doc.setTextColor(this.blackColor);
      let startAtRigth = this.pageWidth - this.border;
      this.doc.setFont('Helvetica', 'bold').setFontSize(fontSizeTitles).text(`Fecha: ${fecha}`, startAtRigth,  50, { align: 'right' });
      this.doc.setFont('Helvetica', 'bold').setFontSize(fontSizeTitles).text(`Sucursal: ${sucursal}`, startAtRigth,  55, { align: 'right' });

      this.doc.setFont('Helvetica','bold').setFontSize(fontSizeNormal).text('Datos personales para la garantía', this.border, 60);
      this.doc.setFont('Helvetica','bold').setFontSize(fontSizeName).text(nombre.toUpperCase(), this.border, 67);
      this.doc.setFont('Helvetica', 'normal').setFontSize(fontSizeNormal).text(`C.I.: ${ci}`, this.border, 75);
      this.doc.setFont('Helvetica', 'normal').setFontSize(fontSizeNormal).text(`Nro. Celular: ${celular}`, this.border, 80);
      this.doc.setFont('Helvetica', 'normal').setFontSize(fontSizeNormal).text(`Correo: ${email}`, this.border, 85);
      this.doc.setFont('Helvetica','bold').setFontSize(fontSizeNormal).text('Datos Vehículo', center, 60);
      this.doc.setFont('Helvetica', 'normal').setFontSize(fontSizeNormal).text(`Nro. Garantia:`, center, 75)
      this.doc.setFont('Helvetica', 'normal').setFontSize(fontSizeNormal).text(`Marca: ${marca}`, center, 80);
      this.doc.setFont('Helvetica', 'normal').setFontSize(fontSizeNormal).text(`Modelo: ${modelo}`, center, 85);
      this.doc.setFont('Helvetica', 'normal').setFontSize(fontSizeNormal).text(`Placa: ${placa}`, center, 90);
  }
  setCustomText(customText: any): void{
    this.doc.setFontSize(11);
    const pageSize = this.doc.internal.pageSize;
    const pageWidth = pageSize.width ? pageSize.width : pageSize.getWidth();
    const text = this.doc.splitTextToSize( customText, pageWidth - 35, {});
    this.doc.text(text, 14, 50);
  }
  build(): void{

    let headerStyle: Partial<Styles> = {
      font: 'helvetica',
      fontStyle: 'bold',
      fillColor: '#2a3181',
      textColor: '#FFFFFF'
    }
    autoTable(this.doc, {headStyles: headerStyle, head: [this.head], body: this.body , startY: 95} );
    // @ts-ignore
    let finalY = (this.doc as any).lastAutoTable.finalY;
    this.doc.setFontSize(12).setFont('Helvetica', 'bold').text(`SubTotal:`, 100, finalY+5);
    this.doc.setFontSize(12).setFont('Helvetica', 'normal').text(`${this.subTotal.toFixed(2)}Bs`, 140, finalY+5);
    // this.doc.setFontSize(12).setFont('Helvetica', 'bold').text(`Descuento:`, 100, finalY+10);
    // this.doc.setFontSize(12).setFont('Helvetica', 'normal').text(`0Bs`, 150, finalY+10);
    // this.doc.setFontSize(14).setFont('Helvetica', 'normal').text(`${this.subTotal.toFixed(2)}Bs`, 140, finalY+15);
    this.doc.setFontSize(11).setFont('Helvetica', 'bold').text("El precio final se contempla el I.V.A. y la instalación de la lamina", this.border, finalY+20);
    this.doc.setFontSize(11).setFont('Helvetica', 'normal').text("con la firma el cliente acepta el precio y la lamina seleccionada", this.border, finalY+25);
    let lineX1 = this.pageWidth - this.border - 50;
    let lineX2 = this.pageWidth - this.border;
    let lineY = finalY+ 35
    this.doc.line(lineX1, lineY, lineX2, lineY)
    this.doc.setFontSize(11).setFont('Helvetica', 'normal').text("Cliente", lineX1+25, finalY+40, {align: 'center'});
  }
  download(): void{
    this.doc.save('proforma.pdf');
  }
}
