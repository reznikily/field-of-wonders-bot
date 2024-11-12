class Store:
    def __init__(self, token):
        from app.users.accessor import UserAccessor

        self.user = UserAccessor(self, token)
