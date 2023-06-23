import { AfterViewInit, Component, OnInit, Renderer2 } from '@angular/core';
import { Router } from '@angular/router';
import { ProformaService } from 'src/app/service/pybackend/proforma/proforma.service';
// import language from 'datatables.net-plugins/i18n/es-ES.json';

@Component({
  selector: 'app-invoice-table',
  templateUrl: './list-proforma.component.html',
  styleUrls: ['./list-proforma.component.css']
})
export class ListProformaComponent implements OnInit {
  dtOptions: DataTables.Settings = {};
  // language: DataTables.LanguageSettings ={ "search": "Buscar:",}
  tableData: any [] = []
  // dtTrigger: Subject<any> = new Subject<any>();

  constructor(private proformaService: ProformaService, private renderer: Renderer2, private router: Router) { }

  ngOnInit(): void {
    this.dtOptions = {
      language : {
        info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
        "processing": "Procesando...",
        "lengthMenu": "Mostrar _MENU_ registros",
        "zeroRecords": "No se encontraron resultados",
        "emptyTable": "Ningún dato disponible en esta tabla",
        "infoEmpty": "Mostrando registros del 0 al 0 de un total de 0 registros",
        "infoFiltered": "(filtrado de un total de _MAX_ registros)",
        "search": "Buscar:",
        "loadingRecords": "Cargando...",
        "paginate": {
            "first": "Primero",
            "last": "Último",
            "next": "Siguiente",
            "previous": "Anterior"
        },
        "aria": {
            "sortAscending": ": Activar para ordenar la columna de manera ascendente",
            "sortDescending": ": Activar para ordenar la columna de manera descendente"
        },
      },
      ajax: (dataTablesParameters: any, callback) => {
        this.proformaService.getUserProforma(dataTablesParameters).subscribe(data =>{
          callback(
             {
              recordsTotal: data.recordsTotal,
              recordsFiltered: data.recordsFiltered,
              data: data.data
             }
          )
        })
      },
      columns: [{
        title: 'Id',
        data: 'id'
      }, {
        title: 'Nombre',
        data: 'name'
      }, {
        title: 'Email',
        data: 'email'
      },{
        title: 'Precio',
        data: 'total_price'
      },{
        title: 'Estado',
        data: 'status'
      }],
      columnDefs: [
        {
            targets: 0,
            title: 'Id',
            orderable: false,
            render: function (data, type, full, meta) {
              return `<a href="/#/proforma/${data}" title='Editar'>${data}</a>`;
              // return `<a [routerLink]="['/proforma/${data}']" title='Editar'>${data}</a>`;
            },
        },
      ],
    };
  }
}
