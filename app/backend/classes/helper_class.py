import calendar
import math
import random
from datetime import datetime, timedelta
import calendar
import pandas 
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class HelperClass:

    def send_email(self, data):
        # Configuración del servidor SMTP
        smtp_server = 'mail.jisparking.com'
        smtp_port = 465
        smtp_user = 'noreply@jisparking.com'
        smtp_password = 'Macana11!'

        # Crear el objeto mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = 'contacto@jisparking.com'  # Reemplaza con la dirección de correo del destinatario
        msg['Subject'] = data['subject']

        # Cuerpo del mensaje
        body = f"""
        Nombre: {data['name']}
        Apellido: {data['lastname']}
        Correo: {data['email']}
        Teléfono: {data['phone']}
        
        Mensaje:
        {data['message']}
        """
        msg.attach(MIMEText(body, 'plain'))

        # Establecer conexión con el servidor SMTP
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, msg['To'], msg.as_string())

    def send_email_with_attachment(self, data, file):
        # Configuración del servidor SMTP
        smtp_server = 'mail.jisparking.com'
        smtp_port = 465
        smtp_user = 'noreply@jisparking.com'
        smtp_password = 'Macana11!'

        # Crear el objeto mensaje
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = 'empleos@jisparking.com'  # Reemplaza con la dirección de correo del destinatario
        msg['Subject'] = 'Nuevo postulante a Jisparking'

        # Cuerpo del mensaje en HTML
        body = f"""
        <html>
            <body>
                <p>Nombre: {data['names']}</p>
                <p>Región: {data['region']}</p>
                <p>Comuna: {data['commune']}</p>
                <p>CV: <a href="{file}" download="Curriculum.pdf">Curriculum</a></p>
            </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))  # Configurar como HTML

        # Establecer conexión con el servidor SMTP
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, msg['To'], msg.as_string())

    # Función para calcular el último periodo
    def calculate_last_period(current_period):
        
        current_period = current_period.split("-")

        current_period_year = int(current_period[0])
        current_period_month = int(current_period[1])

        if current_period_month == 1:
            last_period_year = current_period_year - 1
            last_period_month = 12
        else:
            last_period_year = current_period_year
            last_period_month = current_period_month - 1

        if last_period_month < 10:
            last_period_month = "0" + str(last_period_month)

        last_period = str(last_period_year) + "-" + str(last_period_month)

        return last_period
    
    # Función para calcular 2 periodos atrás
    def calculate_last_two_periods(current_period):
        current_period = current_period.split("-")

        current_period_year = int(current_period[0])
        current_period_month = int(current_period[1])

        if current_period_month == 1:
            last_period_year = current_period_year - 2
            last_period_month = 12
        else:
            last_period_year = current_period_year
            last_period_month = current_period_month - 2

        if last_period_month < 10:
            last_period_month = "0" + str(last_period_month)

        last_period = str(last_period_year) + "-" + str(last_period_month)

        return last_period

    # Función para agregar  dias administrativos
    def add_business_days(start_date, num_days, holidays):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        current_date = start_date
        added_days = 0
        while added_days < float(num_days):
            current_date += timedelta(days=1)
            if calendar.weekday(current_date.year, current_date.month, current_date.day) < 5:
                added_days += 1

        return current_date
    
    # Función para contar los fines de semana
    def count_weekends(start_date, end_date):
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        if end_date.weekday() == 4:  # Si es viernes (0=Lunes, 6=Domingo)
            end_date += timedelta(days=2)  # Suma 2 dias
        weekend_count = 0
        delta = timedelta(days=1)
        current_date = start_date

        while current_date <= end_date:
            if current_date.weekday() >= 5:  # Si es sábado o domingo
                weekend_count += 1
            current_date += delta
        return weekend_count
    
    # Función para calcular el valor de los días de vacaciones
    def vacation_day_value(amount):
        value = math.ceil(amount/30)

        return value

    # Función para calcular la gratificación
    def gratification(salary): 
        return math.ceil(salary*0.25)
    
    def get_end_document_total_years(self, start_year, end_year):
        date1 = datetime.strptime(start_year, "%Y-%m-%d")
        date2 = datetime.strptime(end_year, "%Y-%m-%d")
        
        # Calcular la diferencia en días entre las dos fechas
        delta = date2 - date1
        # Calcular la diferencia en años
        years = delta.days // 365
        # Calcular los meses restantes después de los años completos
        remaining_days = delta.days % 365
        remaining_months = remaining_days // 30

        # Si los meses restantes son mayores o iguales a 6, se agrega un año más
        if remaining_months >= 6:
            years += 1
        
        return years
    
    def months_to_years(self, months):
        years = int(months/12)

        return years

    # Función para calcular la cantidad de dias de vacaciones dependiendo si la persona se encuentra en zona extrema o no
    def vacation_days(self, days, extreme_zone_status_id):
        if days > 0:
            if extreme_zone_status_id == 1:
                total = round(int(days) * float(0.0553333333), 2)
            else:
                total = round(int(days) * float(0.0416666667), 2)
        else:
            total = 0
            
        return total
    
    # Función para calcular la cantidad de dias de vacaciones progresivas
    def progressive_vacation_days(self, months, extreme_zone_status_id):
        if months > 0:
            if extreme_zone_status_id == 1:
                total = math.ceil(float((months+1))*float(1.66))
            else:
                total = math.ceil((float(months+1)) * float(1.25))
        else:
            total = 0
            
        return total
    
    def numeric_rut(self, rut):
        rut = rut.split('-')

        return rut[0]
    
    def upper_string(self, string):
        result = string.upper()

        return result
    
    def split(self, value, separator):
        value = value.split(separator)

        return value
    
    def social_law_date(type, period, value):
        period = HelperClass().split(period, '-')
        period = period[1] +"/"+ period[0]

        if type == 1:
            value = "01/" + str(period)
        elif type == 2:
            value = str(value) +"/"+ str(period)

        return value
    
    def social_law_period(type, period, value):
        period = HelperClass().split(period, '-')

        if int(period[1]) < 10:
            period[1] = "0" + period[1]

        value = period[1] + period[0]

        return value
    
    def social_law_working_days(value):
        if datetime.now().month == 30:
            working_days = 30 - value
        else:
            working_days = datetime.now().month - value

        return working_days
    
    # Función para calcular la cantidad de días hábiles
    def legal_days(self, since, until):
        if since is not None and until is not None:
            since_date = datetime.strptime(str(since), "%Y-%m-%d")
            until_date = datetime.strptime(str(until), "%Y-%m-%d")
            delta = until_date - since_date
            return delta.days
        else:
            return 0
    
    def months(self, since, until):
        since_array = str(since).split("-")
        until_array = str(until).split("-")

        if since is not None and until is not None:
            if until_array[0] != '' and since_array[0] != '':
                return (int(until_array[0]) - int(since_array[0])) * 12 + int(until_array[1]) - int(since_array[1])
            else:
                return 0
        else:
            return 0
            
    def remove_from_string(self, value_to_remove, string):
        string = string.replace(value_to_remove, "")

        return string
    
    def replace(self, value_to_replace, replace_value, string):
        string = string.replace(value_to_replace, replace_value)

        return string
    
    def is_numeric(value):
        try:
            float(value)
            return True
        except ValueError:
            return False
    
    def add_zero(self, number):
        if number < 10:
            result = "0" + str(number)
        else:
            result = number

        return result
    
    def file_name(self, rut, description):
        now = datetime.now()

        current_year = now.year
        current_month = now.month
        current_day = now.day

        current_month = self.add_zero(current_month)

        random_float = random.randint(1, 9999999999999999)

        file_name = str(random_float) + "_" + str(rut) + "_" + str(description) + "_" + str(current_day) + "_" + str(current_month) + "_" + str(current_year)

        return file_name
    
    def nickname(self, name, lastname):
        nickname = str(name) + ' ' + str(lastname) 

        return nickname
    
    def days(self, since, until, no_valid_entered_days = 0):
        # Definir las fechas de inicio y finalización
        start_date = datetime.strptime(since, "%Y-%m-%d")
        end_date = datetime.strptime(until, "%Y-%m-%d")

        # Calcular la cantidad de días hábiles entre las dos fechas
        num_business_days = 0
        current_date = start_date
        while current_date <= end_date:
            if current_date.weekday() < 5:
                num_business_days += 1
            current_date += timedelta(days=1)

        return int(num_business_days)
    
    def verificator_digit(rut):
        rut = list(map(int, str(rut)))
        rut.reverse()
        
        factors = [2, 3, 4, 5, 6, 7]
        sum_value = sum(d * factors[i % len(factors)] for i, d in enumerate(rut))
        
        # Calcular el módulo 11
        rest = sum_value % 11
        verificator_digit = 11 - rest
        
        # Determinar el dígito verificador
        if verificator_digit == 10:
            return "K"
        elif verificator_digit == 11:
            return "0"
        else:
            return str(verificator_digit)

    def numeric_rut(self, rut):
        rut = rut.split('-')

        return rut[0]
    
    def convert_to_utf8(date):
        date = date.split('-')
        date = date[2] + "-" + date[1] + "-" + date[0]
        return date
    
    def get_net(value):
        net = round(value/1.19)

        return net
    
    def how_many_entrance_days(entrance_company):
        # Verificar si la entrada no es None
        if entrance_company is not None:
            # Convertir la fecha de entrada de cadena a objeto datetime
            entrance_company = datetime.strptime(str(entrance_company), '%Y-%m-%d')
            
            # Obtener la fecha actual
            current_date = datetime.now()
            
            # Obtener el año y mes actual
            current_year = current_date.year
            current_month = current_date.month
            
            # Obtener el año y mes de la entrada
            entrance_year = entrance_company.year
            entrance_month = entrance_company.month

            # Verificar si la entrada pertenece al mismo año y mes actual
            if entrance_year == current_year and entrance_month == current_month:
                # Obtener el primer día del mes actual
                first_date = datetime(current_year, current_month, 1)

                # Calcular la diferencia de días entre la entrada y el primer día del mes
                days = (entrance_company - first_date).days
                    
                return max(0, days)  # Retornar la diferencia de días, mínimo 0
                
            else:
                return 0  # Si la entrada no es del mismo año y mes actual, retornar None
        else:
            return 0  # Si la entrada es None, retornar None


    def how_many_exit_days(exit_company):
        # Verificar si la entrada no es None
        if exit_company is not None:
            # Convertir la fecha de entrada de cadena a objeto datetime
            exit_company = datetime.strptime(str(exit_company), '%Y-%m-%d')
            
            # Obtener el año y mes de la entrada
            exit_year = exit_company.year
            exit_month = exit_company.month

            # Obtener la fecha actual
            current_date = datetime.now()

            # Obtener el año y mes actual
            current_year = current_date.year
            current_month = current_date.month

            # Obtener el último día del mes actual
            last_day_month = HelperClass.last_day_month(exit_year, exit_month)

            # Obtener el día de la entrada
            exit_day = exit_company.day

            if exit_year == current_year and exit_month == current_month:

                # Calcular la diferencia de días entre el último día del mes y el día de la entrada
                days = last_day_month - exit_day

                return max(0, days)  # Retornar la diferencia de días, mínimo 0
            else:
                return 0
        else:
            return 0  # Si la entrada es None, retornar 0
    
    def validate_entrance(entrance_company, period):
        if value == None:
            value = 0

        return value
    
    def return_zero_empty_input(self, value):
        if value == None:
            value = 0

        return value
    
    def last_day_month(year, month):
        month = int(month)
        year = int(year)
        # Obtener el último día del mes y si es un año bisiesto
        end_day = calendar.monthrange(year, month)[1]
        is_leap_year = calendar.isleap(year)

        # Si el mes es febrero y es un año bisiesto, el último día es 29, de lo contrario es 28
        if month == 2 and is_leap_year:
            end_day = 29
        else:
            end_day = 28

        if month != 2:
            end_day = 30

        return end_day
    
    def full_last_day_month(year, month):
        month = int(month)
        year = int(year)
        # Obtener el último día del mes y si es un año bisiesto
        end_day = calendar.monthrange(year, month)[1]
        is_leap_year = calendar.isleap(year)

        # Si el mes es febrero y es un año bisiesto, el último día es 29, de lo contrario es 28
        if month == 2 and is_leap_year:
            end_day = 29
        elif month == 2 and is_leap_year == False:
            end_day = 28
        else:
            end_day = 30

        return end_day
    
    def final_day_month(self, month):
        if month == '1':
            return { "end_day": 31, "adjustment_day": -1 },
        elif month == '2':
            return { "end_day": 28, "adjustment_day": 2 }
        elif month == '3':
            return { "end_day": 30, "adjustment_day": 0 }
        elif month == '4':
            return { "end_day": 31, "adjustment_day": -1 }
        elif month == '5':
            return { "end_day": 30, "adjustment_day": 0 }
        elif month == '6':
            return { "end_day": 30, "adjustment_day": 0 }
        elif month == '7':
            return { "end_day": 31, "adjustment_day": -1 }
        elif month == '8':
            return { "end_day": 31, "adjustment_day": -1 }
        elif month == '9':
            return { "end_day": 30, "adjustment_day": 0 }
        elif month == '10':
            return { "end_day": 31, "adjustment_day": -1 }
        elif month == '11':
            return { "end_day": 30, "adjustment_day": 0 }
        elif month == '12':
            return { "end_day": 31, "adjustment_day": -1 }
    
    def get_time_Y_m_d(self):
        return datetime.now().strftime('%Y-%m-%d')
    
    def count_months(since_date, until_date):
        since_date = datetime.strptime(since_date, '%Y-%m-%d')
        until_date = datetime.strptime(until_date, '%Y-%m-%d')

        months = 0
        
        while since_date <= until_date:
            months += 1
            
            if since_date.month == 12:
                since_date = since_date.replace(year=since_date.year + 1, month=1, day=1)
            else:
                since_date = since_date.replace(month=since_date.month + 1, day=1)
        
        return months
    
    def get_periods(self, since, until):
        format = "%Y-%m-%d"
        start_obj = datetime.strptime(since, format)
        end_obj = datetime.strptime(until, format)

        periods = []

        while start_obj <= end_obj:
            if start_obj.month == end_obj.month:
                # Si estamos en el mismo mes, el periodo termina en la fecha de fin
                period_end = end_obj
            else:
                # Si estamos en diferentes meses, el periodo termina al final del mes actual
                next_month = start_obj.replace(day=28) + timedelta(days=4)  # Este será el próximo mes, para cualquier mes
                period_end = next_month - timedelta(days=next_month.day)  # Restamos la cantidad de días que ya pasaron en el próximo mes

            # Calculamos la cantidad de días en este periodo
            days = (period_end - start_obj).days + 1

            # Agregamos este periodo a la lista
            periods.append([start_obj.strftime(format), period_end.strftime(format), days])

            # El próximo periodo comienza al día siguiente
            start_obj = period_end + timedelta(days=1)

        return periods

    # Función para calcular la cantidad de vacaciones progresivas dependiendo de la cantidad de años y el nivel
    def progressive_vacation_days(self, years, level):
        total = 0

        if years >= 13 and (level == 1):
            total = total + 1
        
        if years >= 14 and (level == 1 or level == 2):
            total = total + 1
        
        if years >= 15 and (level == 1 or level == 2 or level == 3):
            total = total + 1
        
        if years >= 16 and (level == 1 or level == 2 or level == 3 or level == 4):
            total = total + 2
        
        if years >= 17 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5):
            total = total + 2
        
        if years >= 18 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6):
            total = total + 2
        
        if years >= 19 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7):
            total = total + 3
        
        if years >= 20 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8):
            total = total + 3
        
        if years >= 21 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8 or level == 9):
            total = total + 3
        
        if years >= 22 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8 or level == 9 or level == 10):
            total = total + 4

        if years >= 23 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8 or level == 9 or level == 10 or level == 11):
            total = total + 4

        if years >= 24 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8 or level == 9 or level == 10 or level == 11 or level == 12):
            total = total + 4

        if years >= 25 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8 or level == 9 or level == 10 or level == 11 or level == 12 or level == 13):
            total = total + 5

        if years >= 26 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8 or level == 9 or level == 10 or level == 11 or level == 12 or level == 13 or level == 14):
            total = total + 5

        if years >= 27 and (level == 1 or level == 2 or level == 3 or level == 4 or level == 5 or level == 6 or level == 7 or level == 8 or level == 9 or level == 10 or level == 11 or level == 12 or level == 13 or level == 14 or level == 15):
            total = total + 5

        if years == 0:
            total = 0

        return total

    # Función para obtener el último día del mes
    def get_last_day_of_month(date_str):
        date = datetime.strptime(date_str, '%Y-%m-%d')
        last_day = calendar.monthrange(date.year, date.month)[1]
        return last_day

    # Función para obtener el último día del mes
    def social_law_get_last_day_of_month(date_str):
        date = datetime.strptime(date_str, '%d/%m/%Y')
        last_day = calendar.monthrange(date.year, date.month)[1]
        return last_day
    
     # Función para obtener el último día del mes
    def last_day_of_month(date_str):
        date = datetime.strptime(date_str, '%Y-%m-%d')
        last_day = date.replace(day=1) - timedelta(days=1) + timedelta(days=32)
        return (last_day - timedelta(days=1)).strftime('%Y-%m-%d')
    
    def get_social_law_young_status(value):
        if value == 1:
            return "S"
        else:
            return "N"

    def extention_contract(date):
        # Convertir la fecha de entrada a un objeto datetime
        date_dt = datetime.strptime(date, "%Y-%m-%d")
        
        # Calcular el último día hábil del mes siguiente
        next_month_end = pandas.date_range(start=date_dt, periods=2, freq='M')[1]
        
        # Formatear la fecha como "YYYY-MM-DD"
        return next_month_end.strftime("%Y-%m-%d")
    
    def fix_current_dte_period(period):
        period = period.split('-')

        month = period[1]

        year = period[0]

        return str(year) + "-" + str(month)
    
    def fix_last_dte_period(period):
        period = period.split('-')

        month = int(period[1]) - 1

        if month == 0:
            month = 12
            year = int(period[0]) - 1
        else:
            year = period[0]

        if month < 10:
            month = "0" + str(month)
        else:
            month = str(month)

        return str(month) + "-" + str(year)
    
    def create_period_date(period):
        period = period.split('-')

        return period[0]  + '-' + period[1] + '-01' + ' 00:00:00'