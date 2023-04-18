class UrsaException(Exception):
    def __init__(self, detail):
        self.code = 50001
        self.detail = detail
