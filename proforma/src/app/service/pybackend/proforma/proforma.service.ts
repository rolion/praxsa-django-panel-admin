import { HttpHeaders, HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {map} from 'rxjs/operators';
import { environment } from '../../../../environments/environment';
import { CarPartFilmItem, Invoice, ProformaCollection } from 'src/app/model/proformaCollection';
import { param } from 'jquery';

@Injectable({
  providedIn: 'root'
})
export class ProformaService {
  httpOptions = {
    headers: new HttpHeaders({
      'Content-Type':  'application/json',
    })
  };

  constructor(private http: HttpClient) {}

  saveProforma(proforma: Invoice): Observable<{id: number}>{
    // let invoice: Invoice
    return this.http
    .post<Invoice>(`${environment.APP_BASE_REF}/product/invoice`, proforma, this.httpOptions)
    .pipe(
      map(  (res:any)=>{
        return {id: res.id};
    })
    )
  }

  getProforma(invoice_id: number){
    return this.http
    .get<Invoice>(`${environment.APP_BASE_REF}/product/invoice/${invoice_id}`,this.httpOptions)
    .pipe(
      map(  (res:any)=>{
        return res;
    })
    )
  }

  getUserProforma(dataTablesParameters: any){
    let url = `${environment.APP_BASE_REF}/product/invoice/all`;
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
