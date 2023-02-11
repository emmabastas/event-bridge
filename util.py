from typing import Type, TypeVar, Callable, Generic
import json
from selenium import webdriver


X = TypeVar("X")
Y = TypeVar("Y")


def memoize(name: str, f: Callable[[X], Y]) -> Callable[[X], Y]:
    return lambda x: memoize_(name, f, x)


def memoize_(name: str, f: Callable[[X], Y], x: X) -> Y:
    try:
        with open(f"./memoized/{name}::{x}", "r") as h:
            return json.load(h)
    except FileNotFoundError:
        y = f(x)
        with open(f"./memoized/{name}::{x}", "w") as h:
            json.dump(y, h)
        return y



R = TypeVar("R", covariant=True)
S = TypeVar("S", contravariant=True)
T = TypeVar("T", contravariant=True)


def curry(f: Callable[[T, S], R]) -> Callable[[T], Callable[[S], R]]:
    return lambda t: lambda s: f(t, s)


C = TypeVar("C")


class LazyInstantiateProxy(Generic[C]):
    def __init__(self, proxied_class: Type[C], *args, **kwargs):
        self.__proxied_class: Type[C] = proxied_class
        self.__instantiation_args = args
        self.__instantiation_kwargs = kwargs
        self.__proxied_instance: C | None = None

    def __getattr__(self, attr):
        if attr == "__proxied_instance":
            return self.__proxied_instance

        if self.__proxied_instance is None:
            self.__proxied_instance = self.__proxied_class(
                *self.__instantiation_args,
                **self.__instantiation_kwargs
            )

        return self.__proxied_instance.__getattribute__(attr)


class LazyFirefoxWebDriver(LazyInstantiateProxy[webdriver.Firefox]):
    def __init__(self, *args, **kwargs):
        super().__init__(webdriver.Firefox, *args, **kwargs)

    def __getattr__(self, attr):
        if attr == "quit" and super().__getattr__("__proxied_instance") is None:
           return lambda: None
        return super().__getattr__(attr)



def lazy_firefox_web_driver(*args, **kwargs) -> webdriver.Firefox:
    return LazyFirefoxWebDriver(*args, **kwargs) # type: ignore
