from ..models import Sucursal
from ..helper.user import User_Helper
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned, FieldError

class User_Business:

    def __init__(self) -> None:
        self.helper = User_Helper()

    def get_user_sucursal(self, username):
        try:
            user_account = User.objects.get(username = username)
            sucursal = Sucursal.objects.filter(empleado__id = user_account.id)
            if len(sucursal) > 0:
                return sucursal[0]
            return None
        except ObjectDoesNotExist:
            print('get_user_sucursal ')
            return None
        except FieldError as e:
            print(str(e))
            return None