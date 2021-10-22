
import itertools
import copy
import enum
from abc import abstractclassmethod, abstractmethod, abstractproperty
from typing import Any, Callable, Dict, Generic, Hashable, Iterable, Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union

from clslang.srcitr import SrcItr, StopSrcItr # type: ignore

# DictKeyVals = Tuple[Tuple, Tuple[Any, Any]]
T = TypeVar('T')
CT = TypeVar('CT') # Char type

CharType = str
CharSeq = str
Maker = Optional[Callable[[Any], Any]]

class SymbolTryFailed(Exception):
    """ Symbol Try Failed Exception """

class NotAllCharsUsed(Exception):
    """ Not all given string used Exception """

class SymbolABC():
    """ Symbol ABC """
    @abstractmethod
    def itr_for_try(self, chitr:SrcItr) -> Iterator:
        """ Process values """
        raise NotImplementedError()

    @abstractmethod
    def tryitr(self, valitr:Iterator) -> Iterator:
        """ Process values
            (If needed, return result values)
        """
        raise NotImplementedError()

    def trystr(self, chseq:Iterable, *, all:bool=True) -> Any:
        res = tuple(self.tryitr(srcitr := SrcItr(chseq)))[0]
        # print('is_eof: %d' % srcitr.is_eof())
        # if all and not srcitr.is_eof():
        #   raise NotAllCharsUsed('Not all characters used on %s' % repr(srcitr))
        return res

SymbolLike = Union[SymbolABC, tuple, str]

def to_symbol(symbol:SymbolLike) -> SymbolABC:
    if isinstance(symbol, SymbolABC):
        return symbol
    if isinstance(symbol, tuple):
        return Seq(*symbol)
    if isinstance(symbol, str):
        if len(symbol) == 1:
            return Char(symbol[0])
        return Str(symbol)
    raise TypeError()

class ResSymbolABC(SymbolABC):
    """ """
    def __init__(self, *, maker:Maker=None):
        self.maker = maker

    def tryitr(self, valitr: Iterator) -> Iterator:
        """ (Override, Final) """
        return self.make_from_itr(self.itr_for_try(valitr))
        
    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ """
        raise NotImplementedError()

class OneResSymbol(ResSymbolABC):
    def preprocess_one_valitr(self, valitr: Iterator) -> Any:
        """ Prepare a value for `make_from_itr` (default implementation) """
        return list(valitr)[0]

    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ (Final) """
        _valitr = self.preprocess_one_valitr(valitr)
        if self.maker is None:
            yield _valitr
        else:
            yield self.maker(_valitr)

