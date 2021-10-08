
import itertools
import copy
from abc import abstractmethod
from typing import Any, Callable, Dict, Generic, Hashable, Iterable, Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union

from clslang.srcitr import SrcItr, StopSrcItr

# DictKeyVals = Tuple[Tuple, Tuple[Any, Any]]
T = TypeVar('T')
CT = TypeVar('CT') # Char type

def flat_tuple_dict(tpl:Tuple[Optional[Tuple], Tuple[Hashable, Any]]) -> Dict[Hashable, List[Any]]:
    if not tpl:
        return {}
    parent, (key, value) = tpl
    cdict = flat_tuple_dict(parent) if parent is not None else {}
    if key not in cdict:
        cdict[key] = []
    cdict[key].append(value)
    return cdict

CharType = int
Maker = Callable[[Iterator], Any]

class SymbolTryFailed(Exception):
    """ Symbol Try Failed Exception """

class IgnoreRes:
    """ Symbol: Ignore on results """

class Symbol():
    """ Symbol ABC """
    def __init__(self, *, maker:Maker):
        self.maker = maker

    def make(self, itr:Iterator):
        return self.maker(itr)

    @abstractmethod
    def tryitr(self, chitr:SrcItr) -> Any:
        raise NotImplementedError()

    def trystr(self, chseq:Iterable) -> Any:
        return self.tryitr(SrcItr(chseq))


class CharABC(Symbol):
    """ Single character """
    @abstractmethod
    def is_valid_char(ch:CharType) -> bool:
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

SymbolLike = Union[Symbol, str]
WSType = Optional[SymbolLike]

class Seq(Symbol):
    """ Sequence of symbols """
    def __init__(self, *symbols:SymbolLike, ws:WSType=None, maker:Maker=tuple):
        # assert all(isinstance(symbol, Symbol) for symbol in symbols), 'Invalid arguments (Symbol expected)'
        super().__init__(maker=maker)
        self.symbols = []
        _ws = self.to_ws_symbol(ws) if ws is not None else None
        for i, sym in enumerate(symbols):
            if _ws is not None and i > 0:
                self.symbols.append(_ws)
            self.symbols.append(self.to_symbol(sym))
        self.is_one_symbol = len([sym for sym in self.symbols if not isinstance(sym, IgnoreRes)]) == 1

    @staticmethod
    def to_symbol(symbol:SymbolLike) -> Symbol:
        if isinstance(symbol, Symbol):
            return symbol
        if isinstance(symbol, str):
            if len(symbol) == 1:
                return Char(symbol[0])
            return Str(symbol)
        raise TypeError()

    @staticmethod
    def to_ws_symbol(symbol:SymbolLike) -> Symbol:
        if isinstance(symbol, Symbol):
            return symbol
        if isinstance(symbol, str):
            if len(symbol) == 1:
                return IgnoreOpt(Char(symbol[0]))
            return IgnoreOpt(RepStr(Chars(*(ch for ch in symbol))))
        raise TypeError()
    
    def makeone(self, val) -> Any:
        return val

    def _makeseq(self, vitr:Iterator) -> Any:
        return self.make(vitr)

    def _make(self, vitr:Iterator) -> Any:
        if self.is_one_symbol:
            vals = tuple(vitr)
            return self.makeone(vals[0])
        return self._makeseq(vitr)

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

class ExplStr(Seq):
    """ String (Explicit) """
    def __init__(self, chseq:str):
        super().__init__(*(ExplChar(ch) for ch in chseq))

    def make(self, seq_res:Iterator) -> str:
        return ''.join(seq_res)

class Str(ExplStr, IgnoreRes):
    """ String (Ignored in results) """
    def __init__(self, chseq:str, *, value:Any=str):
        super().__init__(chseq)
        self.value = value

    def make(self, itr:Iterator):
        if self.value is str:
            super().make(itr)
        _ = tuple(itr)
        return self.value

class Rep(Seq):
    """ Repeat """
    def __init__(self, *symbols:Symbol, min:Optional[int]=None, max:Optional[int]=None, ws:WSType=None, ws_elm:WSType=None, maker:Maker=tuple):
        super().__init__(*symbols, ws=ws_elm, maker=maker)
        self.min = min
        self.max = max
        self.ws_rep = self.to_ws_symbol(ws) if ws is not None else None

    def tryitr(self, chitr:SrcItr) -> Any:
        _super = super()
        def _itr():
            for i in (itertools.count() if self.max is None else range(self.max)):
                try:
                    with chitr as _chitr:
                        if self.ws_rep is not None:
                            _ = self.ws_rep.tryitr(_chitr)
                        yield _super.tryitr(_chitr)
                except (SymbolTryFailed, StopSrcItr):
                    break
            if self.min is not None and i < self.min:
                raise SymbolTryFailed()
        return self._makeseq(_itr())

class RepStr(Rep):
    def __init__(self, *symbols:Symbol, min:Optional[int]=1, max:Optional[int]=None, maker:Maker=tuple) -> None:
        super().__init__(*symbols, min=min, max=max, maker=maker)

    """ Repeat characters, get string """
    def make(self, seq_res:Iterator) -> str:
        return ''.join(seq_res)

class Opt(Rep):
    """ Optional """
    def __init__(self, *symbols:Symbol, ws_elm:WSType=None, maker:Maker=tuple):
        super().__init__(*symbols, max=1, ws_elm=ws_elm, maker=maker)

class IgnoreOpt(Opt, IgnoreRes):
    """ Optioal (ignore) """

class OR(Symbol):
    """ OR """
    def __init__(self, *symbols:Symbol, maker:Maker=tuple):
        super().__init__(maker=maker)
        self.symbols = list(symbols)

    def add(self, symbol:Symbol):
        self.symbols.append(symbol)

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
        return self._makeseq(itertools.chain.from_iterable(v if isinstance(v, tuple) else (v,) for v in seq_res))

class ChainChars(Seq):
    """ Chain characters """
    def _make(self, seq_res:Iterator) -> Any:
        return self.makeone(''.join(self._to_str(v) for v in seq_res))

    @classmethod
    def _to_str(cls, v) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, tuple):
            return ''.join(cls._to_str(_v) for _v in v)
        raise TypeError()

class RepSep(Seq):
    """ Repeat with separator """
    def __init__(self, *symbols:Symbol, sep:Symbol, ws:WSType=None, ws_elm:WSType=None, maker:Maker=tuple):
        val = symbols[0] if len(symbols) == 1 else Seq(*symbols)
        super().__init__(Chain(Rep(val, Char(sep), ws=ws, ws_elm=ws_elm), Opt(val, ws_elm=ws_elm), ws=ws, maker=maker))
