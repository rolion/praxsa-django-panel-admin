class User_Helper():

    def is_user_admin(self, user):
        user_groups = user.groups.values_list('name',flat = True)
        return 'admin' in list(user_groups)
    
    def is_user_installer(self, user):
        user_groups = user.groups.values_list('name',flat = True)
        return 'instalador' in list(user_groups)
