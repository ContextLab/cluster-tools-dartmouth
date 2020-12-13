from functools import wraps
from os.path import expanduser, expandvars, realpath
from pathlib import Path
from typing import overload

from clustertools.shared.typing import PathLike


# TODO: implement versions of expanduser and expandvars that
#  (optionally?) use PseudoEnviron

@overload
def cleanpath(path: str) -> str:
    ...
@overload
def cleanpath(path: Path) -> Path:
    ...
def cleanpath(path: PathLike) -> PathLike:
    return type(path)(str(realpath(expanduser(expandvars(path)))))


def bindable(func):
    # ADD DOCSTRING - decorates a function 'func', allowing it to be
    #  bound to an object 'instance' at runtime and optionally added as
    #  an instance method
    @wraps(func)
    def bind(instance):
        return func.__get__(instance)
    return bind
