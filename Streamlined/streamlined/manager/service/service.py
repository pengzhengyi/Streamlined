from typing import Type


class Service:
    pass


def add_services(name: str, *service_classes: Type[Service]) -> Type[Service]:

    return type(name, service_classes, {})
