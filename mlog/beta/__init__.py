"""mlog.beta: Beta language features, data structures, and abstractions for Mindustry Logic."""

import re
from typing import Any, Generic, Iterator, List, Optional, TypeVar, Union

T = TypeVar("T")


class LocalArray(Generic[T]):
    """Compile-time, in-register fixed-size array in mlog.beta.

    Mapped directly to processor registers (arr_0, arr_1, ...).
    Does NOT require a physical Memory Cell or Memory Bank.
    Supports compile-time static indexing with zero memory overhead.
    """

    def __init__(
        self,
        size: int,
        default: Optional[T] = None,
        dtype: Optional[Union[type, str]] = None,
    ) -> None:
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError(f"LocalArray size must be a positive integer, got {size!r}")
        if size > 64:
            raise ValueError(f"LocalArray size {size} exceeds maximum register capacity (64)")

        VALID_TYPE_DTYPES = (int, float, bool, str, object)
        VALID_STR_DTYPES = ("int", "float", "bool", "str", "any")
        if dtype is not None:
            if dtype is Any or (hasattr(dtype, "_name") and dtype._name == "Any"):
                pass
            elif isinstance(dtype, type):
                if dtype not in VALID_TYPE_DTYPES:
                    raise ValueError(f"unsupported LocalArray dtype '{dtype}': expected int, float, bool, str, or any")
            elif isinstance(dtype, str):
                if dtype.lower() not in VALID_STR_DTYPES:
                    raise ValueError(f"unsupported LocalArray dtype '{dtype}': expected int, float, bool, str, or any")
            else:
                raise TypeError(f"LocalArray dtype must be a type or string, got {type(dtype).__name__}")

        self._size = size
        self._default = default
        self._dtype = dtype
        self._elements = [default] * size

    @property
    def size(self) -> int:
        """Return the fixed capacity of the LocalArray."""
        return self._size

    @property
    def capacity(self) -> int:
        """Return the register capacity of the LocalArray (equals size)."""
        return self._size

    @property
    def dtype(self) -> Optional[Union[type, str]]:
        """Return the element dtype of the LocalArray."""
        return self._dtype

    def __len__(self) -> int:
        return self._size

    def __getitem__(self, index: int) -> T:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError(f"LocalArray index must be an integer, got {type(index).__name__}")
        if index < 0 or index >= self._size:
            raise IndexError(f"LocalArray index out of range: {index} not in [0, {self._size})")
        return self._elements[index]

    def __setitem__(self, index: int, value: T) -> None:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError(f"LocalArray index must be an integer, got {type(index).__name__}")
        if index < 0 or index >= self._size:
            raise IndexError(f"LocalArray index out of range: {index} not in [0, {self._size})")
        self._elements[index] = value

    def __iter__(self) -> Iterator[T]:
        return iter(self._elements)

    def fill(self, value: T) -> None:
        """Fill all elements in the array with value."""
        for i in range(self._size):
            self._elements[i] = value

    def __repr__(self) -> str:
        return f"LocalArray(size={self._size}, elements={self._elements!r})"


class BlockArray(Generic[T]):
    """Runtime array backed by a Mindustry Memory Cell (64) or Memory Bank (512).

    Supports O(1) dynamic indexing at runtime via native `read` and `write` opcodes.
    Requires a physical hardware block linked to the processor.
    """

    CELL_CAPACITY = 64
    BANK_CAPACITY = 512

    def __init__(
        self,
        block: str,
        size: int,
        dtype: Optional[Union[type, str]] = None,
    ) -> None:
        if not isinstance(block, str) or not block:
            raise ValueError(f"BlockArray block must be a non-empty string, got {block!r}")

        canonical = block.lower()
        if re.match(r"^cell\d*$", canonical):
            self._capacity = self.CELL_CAPACITY
        elif re.match(r"^bank\d*$", canonical):
            self._capacity = self.BANK_CAPACITY
        else:
            raise ValueError(
                f"invalid memory block '{block}': BlockArray only supports memory cells (capacity {self.CELL_CAPACITY}) "
                f"or memory banks (capacity {self.BANK_CAPACITY})"
            )

        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError(f"BlockArray size must be a positive integer, got {size!r}")
        if size > self._capacity:
            raise ValueError(
                f"BlockArray size {size} exceeds physical block '{canonical}' capacity ({self._capacity})"
            )

        VALID_TYPE_DTYPES = (int, float, bool, str, object)
        VALID_STR_DTYPES = ("int", "float", "bool", "str", "unit", "block", "any")
        if dtype is not None:
            if dtype is Any or (hasattr(dtype, "_name") and dtype._name == "Any"):
                pass
            elif isinstance(dtype, type):
                if dtype not in VALID_TYPE_DTYPES:
                    raise ValueError(
                        f"unsupported BlockArray dtype '{dtype}': expected one of {', '.join(VALID_STR_DTYPES)}"
                    )
            elif isinstance(dtype, str):
                if dtype.lower() not in VALID_STR_DTYPES:
                    raise ValueError(
                        f"unsupported BlockArray dtype '{dtype}': expected one of {', '.join(VALID_STR_DTYPES)}"
                    )
            else:
                raise TypeError(f"BlockArray dtype must be a type or string, got {type(dtype).__name__}")

        self._block = canonical
        self._size = size
        self._dtype = dtype
        self._elements: List[Any] = [0.0] * size

    @property
    def block(self) -> str:
        """Return the target hardware memory block name (e.g. 'cell1')."""
        return self._block

    @property
    def size(self) -> int:
        """Return the fixed allocated size of the BlockArray."""
        return self._size

    @property
    def capacity(self) -> int:
        """Return the maximum physical capacity of the backing block."""
        return self._capacity

    @property
    def dtype(self) -> Optional[Union[type, str]]:
        """Return the element dtype of the BlockArray."""
        return self._dtype

    def __len__(self) -> int:
        return self._size

    def __getitem__(self, index: int) -> T:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError(f"BlockArray index must be an integer, got {type(index).__name__}")
        if index < 0 or index >= self._size:
            raise IndexError(f"BlockArray index out of range: {index} not in [0, {self._size})")
        return self._elements[index]

    def __setitem__(self, index: int, value: T) -> None:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError(f"BlockArray index must be an integer, got {type(index).__name__}")
        if index < 0 or index >= self._size:
            raise IndexError(f"BlockArray index out of range: {index} not in [0, {self._size})")
        self._elements[index] = value

    def __iter__(self) -> Iterator[T]:
        return iter(self._elements)

    def fill(self, value: T) -> None:
        """Fill all elements in the array with value."""
        for i in range(self._size):
            self._elements[i] = value

    def __repr__(self) -> str:
        return f"BlockArray(block='{self._block}', size={self._size}, elements={self._elements!r})"