class MultiResSymbol(ResSymbolABC):
    """ Normal symbol ABC
        (Returns a value)
    """
    def preprocess_multi_valitr(self, valitr: Iterator) -> Iterator:
        """ Prepare a value for `make_from_itr` (default implementation) """
        return valitr

    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ (Final) """
        _valitr = self.preprocess_multi_valitr(valitr)
        if self.maker is None:
            yield tuple(_valitr)
        else:
            yield self.maker(_valitr)

class AnyTypeResSymbol(OneResSymbol, MultiResSymbol):
    """ """
    @abstractproperty
    def is_no_res(self) -> bool:
        """ Returns if make no values or not """
        raise NotImplementedError()

    @abstractproperty
    def is_one_res(self) -> bool:
        """ Returns if make a one value or not """
        raise NotImplementedError()
    
    def tryitr(self, valitr: Iterator) -> Iterator:
        if self.is_no_res:
            yield from NoResSymbol.tryitr(self, valitr)
        else:
            yield from ResSymbolABC.tryitr(self, valitr)

    def make_from_itr(self, val:Iterator) -> Iterator:
        if self.is_one_res:
            yield from OneResSymbol.make_from_itr(self, val)
        else:
            yield from MultiResSymbol.make_from_itr(self, val)

class NoResSymbol(SymbolABC):
    """ Symbol: Ignore on results
        (Returns no value)
    """
    def tryitr(self, valitr: Iterator) -> Iterator:
        """ (Override, Final) """
        _ = list(self.itr_for_try(valitr))
        yield from () # Returns nothing

class CharABC(SymbolABC):
    """ Single character """
    @abstractmethod
    def is_valid_char(self, ch:CharType) -> bool:
        """ Returns if a character is valid """

    def itr_for_try(self, chitr: SrcItr) -> Iterator:
        ch = next(chitr)
        if self.is_valid_char(ch):
            yield ch
            return
        raise SymbolTryFailed()

class CharWithEscapeABC(CharABC):
    """ Character with escape """

    @abstractmethod
    def is_escape_char(self, ch:CharType) -> bool:
        """ Returns if a character is the begin of escape """

    def itr_for_try(self, chitr: SrcItr) -> Iterator:
        ch = next(chitr)
        if self.is_escape_char(ch):
            yield next(chitr)
            return
        if self.is_valid_char(ch):
            yield ch
            return
        raise SymbolTryFailed()

class CharWithSingleEscapeABC(CharWithEscapeABC):
    """ Character with escape """
    def __init__(self, *, escape_char) -> None:
        super().__init__()
        self.escape_char = escape_char

    def is_escape_char(self, ch: CharType) -> bool:
        return ch == self.escape_char

class OneCharABC(CharABC):
    """ One Char ABC """
    def __init__(self, ch:CharType) -> None:
        super().__init__()
        self.ch = ch

    def is_valid_char(self, ch:CharType) -> bool:
        return ch == self.ch

class Char(OneCharABC, NoResSymbol):
    """ Char (Ignored in results) """

class ResCharABC(CharABC, OneResSymbol):
    def __init__(self, maker:Maker=None) -> None:
        CharABC.__init__(self)
        OneResSymbol.__init__(self, maker=maker)

class ExplChar(OneCharABC, ResCharABC):
    """ Char (Explicit) """
    def __init__(self, ch:CharType, *, maker:Maker=None) -> None:
        OneCharABC.__init__(self, ch)
        ResCharABC.__init__(self, maker=maker)

class CharNot(ResCharABC):
    def __init__(self, ch:CharType, *, maker:Maker=None) -> None:
        super().__init__(maker=maker)
        self.ch = ch

    def is_valid_char(self, ch:CharType) -> bool:
        return ch != self.ch

class CharNotWithEscape(CharWithSingleEscapeABC, CharNot):
    def __init__(self, ch: CharType, escape_char: CharType, maker:Maker=None) -> None:
        CharWithSingleEscapeABC.__init__(self, escape_char)
        CharNot.__init__(self, ch, maker=maker)

class Chars(ResCharABC):
    def __init__(self, *chs:CharType, maker:Maker=None) -> None:
        super().__init__(maker=maker)
        self.chset = set(chs)

    def is_valid_char(self, ch:CharType) -> bool:
        return ch in self.chset

class CharsNot(ResCharABC):
    def __init__(self, *chs:CharType, maker:Maker=None) -> None:
        super().__init__(maker=maker)
        self.chset = set(chs)

    def is_valid_char(self, ch:CharType) -> bool:
        return ch not in self.chset

class CharsNotWithEscape(CharWithSingleEscapeABC, CharsNot):
    def __init__(self, *chs: CharType, escape_char: CharType, maker:Maker=None) -> None:
        CharWithSingleEscapeABC.__init__(self, escape_char=escape_char)
        CharsNot.__init__(self, *chs, maker=maker)

# class CharRange(CharABC):
#     def __init__(self, ch_first:CharType, ch_last:CharType) -> None:
#         self.ch_first = int(ch_first)
#         self.ch_last  = int(ch_last)

#     def is_valid_char(self, ch:CharType) -> bool:
#         return self.ch_first <= int(ch) and int(ch) <= self.ch_last 

# DigitChars = CharRange('0', '9')
# UpperAlphaChars = CharRange('A', 'Z')
# LowerAlphaChars = CharRange('a', 'z')

class SeqABC(SymbolABC):
    """ Sequence of symbols (ABC) """
    def __init__(self, *symbols:SymbolLike):
        super().__init__()
        self.symbols = list(map(to_symbol, symbols))
    
    def itr_for_try(self, chitr:SrcItr) -> Iterator:
        for sym in self.symbols:
            yield from sym.tryitr(chitr)

class Seq(SeqABC, AnyTypeResSymbol):
    """ Sequence of symbols """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        SeqABC.__init__(self, *symbols)
        AnyTypeResSymbol.__init__(self, maker=maker)
        _nsyms = len(list(filter(
            lambda sym: not isinstance(sym, NoResSymbol) and not (isinstance(sym, AnyTypeResSymbol) and sym.is_no_res),
            self.symbols
        )))
        self._is_no_res = (_nsyms == 0)
        self._is_one_res = (_nsyms == 1)

    @property
    def is_no_res(self) -> bool:
        return self._is_no_res

    @property
    def is_one_res(self) -> bool:
        return self._is_one_res

class MultiSeq(SeqABC, MultiResSymbol):
    """ Sequence of symbols (Returns multi values) """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        SeqABC.__init__(self, *symbols)
        MultiResSymbol.__init__(self, maker=maker)

class Ignore(NoResSymbol, Seq):
    """ Sequences to ignore """

class StrMaker(OneResSymbol):
    """ Symbol which makes string """
    def preprocess_one_valitr(self, valitr: Iterator) -> Any:
        return ''.join(valitr)

class ExplStr(StrMaker, SeqABC):
    """ String (Explicit) """
    def __init__(self, chseq:str):
        StrMaker.__init__(self)
        SeqABC.__init__(self, *(ExplChar(ch) for ch in chseq))

class Str(ExplStr, OneResSymbol):
    """ String (Ignored in results) """
    def __init__(self, chseq:str, *, value:Any=str):
        """
            chseq: The string to find
            value: The The specific value which corresponds to `chseq`
                   (use `str` to return the original string)
        """
        ExplStr.__init__(self, chseq)
        OneResSymbol.__init__(self, maker=self._maker)
        self.value = value

    def _maker(self, text:Any) -> Any:
        if self.value is str:
            return text
        return self.value

class RepABC(SymbolABC):
    """ Repeat """
    def __init__(self, *symbols:SymbolLike, child_maker:Maker=None, min:Optional[int]=None, max:Optional[int]=None):
        super().__init__()
        self.child_symbol = Seq(*symbols, maker=child_maker)
        self.min = min
        self.max = max

    def itr_for_try(self, chitr:SrcItr) -> Iterator:
        for i in (itertools.count() if self.max is None else range(self.max)):
            try:
                with chitr as _chitr:
                    yield from self.child_symbol.tryitr(_chitr)
            except (SymbolTryFailed, StopSrcItr):
                break
        if self.min is not None and i < self.min:
            raise SymbolTryFailed()

class IgnoreRep(RepABC, NoResSymbol):
    def __init__(self, *symbols: SymbolLike, child_maker: Maker = None, min: Optional[int] = None, max: Optional[int] = None):
        RepABC.__init__(self, *symbols, child_maker=child_maker, min=min, max=max)
        NoResSymbol.__init__(self)

class Rep(RepABC, MultiResSymbol):
    def __init__(self, *symbols: SymbolLike, child_maker: Maker = None, min: Optional[int] = None, max: Optional[int] = None, maker: Maker = None):
        RepABC.__init__(self, *symbols, child_maker=child_maker, min=min, max=max)
        MultiResSymbol.__init__(self, maker=maker)

class RepStr(RepABC, StrMaker):
    def __init__(self, *symbols:SymbolLike, min:Optional[int]=1, max:Optional[int]=None, maker:Maker=None) -> None:
        RepABC.__init__(self, *symbols, min=min, max=max)
        StrMaker.__init__(self, maker=maker)

class Opt(Rep):
    """ Optional """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        super().__init__(*symbols, max=1, maker=maker)

class IgnoreOpt(IgnoreRep):
    """ Optioal (ignore) """
    def __init__(self, *symbols:SymbolLike):
        super().__init__(*symbols, max=1)

class OR(OneResSymbol):
    """ OR """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        super().__init__(maker=maker)
        self.symbols = list(map(to_symbol, symbols))

    def itr_for_try(self, chitr: SrcItr) -> Iterator:
        for symbol in self.symbols:
            try:
                with chitr as _chitr:
                    yield from symbol.tryitr(_chitr)
                    return
            except (SymbolTryFailed, StopSrcItr):
                pass
        raise SymbolTryFailed()
        
    def add(self, symbol:SymbolLike):
        """ Add a new symbol to this sequence """
        self.symbols.append(sym := to_symbol(symbol))

class Chain(SeqABC, MultiResSymbol):
    """ Chain sequences """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        SeqABC.__init__(self, *symbols)
        MultiResSymbol.__init__(self, maker=maker)

    def preprocess_multi_valitr(self, valitr: Iterator) -> Any:
        return itertools.chain.from_iterable(valitr)

class ChainChars(SeqABC, OneResSymbol):
    """ Chain characters """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        SeqABC.__init__(self, *symbols)
        OneResSymbol.__init__(self, maker=maker)

    def preprocess_one_valitr(self, valitr: Iterator) -> Any:
        return ''.join(self._to_str(v) for v in valitr)

    @classmethod
    def _to_str(cls, v) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, tuple):
            return ''.join(cls._to_str(_v) for _v in v)
        raise TypeError()

class RepSep(Seq):
    """ Repeat with separator """
    def __init__(self, *symbols:SymbolLike, sep:SymbolLike, maker:Maker=None):
        val = symbols[0] if len(symbols) == 1 else Seq(*symbols)
        super().__init__(Chain(Rep(val, sep), Opt(val), maker=maker))
