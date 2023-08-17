import { HttpHeaders, HttpClient } from '@angular/common/http';
import { Injectable,  Inject, PLATFORM_ID, } from '@angular/core';
import { Observable } from 'rxjs';
import {map} from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import { CarPartFilmItem, Invoice, ProformaCollection } from 'src/app/model/proformaCollection';
import { param } from 'jquery';
import { isPlatformBrowser } from '@angular/common';

@Injectable({
  providedIn: 'root'
})
export class ProformaService {
  httpOptions = {
    headers: new HttpHeaders({
      'Content-Type':  'application/json',
    })
  };

  base_url: Object;

  constructor(private http: HttpClient, @Inject(PLATFORM_ID) plataformId: Object) {
    this.base_url = isPlatformBrowser(plataformId)? environment.BROWSER_APP_BASE_REF: environment.SERVER_APP_BASE_REF;
  }

  saveProforma(proforma: Invoice): Observable<{id: number}>{
    // let invoice: Invoice
    console.log('proforma to save ', proforma)
    return this.http
    .post<Invoice>(`${this.base_url}/product/invoice`, proforma, this.httpOptions)
    .pipe(
      map(  (res:any)=>{
        return {id: res.id};
    })
    )
  }

  getProforma(invoice_id: number){
    return this.http
    .get<Invoice>(`${this.base_url}/product/invoice/${invoice_id}`,this.httpOptions)
    .pipe(
      map(  (res:any)=>{
        return res;
    })
    )
  }

  getUserProforma(dataTablesParameters: any){
    let url = `${this.base_url}/product/invoice/all`;
    return this.http
    .get<{
      recordsTotal: number, 
      recordsFiltered: number, 
      data: any}>
    (url, {params: dataTablesParameters})
    .pipe(
      map(  (res:any)=>{
        return {recordsTotal: res.recordsTotal, recordsFiltered: res.recordsFiltered, data: res.data};
    })
    )
  }

}
