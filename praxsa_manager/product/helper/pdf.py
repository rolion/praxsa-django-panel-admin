from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor, black

class PDFService:

    def __init__(self, file_name = 'Proforma') -> None:
        self.x_position = 14
        self.main_color = (42/255,49/255,129/255)
        self.increment = 5
        self.company_name = 'Praxsa'
        self.canvas = canvas.Canvas(filename=f'{file_name}.pdf', pagesize=letter) 
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

    def set_proforma_detail(self, fecha, nombre, ci, email, celular, marca, modelo, placa):
      columnSeparation = 75
      fontSizeTitles = 12
      fontSizeNormal = 11
      fontSizeName = 14
    #   self.canvas.setFillColor(aColor=black)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeTitles)
      self.canvas.drawString(text='Fecha', x = self.x_position,  y=50)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=fecha, x = self.x_position, y=55)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeTitles)
      self.canvas.drawString(text='Cod. Proforma', x = self.x_position  +columnSeparation, y=50)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeNormal)
      self.canvas.drawString(text='Datos personales para la garantía', x = self.x_position, y=60)
      self.canvas.setFont(psfontname='Helvetica-Bold', size=fontSizeName)
      self.canvas.drawString(text=nombre, x = self.x_position, y=67)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'C.I.: {ci}', x = self.x_position, y=75)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Nro. Celular: {celular}', x = self.x_position, y=80)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Correo: {email}', x = self.x_position, y=85)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text='Nro. Garantia:', x = self.x_position +columnSeparation, y=75)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Marca: {marca}', x = self.x_position +columnSeparation, y=80)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Modelo: {modelo}', x = self.x_position +columnSeparation, y=85)
      self.canvas.setFont(psfontname='Helvetica', size=fontSizeNormal)
      self.canvas.drawString(text=f'Placa: {placa}', x = self.x_position +columnSeparation, y=90)

    def create_file(self):
        self.set_company_name()
        self.set_company_addres(address='some addres', city='santa cruz', phoneNumber='+59173979677')
        self.set_title(title='Proforma')
        # self.set_proforma_detail(fecha='12/12/2023', nombre='oscar leon', ci='6349744', email='roleonm@gmail.com', marca='suzuki', modelo='alto', placa='asd123', celular=73979677)
        self.canvas.showPage()
        self.canvas.save()
