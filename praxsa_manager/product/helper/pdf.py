from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from ..models import Proforma_Header, Proforma_Detail

class PDFService:

    def __init__(self, buffer) -> None:
        
        self.x_position = 14
        self.main_color = (42/255,49/255,129/255)
        self.increment = 5
        self.company_name = 'Praxsa'
        self.canvas = canvas.Canvas(buffer) 
        self.canvas.translate(27, 792)

    def set_company_name(self):
        self.canvas.setFont(psfontname='Helvetica', size=15)
        self.canvas.setFillColor(aColor=self.main_color)
        # print(letter)
        self.canvas.drawString(x=self.x_position, y=-63, text= self.company_name)

    def set_company_addres(self, address, city, phoneNumber):
        self.canvas.setFont( psfontname='Helvetica',size=9)
        self.canvas.setFillColor(aColor=black)
        self.canvas.drawString(text=address, x=self.x_position, y= -73)
        self.canvas.drawString(text=city, x=self.x_position, y=-83)
        self.canvas.drawString(text=phoneNumber, x=self.x_position, y=-93, )
    
    def set_title(self, title):
        self.canvas.setFont(psfontname='Helvetica-Bold', size=22)
        self.canvas.setFillColor(aColor=self.main_color)
        self.canvas.drawString(text=title, x=self.x_position, y=-115 )

    def set_proforma_header(self, fecha, nombre, ci, email, celular, marca, modelo, placa, codigo_proforma, codigo_garantia='Pendiente'):
      columnSeparation = 250
      fontSizeTitles = 12
      fontSizeNormal = 11
      fontSizeName = 14
      initialY=-130
      base_increment=-15
      self.canvas.setFillColor(aColor=black)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeTitles)
      self.canvas.drawString(text='Fecha', x = self.x_position,  y=initialY)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=fecha, x = self.x_position, y=initialY + base_increment)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeTitles)
      self.canvas.drawString(text=f'Cod. Proforma',
                             x = self.x_position + columnSeparation,
                             y=initialY
                             )
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=str(codigo_proforma), x = self.x_position + columnSeparation, y=initialY + base_increment)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Datos personales para la garantía', 
                             x = self.x_position,
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
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Nro. Garantia: {codigo_garantia}', 
                             x = self.x_position +columnSeparation, 
                             y=initialY + base_increment * 4)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Marca: {marca}', 
                             x = self.x_position +columnSeparation, 
                             y=initialY + base_increment * 5)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Modelo: {modelo}', 
                             x = self.x_position +columnSeparation, 
                             y=initialY + base_increment * 6)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Placa: {placa}', 
                             x = self.x_position +columnSeparation, 
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
      total = 0
      for item in body:
        self.canvas.drawString(text= item.car_part.name, 
                             x = self.x_position +10, 
                             y=initialY + (base_increment) * row_increment)
        self.canvas.drawString(text=item.window_film.name, 
                                x = self.x_position +200, 
                                y=initialY + (base_increment) * row_increment)
        self.canvas.drawString(text=str(item.sub_total), 
                                x = self.x_position +400, 
                                y=initialY + (base_increment) * row_increment)
        total += item.sub_total
        row_increment+=1
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Subtotal', 
                                x = self.x_position +200, 
                                y=initialY + (base_increment) * (row_increment + 1))
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=str(total), 
                                x = self.x_position +400, 
                                y=initialY + (base_increment) * (row_increment + 1))
      
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Descuento', 
                                x = self.x_position +200, 
                                y=initialY + (base_increment) * (row_increment + 2))
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text='0', 
                                x = self.x_position +400, 
                                y=initialY + (base_increment) * (row_increment + 2))
      
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text="El precio final se contempla el I.V.A. y la instalación de la lamina", 
                                x = self.x_position, 
                                y=initialY + (base_increment) * (row_increment + 3))
      
    def nota_trabajo_body(self, body: [Proforma_Detail]):
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
        
        self.canvas.drawString(text='Cantidad', 
                                x = self.x_position +400, 
                                y=initialY + (base_increment +0.7) * 9)
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
            self.canvas.drawString(text=str(item.quantity), 
                                    x = self.x_position +400, 
                                    y=initialY + (base_increment) * row_increment)
            row_increment+=1
        
    def create_proforma(self, header: Proforma_Header, detail: [Proforma_Detail], title ='Proforma',codigo_garantia = 'Pendiente'):
        self.set_company_name()
        self.set_company_addres(address='4to anillo, radial 26, calle #3', city='santa cruz', phoneNumber='3 352139')
        self.set_title(title= title)
        self.set_proforma_header(fecha=header.proforma_created_on.strftime("%d-%m-%Y %H:%M:%S"), 
                                 nombre= header.name, 
                                 ci=header.ci_nit, 
                                 email= header.email, 
                                 marca= header.car_model_id.car_brand_id.name, 
                                 modelo= header.car_model_id.name, 
                                 placa= header.car_plate, 
                                 celular= header.phone_number,
                                 codigo_garantia= codigo_garantia,
                                 codigo_proforma = header.id)
        self.proforma_body(body=detail)
        self.canvas.showPage()
        self.canvas.save()
        
    def create_nota_trabajo(self, header: Proforma_Header, detail: [Proforma_Detail]):
        self.set_company_name()
        self.set_company_addres(address='4to anillo, radial 26, calle #3', city='santa cruz', phoneNumber='3 352139')
        self.set_title(title='Nota trabajo')
        self.set_proforma_header(fecha=header.proforma_created_on.strftime("%d-%m-%Y %H:%M:%S"), 
                                 nombre= header.name, 
                                 ci=header.ci_nit, 
                                 email= header.email, 
                                 marca= header.car_model_id.car_brand_id.name, 
                                 modelo= header.car_model_id.name, 
                                 placa= header.car_plate, 
                                 celular= header.phone_number)
        self.nota_trabajo_body(body=detail)
        self.canvas.showPage()
        self.canvas.save()