class Array(Generic[T]):
    """Unified Array factory for mlog.beta.

    Dispatches to:
    - LocalArray: when instantiated with size only (e.g. Array(4), Array(size=4)),
      creating a compile-time in-register array with 0 external memory blocks.
    - BlockArray: when instantiated with a block name (e.g. Array("cell1", 10),
      Array(block="cell1", size=10)), backed by a physical Memory Cell or Memory Bank.
    """

    _generic_dtype = None

    @classmethod
    def __class_getitem__(cls, item: Any) -> Any:
        class _SpecializedArray(cls):  # type: ignore[valid-type, misc]
            _generic_dtype = item

        return _SpecializedArray

    def __new__(
        cls,
        *args: Any,
        **kwargs: Any,
    ) -> Union[LocalArray[Any], BlockArray[Any]]:
        valid_kwargs = {"block", "size", "dtype", "default"}
        for k in kwargs:
            if k not in valid_kwargs:
                raise TypeError(f"Array() got an unexpected keyword argument {k!r}")

        block = kwargs.get("block")
        size = kwargs.get("size")
        dtype = kwargs.get("dtype")
        default = kwargs.get("default")

        if dtype is None and cls._generic_dtype is not None:
            dtype = cls._generic_dtype

        num_args = len(args)
        if num_args > 3:
            raise TypeError(f"Array() takes at most 3 positional arguments ({num_args} given)")

        if num_args == 0:
            if size is None:
                raise TypeError("Array() missing required argument: 'size'")
            if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
                raise ValueError(f"Array size must be a positive integer, got {size!r}")
            if block is not None:
                if "default" in kwargs and default is not None:
                    raise ValueError(
                        "argument 'default' is only supported for in-register LocalArray, not BlockArray; "
                        "use .fill() for BlockArray"
                    )
                return BlockArray(block=block, size=size, dtype=dtype)
            else:
                return LocalArray(size=size, default=default, dtype=dtype)

        first_arg = args[0]
        if isinstance(first_arg, bool):
            raise ValueError(f"Array size must be a positive integer, got {first_arg!r}")

        if isinstance(first_arg, str):
            if "block" in kwargs:
                raise TypeError("Array() got multiple values for argument 'block'")
            block = first_arg

            if num_args >= 2:
                if "size" in kwargs:
                    raise TypeError("Array() got multiple values for argument 'size'")
                size = args[1]

            if num_args == 3:
                if "dtype" in kwargs:
                    raise TypeError("Array() got multiple values for argument 'dtype'")
                dtype = args[2]

            if size is None:
                raise TypeError("Array() missing required argument: 'size'")
            if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
                raise ValueError(f"Array size must be a positive integer, got {size!r}")

            if "default" in kwargs and default is not None:
                raise ValueError(
                    "argument 'default' is only supported for in-register LocalArray, not BlockArray; "
                    "use .fill() for BlockArray"
                )

            return BlockArray(block=block, size=size, dtype=dtype)

        elif isinstance(first_arg, int):
            if "size" in kwargs:
                raise TypeError("Array() got multiple values for argument 'size'")
            size = first_arg

            if isinstance(size, bool) or size <= 0:
                raise ValueError(f"Array size must be a positive integer, got {size!r}")

            if num_args >= 2:
                if "default" in kwargs:
                    raise TypeError("Array() got multiple values for argument 'default'")
                default = args[1]

            if num_args == 3:
                if "dtype" in kwargs:
                    raise TypeError("Array() got multiple values for argument 'dtype'")
                dtype = args[2]

            if "block" in kwargs and block is not None:
                raise TypeError("Array() received unexpected 'block' argument when size is passed positionally")

            return LocalArray(size=size, default=default, dtype=dtype)

        else:
            raise TypeError(
                f"Array() first argument must be a string (block name) or integer (size), got {type(first_arg).__name__}"
            )


__all__ = ["LocalArray", "BlockArray", "Array"]
