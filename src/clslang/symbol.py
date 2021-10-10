
import itertools
import copy
from abc import abstractmethod
from typing import Any, Callable, Dict, Generic, Hashable, Iterable, Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union

from clslang.srcitr import SrcItr, StopSrcItr

# DictKeyVals = Tuple[Tuple, Tuple[Any, Any]]
T = TypeVar('T')
CT = TypeVar('CT') # Char type

CharType = str
CharSeq = str
Maker = Callable[[Any], Any]

class SymbolTryFailed(Exception):
    """ Symbol Try Failed Exception """

class IgnoreRes:
    """ Symbol: Ignore on results """

class Symbol():
    """ Symbol ABC """
    def __init__(self, *, maker:Maker):
        self.maker = maker

    def make(self, val:Any) -> Any:
        if self.maker is None:
            if isinstance(val, Iterator):
                return tuple(val)
            return val
        return self.maker(val)

    @abstractmethod
    def tryitr(self, chitr:SrcItr) -> Any:
        raise NotImplementedError()

    def trystr(self, chseq:Iterable) -> Any:
        return self.tryitr(SrcItr(chseq))

SymbolLike = Union[Symbol, tuple, str]

def to_symbol(symbol:SymbolLike) -> Symbol:
    if isinstance(symbol, Symbol):
        return symbol
    if isinstance(symbol, tuple):
        return Seq(*symbol)
    if isinstance(symbol, str):
        if len(symbol) == 1:
            return Char(symbol[0])
        return Str(symbol)
    raise TypeError()

class CharABC(Symbol):
    """ Single character """
    @abstractmethod
    def is_valid_char(self, ch:CharType) -> bool:
        raise NotImplementedError()

    def tryitr(self, chitr:SrcItr) -> Any:
        ch = next(chitr)
        if self.is_valid_char(ch):
            return ch
        raise SymbolTryFailed()

class ExplChar(CharABC):
    """ Char (Explicit) """
    def __init__(self, ch:CharType, *, maker:Maker=tuple) -> None:
        super().__init__(maker=maker)
        self.ch = ch

    def is_valid_char(self, ch:CharType) -> bool:
        return ch == self.ch

class Char(ExplChar, IgnoreRes):
    """ Char (Ignored in results) """

class CharNot(CharABC):
    def __init__(self, ch:CharType, *, maker:Maker=tuple) -> None:
        super().__init__(maker=maker)
        self.ch = ch

    def is_valid_char(self, ch:CharType) -> bool:
        return ch != self.ch

class Chars(CharABC):
    def __init__(self, *chs:CharType, maker:Maker=tuple) -> None:
        super().__init__(maker=maker)
        self.chset = set(chs)

    def is_valid_char(self, ch:CharType) -> bool:
        return ch in self.chset

class CharsNot(CharABC):
    def __init__(self, *chs:CharType, maker:Maker=tuple) -> None:
        super().__init__(maker=maker)
        self.chset = set(chs)

    def is_valid_char(self, ch:CharType) -> bool:
        return ch not in self.chset

# class CharRange(CharABC):
#     def __init__(self, ch_first:CharType, ch_last:CharType) -> None:
#         self.ch_first = int(ch_first)
#         self.ch_last  = int(ch_last)

#     def is_valid_char(self, ch:CharType) -> bool:
#         return self.ch_first <= int(ch) and int(ch) <= self.ch_last 

# DigitChars = CharRange('0', '9')
# UpperAlphaChars = CharRange('A', 'Z')
# LowerAlphaChars = CharRange('a', 'z')

class Seq(Symbol):
    """ Sequence of symbols """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        super().__init__(maker=maker)
        self.symbols = list(map(to_symbol, symbols))
        self._n_out_syms = len(list(filter(lambda sym: not isinstance(sym, IgnoreRes), self.symbols)))

    def add(self, symbol:SymbolLike):
        """ Add a new symbol to this sequence """
        self.symbols.append(sym := to_symbol(symbol))
        if not isinstance(sym, IgnoreRes):
            self._n_out_syms += 1
    
    def _make(self, vitr:Iterator) -> Any:
        """ Make a value from the processed child values
            (Default implementation)
        """
        return self.make(vitr if self._n_out_syms != 1 else list(vitr)[0])

    def tryitr(self, chitr:SrcItr) -> Any:
        """ Put a character """
        def _itr():
            for sym in self.symbols:
                res = sym.tryitr(chitr)
                if not isinstance(sym, IgnoreRes):
                    yield res
        return self._make(_itr())

