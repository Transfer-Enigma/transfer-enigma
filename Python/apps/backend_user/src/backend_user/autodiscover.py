import pkgutil
from importlib import import_module


def api_discover() -> list:  # noqa: C901
    routers = []
    pkg = import_module("backend_user.api")

    for version_pkg in pkgutil.iter_modules(pkg.__path__):
        module_name = f"backend_user.api.{version_pkg.name}"
        try:
            module = import_module(module_name)
        except (ModuleNotFoundError, AttributeError) as ex:
            raise ex

        for api_pkg in pkgutil.iter_modules(module.__path__):
            module_name = f"backend_user.api.{version_pkg.name}.{api_pkg.name}"
            try:
                module = import_module(module_name)
            except (ModuleNotFoundError, AttributeError) as ex:
                raise ex

            for package_module in pkgutil.iter_modules(module.__path__):
                if not package_module.ispkg:
                    try:
                        endpoints = import_module(module_name + "." + package_module.name)
                        routers.append(endpoints.router)
                    except (ModuleNotFoundError, AttributeError) as ex:
                        raise ex

    return routers
