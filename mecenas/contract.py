

class Contract:
    def __init__(self, addresses, initial_tx=None, v=0):
        self.version = v
        self.initial_tx = initial_tx
        self.addresses = addresses

    @staticmethod
    def participants(version):
        pass
    @staticmethod
    def roles(version):
        pass