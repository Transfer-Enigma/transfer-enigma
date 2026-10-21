def create_an_error_descriptor_from_an_exception(exception: Exception):
    return {
        "class_type": str(type(exception)),
        "description": str(exception),
    }


def create_multi_error_response_from_an_array_of_exceptions(exceptions: list[Exception]):
    return {
        "errors": [
            create_an_error_descriptor_from_an_exception(e)
            for e in exceptions
            if isinstance(e, Exception)
        ],
    }
