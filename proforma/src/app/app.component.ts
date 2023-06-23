import { Component, isDevMode } from '@angular/core';
import { Modelo } from './model/modelo';
import { DataService } from './service/data.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'calculadora';
  modelosArray: Modelo[] = [];
  constructor(private data: DataService){

  }

  ngOnInit(): void {
    if (isDevMode()) {
      console.log('Development!');
    } else {
      console.log('Production!');
    }
    // this.data.getModelo().subscribe(data => this.modelosArray = data);
    // this.data.getCalculatorInfo().subscribe(data =>{
    //   this.modelosArray = data.modelos
    //   console.log('data', data)
    // })
  }
}
