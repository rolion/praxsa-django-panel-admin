import { Component, PLATFORM_ID, TransferState, makeStateKey, Inject, } from '@angular/core';
import { formatDate, isPlatformServer } from "@angular/common";
import { ActivatedRoute } from '@angular/router';
import { WindowsFilmService } from 'src/app/service/pybackend/film/windows-film.service';
import { WindowsFilm } from 'src/app/model/windowsFilm';
import { DomSanitizer } from '@angular/platform-browser';

@Component({
  selector: 'app-windows-film',
  templateUrl: './windows-film.component.html',
  styleUrls: ['./windows-film.component.css']
})
export class WindowsFilmComponent {

  plataformId: Object;
  windowsFilmDao: WindowsFilm;
  innerHtml: any;

  constructor(
      private route: ActivatedRoute, 
      private windowsFilmService: WindowsFilmService,
      private transferState: TransferState,
      @Inject(PLATFORM_ID) plataformId: Object,
      private sanitizer: DomSanitizer
    ) {
      this.plataformId = plataformId;
      this.windowsFilmDao = new WindowsFilm();
     }

  setData(data: WindowsFilm){
      this.windowsFilmDao = data;
  }

  getWindowsFilmInfo(id: string){
    this.windowsFilmService.getWindowsFilmInfo(+id).subscribe(
      {
        next: (res) =>{
          this.windowsFilmDao = res.layer;
          this.innerHtml = null;
          if(this.windowsFilmDao.content){
            this.innerHtml = this.sanitizer.bypassSecurityTrustHtml(this.windowsFilmDao.content);;
          } 
          
          console.log(res.layer)
        },
        error: (error) => {console.log('error getting windwsfilm', error)}
      }
    )
  }

  ngOnInit(): void {
    let id = this.route.snapshot.paramMap.get('id') || "";
    this.getWindowsFilmInfo(id)
  }

}
