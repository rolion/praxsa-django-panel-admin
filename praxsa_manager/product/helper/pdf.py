import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import inch, mm, cm, pica
from django.conf import settings
from reportlab.lib.utils import Image as PilImage
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from ..models import Detalle_Nota_Trabajo, Nota_trabajo, Proforma_Header, Proforma_Detail


class PDFService:

    def __init__(self, buffer) -> None:
        
        self.x_position = 14
        self.main_color = (42/255,49/255,129/255)
        self.increment = 5
        self.company_name = 'Praxsa'
        self.canvas = canvas.Canvas(buffer, pagesize=letter)
        
        self.canvas.translate(27, 792)
        self.border = 14
        self.top_border = -42

    def set_company_name(self):
        img = os.path.join(settings.BASE_DIR,'product/static/img/praxsa-logo.jpeg')
        self.canvas.drawImage(img, x=self.border, y=self.top_border-38, width=50, height=50)
        self.canvas.setFont(psfontname='Helvetica', size=15)
        self.canvas.setFillColor(aColor=self.main_color)
        self.canvas.drawString(x=self.border + 50, y=self.top_border, text= self.company_name.upper())

    def set_company_addres(self, address, city, phoneNumber):
        self.canvas.setFont( psfontname='Helvetica',size=9)
        self.canvas.setFillColor(aColor=black)
        self.canvas.drawString(text=address, x=self.border + 50, y= self.top_border -10)
        self.canvas.drawString(text=city, x=self.border + 50, y=self.top_border -20)
        self.canvas.drawString(text=phoneNumber, x=self.border + 50, y=self.top_border -30, )
    
    def set_title(self, title, proforma_id):
        self.canvas.setFont(psfontname='Helvetica-Bold', size=22)
        self.canvas.setFillColor(aColor=self.main_color)
        center = (letter[0]/2)-20
        self.canvas.drawCentredString(text=title, x=center, y=self.top_border - 60, )
        self.canvas.setFont(psfontname='Helvetica', size=12)
        self.canvas.drawCentredString(text=f'Nro. {proforma_id}', x=center, y=self.top_border - 75, )

    def set_proforma_header(self, fecha, nombre, ci, email, celular, marca, modelo, placa, codigo_proforma, sucursal ,codigo_garantia='Pendiente'):
      columnSeparation = 250
      fontSizeTitles = 12
      fontSizeNormal = 11
      fontSizeName = 14
      initialY=-130
      base_increment=-15
      
      xRightStart =  520 + 14 
      self.canvas.setFillColor(aColor=black)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeTitles)
      self.canvas.drawRightString(text=f'Fecha: {fecha}', x = xRightStart,  y=initialY)
      self.canvas.drawRightString(text=f'Sucursal: {sucursal.name}',
                             x = xRightStart ,
                             y=initialY - 10
                             )
      
      self.canvas.drawString(text='Datos personales para la garantía', 
                             x = self.x_position,
                             y=initialY + base_increment * 2)
      center = (self.canvas._pagesize[0] /2) - self.border
      self.canvas.drawString(text='Datos vehículo', 
                             x = center,
                             y=initialY + base_increment * 2)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeName)
      self.canvas.drawString(text=nombre, x = self.x_position, y=initialY + base_increment * 3)

      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'C.I.: {ci}', 
                             x = self.x_position, 
                             y=initialY + base_increment * 4)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Nro. Celular: {celular}',
                             x = self.x_position, 
                             y=initialY + base_increment * 5)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Correo: {email}', 
                             x = self.x_position, 
                             y=initialY + base_increment * 6)

      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
    
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Nro. Garantia: {codigo_garantia}', 
                             x = center, 
                             y=initialY + base_increment * 4)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Marca: {marca}', 
                             x = center, 
                             y=initialY + base_increment * 5)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Modelo: {modelo}', 
                             x = center, 
                             y=initialY + base_increment * 6)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Placa: {placa}', 
                             x = center, 
                             y=initialY + base_increment * 7)

    def proforma_body(self, body: [Proforma_Detail]):
      fontSizeNormal = 11
      initialY=-130
      base_increment=-15
      self.canvas.setFillColor(aColor=self.main_color)
      self.canvas.rect(x = self.x_position, y=initialY + base_increment * 9, width=520, height=20, stroke=0, fill=1) 
      self.canvas.setFillColor(aColor=white)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Item', 
                             x = self.x_position +10, 
                             y=initialY + (base_increment +0.7) * 9)
      self.canvas.drawString(text='Lamnia', 
                             x = self.x_position +200, 
                             y=initialY + (base_increment +0.7) * 9)
      self.canvas.drawString(text='Precio Total', 
                             x = self.x_position +400, 
                             y=initialY + (base_increment +0.7) * 9)
      
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.setFillColor(aColor=black)
      base_increment=-15
      row_increment =10
      subtotal = 0
      descuento = body[0].proforma_header.discount
      for item in body:
        self.canvas.drawString(text= item.car_part.name, 
                             x = self.x_position +10, 
                             y=initialY + (base_increment) * row_increment)
        self.canvas.drawString(text=item.window_film.name, 
                                x = self.x_position +200, 
                                y=initialY + (base_increment) * row_increment)
        self.canvas.drawString(text=f'{str(item.sub_total)} Bs', 
                                x = self.x_position +400, 
                                y=initialY + (base_increment) * row_increment)
        subtotal += item.sub_total
        row_increment+=1
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Subtotal', 
                                x = self.x_position +200, 
                                y=initialY + (base_increment) * (row_increment + 1))
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawRightString(text=f'{str(subtotal)} Bs', 
                                x = self.x_position +450, 
                                y=initialY + (base_increment) * (row_increment + 1))
      
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Descuento', 
                                x = self.x_position +200, 
                                y=initialY + (base_increment) * (row_increment + 2))
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawRightString(text=f'{str(descuento)} Bs', 
                                x = self.x_position +450, 
                                y=initialY + (base_increment) * (row_increment + 2))
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Total', 
                                x = self.x_position +200, 
                                y=initialY + (base_increment) * (row_increment + 3))
      total = subtotal - descuento
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawRightString(text=f'{str(total)} Bs', 
                                x = self.x_position +450, 
                                y=initialY + (base_increment) * (row_increment + 3))
      
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text="El precio final se contempla el I.V.A. y la instalación de la lamina", 
                                x = self.x_position, 
                                y=initialY + (base_increment) * (row_increment + 5))
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text="con la firma el cliente acepta el precio y la lamina seleccionada", 
                                x = self.x_position, 
                                y=initialY + (base_increment) * (row_increment + 6))
      X2 =  520 + 14 
      X1 = X2 - 150
      y=initialY + (base_increment) * (row_increment + 7)
      self.canvas.line(X1, y, X2, y)
      center = X1 + (X2-X1)/2
      y=initialY + (base_increment) * (row_increment + 8)
      self.canvas.drawCentredString(text='Cliente', x=center, y=y )
      
    def nota_trabajo_body(self, body: [Detalle_Nota_Trabajo]):
        fontSizeNormal = 11
        initialY=-130
        base_increment=-15
        self.canvas.setFillColor(aColor=self.main_color)
        self.canvas.rect(x = self.x_position, y=initialY + base_increment * 9, width=520, height=20, stroke=0, fill=1) 
        self.canvas.setFillColor(aColor=white)
        self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
        self.canvas.drawString(text='Lamina', 
                                x = self.x_position +10, 
                                y=initialY + (base_increment +0.7) * 9)
        self.canvas.drawString(text='Ancho', 
                                x = self.x_position +150, 
                                y=initialY + (base_increment +0.7) * 9)
        self.canvas.drawString(text='Largo', 
                                x = self.x_position +300, 
                                y=initialY + (base_increment +0.7) * 9)
        
        # self.canvas.drawString(text='Cantidad', 
        #                         x = self.x_position +400, 
        #                         y=initialY + (base_increment +0.7) * 9)
        row_increment =10
        self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
        self.canvas.setFillColor(aColor=black)
        for item in body:
            # print('lamina', item.window_film.name)
            self.canvas.drawString(text= item.window_film.name, 
                                x = self.x_position +10, 
                                y=initialY + (base_increment) * row_increment)
            # print('width ', item.width)
            self.canvas.drawString(text=str(item.width), 
                                    x = self.x_position +150, 
                                    y=initialY + (base_increment) * row_increment)
            # print('length ', item.length)
            self.canvas.drawString(text=str(item.length), 
                                    x = self.x_position +300, 
                                    y=initialY + (base_increment) * row_increment)
            # print('quantity ', item.quantity)
            # self.canvas.drawString(text=str(item.quantity), 
            #                         x = self.x_position +400, 
            #                         y=initialY + (base_increment) * row_increment)
            row_increment+=1
        
    def create_proforma(self, header: Proforma_Header, detail: [Proforma_Detail], title ='Proforma',codigo_garantia = 'Pendiente'):
        self.set_company_name()
        self.set_company_addres(address='4to anillo, radial 26, calle #3', city='santa cruz', phoneNumber='3 352139')
        self.set_title(title= title, proforma_id=header.id)
        self.set_proforma_header(fecha=header.proforma_created_on.strftime("%d/%m/%Y"), 
                                 nombre= header.name, 
                                 ci=header.ci_nit, 
                                 email= header.email, 
                                 marca= header.car_model_id.car_brand_id.name, 
                                 modelo= header.car_model_id.name, 
                                 placa= header.car_plate, 
                                 celular= header.phone_number,
                                 codigo_garantia= codigo_garantia,
                                 codigo_proforma = header.id,
                                 sucursal= header.sucursal)
        self.proforma_body(body=detail)
        self.canvas.showPage()
        self.canvas.save()
        
    def create_nota_trabajo(self, nota_trabajo: Nota_trabajo, detail: [Detalle_Nota_Trabajo]):
        header = nota_trabajo.proforma
        self.set_company_name()
        self.set_company_addres(address='4to anillo, radial 26, calle #3', city='santa cruz', phoneNumber='3 352139')
        self.set_title(title='Nota trabajo', proforma_id=nota_trabajo.id)
        self.set_proforma_header(fecha=header.proforma_created_on.strftime("%d-%m-%Y %H:%M:%S"), 
                                 nombre= header.name, 
                                 ci=header.ci_nit, 
                                 email= header.email, 
                                 marca= header.car_model_id.car_brand_id.name, 
                                 modelo= header.car_model_id.name, 
                                 placa= header.car_plate, 
                                 celular= header.phone_number,
                                 codigo_proforma= header.id,
                                 codigo_garantia=nota_trabajo.codigo_garantia,
                                 sucursal= header.sucursal)
        self.nota_trabajo_body(body=detail)
        self.canvas.showPage()
        self.canvas.save()