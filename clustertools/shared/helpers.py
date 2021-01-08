from __future__ import annotations

import time
from functools import wraps
from os.path import expanduser, expandvars, realpath
from pathlib import Path
from typing import overload, TYPE_CHECKING

if TYPE_CHECKING:
    from clustertools.shared.typing import PathLike, WallTimeStr


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


def validate_walltime(walltime_str: str) -> WallTimeStr:
    try:
        time.strptime(walltime_str, '%H:%M:%S')
    except ValueError:
        try:
            time.strptime(walltime_str, '%M:%S')
        except ValueError:
            raise ValueError(
                "Received malformed 'wall_time' string. Format should be "
                "'%H:%M:%S', or '%M:%S' if requesting < 1 hour"
            )
    return walltime_str
