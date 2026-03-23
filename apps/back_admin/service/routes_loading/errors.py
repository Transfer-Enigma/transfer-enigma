import enum


class LoadingErrorException(Exception):
    pass


class InvalidRouteConditionException(LoadingErrorException):
    def __init__(self, condition):
        self.condition = condition

        super().__init__(
            f"Error: routes table contains invalid condition '{self.condition}':"
        )


class InvalidRouteConditionPricesException(LoadingErrorException):
    def __init__(self, condition, sea_prices, rail_prices):
        self.condition = "/".join(condition)
        self.sea_prices = list(map(str, sea_prices))
        self.rail_prices = list(map(str, rail_prices))

        super().__init__(
            f"Error: routes table contains invalid price configuration for condition '{self.condition}':"
            "SEA prices - " + (", ".join(self.sea_prices)) + "; "
            "RAIL prices - " + (", ".join(self.rail_prices))
        )


class PointsWithNanException(LoadingErrorException):
    def __init__(self, row_numbers: list[int]):
        super().__init__("Error: points table contains empty cells in rows: " + (", ".join(map(str, row_numbers))))
        self.row_numbers = row_numbers


class InvalidRouteTypeException(LoadingErrorException):
    def __init__(self, route_type):
        super().__init__(f"Error: invalid route type '{route_type}'")
        self.route_type = route_type


class InvalidRouteConditionCurrencyPairException(LoadingErrorException):
    def __init__(self, conditions, currencies, route_type):
        self.conditions = "/".join(conditions)
        self.currencies = "/".join(currencies)
        self.route_type = route_type.value if isinstance(route_type, enum.Enum) else route_type

        super().__init__(
            "Error: a route has invalid combination of conditions, currencies and route type:"
            f"{self.conditions}, {self.currencies}, {self.route_type}"
        )


class NotFoundException(LoadingErrorException):
    pass


class PointNotFoundException(NotFoundException):
    def __init__(self, error_key):
        super().__init__(f"Error: point '{error_key}' is not found")
        self.error_key = error_key
