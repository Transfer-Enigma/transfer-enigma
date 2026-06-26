class LoadingErrorException(Exception):
    pass


class InvalidRouteConditionException(LoadingErrorException):
    def __init__(self, condition):
        self.condition = condition

        super().__init__(
            f"Error: routes table contains invalid condition '{self.condition}':"
        )


class NoPriceInRouteException(LoadingErrorException):
    def __init__(self):
        super().__init__("Error: routes table contains a row without any prices")


class InvalidRouteTypeException(LoadingErrorException):
    def __init__(self, route_type):
        self.route_type = route_type
        super().__init__(f"Error: invalid route type: {route_type}")


class PointsWithNanException(LoadingErrorException):
    def __init__(self, row_numbers: list[int]):
        super().__init__("Error: points table contains empty cells in rows: " + (", ".join(map(str, row_numbers))))
        self.row_numbers = row_numbers


class InvalidDropOffRow(LoadingErrorException):
    pass


class NotFoundException(LoadingErrorException):
    pass


class PointNotFoundException(NotFoundException):
    def __init__(self, error_key):
        super().__init__(f"Error: point '{error_key}' is not found")
        self.error_key = error_key
