from __future__ import annotations

from pathlib import Path, PurePosixPath
import sys
from typing import (Any,
                    BinaryIO,
                    Callable,
                    Dict,
                    List,
                    Literal,
                    NewType,
                    Optional,
                    overload,
                    Protocol,
                    Sequence,
                    TextIO,
                    Type,
                    TypeVar,
                    Union)

from clustertools.file_objects.configs.base_config import BaseConfig
from clustertools.shared.object_monitors import MonitoredEnviron, MonitoredList


PathLike = Union[Path, PurePosixPath, str]


T = TypeVar('T')
OneOrMore = Union[T, Sequence[T]]
NoneOrMore = Optional[OneOrMore]    # equivalent to Union[None, OneOrMore]


MswDestBase = TypeVar('MswDestBase', BinaryIO, Path, str, TextIO)
MswStdoutDest = Union[MswDestBase, Type[type(sys.stdout)], Literal['stdout']]
MswStderrDest = Union[MswDestBase, Type[type(sys.stderr)], Literal['stderr']]


WallTimeStr = NewType('WallTimeStr', str)
EmailAddress = NewType('EmailAddress', str)

list_of_str = List[str]

# config hook typing
_Config = TypeVar('_Config', bound=BaseConfig)
_Func1 = TypeVar('_Func1', bound=Callable)
_Func2 = TypeVar('_Func2', bound=Callable)
_UncheckedVal = TypeVar('_UncheckedVal', bound=Any)
_CheckedVal = TypeVar('_CheckedVal', bound=Any)
# _Hook = TypeVar('_Hook', bound=_Func1[[_Conf, _CheckedVal], None])
_BoundHook = TypeVar('_BoundHook', bound=_Func2[[_UncheckedVal], _CheckedVal])
_str_return_types = Union[str, PathLike, MonitoredList, WallTimeStr,
                          EmailAddress, Literal['local', 'remote', 'recent']]
_nested_dict = Dict[str, Union[str, '_nested_dict']]
class _Hook(Protocol[_Config, _UncheckedVal]):
    @overload
    def __call__(self, val: str) -> str: ...

    @overload
    def __call__(self, val: str) -> PathLike: ...

    @overload
    def __call__(self, val: str) -> MonitoredList: ...

    @overload
    def __call__(self, val: str) -> WallTimeStr: ...

    @overload
    def __call__(self, val: str) -> EmailAddress: ...

    @overload
    def __call__(self, val: str) -> Literal['local', 'remote', 'recent']: ...

    @overload
    def __call__(self, val: bool) -> bool: ...

    @overload
    def __call__(self, val: int) -> int: ...

    @overload
    def __call__(self, val: List[str]) -> MonitoredList: ...

    @overload
    def __call__(self, val: _nested_dict) -> MonitoredEnviron: ...

    def __call__(self, val: Union[str, bool, int, list]) -> Any: ...

    def __get__(self, inst: _Conf) -> _BoundHook: ...
