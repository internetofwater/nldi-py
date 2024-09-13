class ProviderGenericError(Exception):
    """provider generic error"""

    pass


class ProviderConnectionError(ProviderGenericError):
    """provider connection error"""

    pass


class ProviderTypeError(ProviderGenericError):
    """provider type error"""

    pass


class ProviderInvalidQueryError(ProviderGenericError):
    """provider invalid query error"""

    pass


class ProviderQueryError(ProviderGenericError):
    """provider query error"""

    pass


class ProviderItemNotFoundError(ProviderGenericError):
    """provider item not found query error"""

    pass
