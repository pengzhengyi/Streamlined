from streamlined.component.proxies.proxy import Proxy


class Base:
    def __init__(self):
        super().__init__()
        self.foo = "bar"


def test_proxy():
    proxy = Proxy(Base())
    assert proxy.foo == "bar"
