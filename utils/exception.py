class UrsaException(Exception):
    def __init__(self, detail):
        self.code = 50001
        self.detail = detail


class MqException(UrsaException):
    def __init__(self, detail):
        self.code = 50002
        self.detail = detail


class BreakException(Exception):
    def __init__(self):
        pass


class CancelException(Exception):
    def __init__(self):
        pass