class Ignore(Seq, IgnoreRes):
    """ Sequences to ignore """

class StrMaker(Symbol):
    """ Symbol which makes string """
    def _make(self, seq_res:Iterator) -> Any:
        return ''.join(seq_res)

class ExplStr(StrMaker, Seq):
    """ String (Explicit) """
    def __init__(self, chseq:str):
        super().__init__(*(ExplChar(ch) for ch in chseq))

class Str(ExplStr, IgnoreRes):
    """ String (Ignored in results) """
    def __init__(self, chseq:str, *, value:Any=str):
        """
            chseq: The string to find
            value: The The specific value which corresponds to `chseq`
                   (use `str` to return the original string)
        """
        super().__init__(chseq)
        self.value = value

    def _make(self, seq_res:Iterator) -> Any:
        if self.value is str:
            return super().make(seq_res)
        _ = tuple(seq_res) # Try the rule sequence 
        return self.value

class Rep(Symbol):
    """ Repeat """
    def __init__(self, *symbols:SymbolLike, child_maker:Maker=None, min:Optional[int]=None, max:Optional[int]=None, maker:Maker=None):
        super().__init__(maker=maker)
        self.child_symbol = Seq(*symbols, maker=child_maker)
        self.min = min
        self.max = max

    def tryitr(self, chitr:SrcItr) -> Any:
        def _itr():
            for i in (itertools.count() if self.max is None else range(self.max)):
                try:
                    with chitr as _chitr:
                        yield self.child_symbol.tryitr(_chitr)
                except (SymbolTryFailed, StopSrcItr):
                    break
            if self.min is not None and i < self.min:
                raise SymbolTryFailed()
        return self._make(_itr())
        
    def _make(self, vitr:Iterator) -> Any:
        """ Make a value from the processed child values
            (Override)
        """
        return self.make(vitr)

class RepStr(StrMaker, Rep):
    def __init__(self, *symbols:SymbolLike, min:Optional[int]=1, max:Optional[int]=None, maker:Maker=None) -> None:
        super().__init__(*symbols, min=min, max=max, maker=maker)

class Opt(Rep):
    """ Optional """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        super().__init__(*symbols, max=1, maker=maker)

class IgnoreOpt(Opt, IgnoreRes):
    """ Optioal (ignore) """

class OR(Symbol):
    """ OR """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        super().__init__(maker=maker)
        self.symbols = list(map(to_symbol, symbols))

    def tryitr(self, chitr:SrcItr) -> Any:
        for symbol in self.symbols:
            try:
                with chitr as _chitr:
                    return symbol.tryitr(_chitr)
            except (SymbolTryFailed, StopSrcItr):
                pass
        raise SymbolTryFailed()

class Chain(Seq):
    """ Chain sequences """
    def _make(self, seq_res:Iterator) -> Any:
        return self.make(itertools.chain.from_iterable(v if isinstance(v, tuple) else (v,) for v in seq_res))

class ChainChars(Seq):
    """ Chain characters """
    def _make(self, seq_res:Iterator) -> Any:
        return self.make(''.join(self._to_str(v) for v in seq_res))

    @classmethod
    def _to_str(cls, v) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, tuple):
            return ''.join(cls._to_str(_v) for _v in v)
        raise TypeError()

class RepSep(Seq):
    """ Repeat with separator """
    def __init__(self, *symbols:Symbol, sep:SymbolLike, maker:Maker=None):
        val = symbols[0] if len(symbols) == 1 else Seq(*symbols)
        super().__init__(Chain(Rep(val, sep), Opt(val), maker=maker))
