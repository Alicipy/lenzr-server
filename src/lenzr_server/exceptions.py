class NotFoundException(Exception):
    def __init__(self, detail: str = "Not found"):
        self.detail = detail
        super().__init__(detail)


class AlreadyExistingException(Exception):
    def __init__(self, detail: str = "Already exists"):
        self.detail = detail
        super().__init__(detail)
