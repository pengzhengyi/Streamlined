from streamlined.component.proxies.patch import patch


class Base:
    def __init__(self):
        super().__init__()
        self.foo = "foo"
        self.bar = "bar"

    def concat(self):
        return self.foo + self.bar


class BasePatchProvider:
    def __init__(self, foo: str, **kwargs):
        super().__init__(**kwargs)
        self.foo = foo


def test_patch():

    # attribute proxying
    base = Base()
    assert base.foo == "foo"
    assert base.bar == "bar"

    patched_base = patch(base, BasePatchProvider, foo="PATCHED FOO")
    assert patched_base.foo == "PATCHED FOO"
    assert patched_base.bar == "bar"

    # method self reference proxying
    assert patched_base.concat() == "PATCHED FOObar"
