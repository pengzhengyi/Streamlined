from decorator import FunctionMaker


def decorator_apply(dec, func):
    """
    Decorate a function by preserving the signature even if dec
    is not a signature-preserving decorator.

    See https://github.com/micheles/decorator/blob/master/docs/documentation.md
    """
    return FunctionMaker.create(
        func, "return decfunc(%(signature)s)", dict(decfunc=dec(func)), __wrapped__=func
    )
