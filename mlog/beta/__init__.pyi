from typing import Any, Generic, Iterator, Optional, TypeVar, Union, overload

T = TypeVar("T")

class LocalArray(Generic[T]):
    """Compile-time, in-register fixed-size array in mlog.beta."""

    def __init__(
        self,
        size: int,
        default: Optional[T] = None,
        dtype: Optional[Union[type, str]] = None,
    ) -> None: ...
    @property
    def size(self) -> int: ...
    @property
    def capacity(self) -> int: ...
    @property
    def dtype(self) -> Optional[Union[type, str]]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> T: ...
    def __setitem__(self, index: int, value: T) -> None: ...
    def __iter__(self) -> Iterator[T]: ...
    def fill(self, value: T) -> None: ...

class BlockArray(Generic[T]):
    """Runtime array backed by a Mindustry Memory Cell (64) or Memory Bank (512)."""

    def __init__(
        self,
        block: str,
        size: int,
        dtype: Optional[Union[type, str]] = None,
    ) -> None: ...
    @property
    def block(self) -> str: ...
    @property
    def size(self) -> int: ...
    @property
    def capacity(self) -> int: ...
    @property
    def dtype(self) -> Optional[Union[type, str]]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> T: ...
    def __setitem__(self, index: int, value: T) -> None: ...
    def __iter__(self) -> Iterator[T]: ...
    def fill(self, value: T) -> None: ...

class Array(Generic[T]):
    """Unified Array factory for mlog.beta."""

    @overload
    def __new__(
        cls,
        size: int,
        default: Optional[T] = None,
        dtype: Optional[Union[type, str]] = None,
    ) -> LocalArray[T]: ...
    @overload
    def __new__(
        cls,
        block: str,
        size: int,
        dtype: Optional[Union[type, str]] = None,
    ) -> BlockArray[T]: ...
    @overload
    def __new__(
        cls,
        *,
        size: int,
        block: Optional[str] = None,
        default: Optional[T] = None,
        dtype: Optional[Union[type, str]] = None,
    ) -> Union[LocalArray[T], BlockArray[T]]: ...
    def __new__(cls, *args: Any, **kwargs: Any) -> Union[LocalArray[Any], BlockArray[Any]]: ...

__all__ = ["LocalArray", "BlockArray", "Array"]
