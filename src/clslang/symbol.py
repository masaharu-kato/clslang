"""
    Definitions of essential Symbol classes
"""
import itertools
import sys
from abc import abstractclassmethod, abstractmethod, abstractproperty
from typing import Any, Callable, Dict, Generic, Hashable, Iterable, Iterator, List, Optional, Set, Tuple, Type, TypeVar, Union

from clslang.srcitr import SrcItr, StopSrcItr # type: ignore

IS_DEBUG = False

# DictKeyVals = Tuple[Tuple, Tuple[Any, Any]]
T = TypeVar('T')
CT = TypeVar('CT') # Char type

CharType = Union[int, str]
CharSeq = Union[bytes, str]
Maker = Optional[Callable[[Any], Any]]

class _UnspecifiedType:
    """ Unspecified type """

# A value which means `unspecified` (Distinguish from the python `None`)
Unspecified = _UnspecifiedType() 


class SymbolTryFailed(Exception):
    """ Symbol Try Failed Exception """

class NotAllCharsUsed(Exception):
    """ Not all given string used Exception """

class SymbolABC():
    """ Symbol ABC """
    def __init__(self):
        self._debug_indent_lv = 0

    @abstractmethod
    def itr_for_try(self, chitr:SrcItr) -> Iterator:
        """ Process values """
        raise NotImplementedError()

    @abstractmethod
    def tryitr(self, valitr:Iterator) -> Iterator:
        """ Parse values
            (If needed, return result values)
        """
        raise NotImplementedError()

    def trystr(self, chseq:Iterable, *, use_all: bool=True) -> Any:
        """ Parse a given sequence (string or bytes)
            If use_all options is True (default),
            assumes all characters on the sequence are used for parsing
        """
        res = tuple(self.tryitr(srcitr := SrcItr(chseq)))[0]
        if use_all and not srcitr.is_eof():
            raise NotAllCharsUsed('Not all characters used on %s' % repr(srcitr))
        return res

    def debug(self, *args, **kwargs):
        """ Print a debug output """
        if IS_DEBUG:
            print(*([' '] * self._debug_indent_lv), *args, **kwargs, file=sys.stderr)

    # def debug_indent(self):
    #     self._debug_indent_lv += 1

    # def debug_unindent(self):
    #     if self._debug_indent_lv > 0:
    #         self._debug_indent_lv -= 1


SymbolLike = Union[SymbolABC, tuple, bytes, str]

def to_symbol(symbol: SymbolLike) -> SymbolABC:
    """ Make a Symbol class from a symbol-like value """
    if isinstance(symbol, SymbolABC):
        return symbol
    if isinstance(symbol, tuple):
        return Seq(*symbol)
    if isinstance(symbol, str):
        if len(symbol) == 1:
            return Char(symbol[0])
        return Str(symbol)
    if isinstance(symbol, bytes):
        if len(symbol) == 1:
            return Char(symbol[0:1])
        return Str(symbol)
    raise TypeError(type(symbol))

class ResSymbolABC(SymbolABC):
    """ Symbol which returns result(s) """
    def __init__(self, *, maker: Maker):
        SymbolABC.__init__(self)
        self.maker = maker

    def tryitr(self, valitr: Iterator) -> Iterator:
        """ Process value-iterator (Override, Final) """
        return self.make_from_itr(self.itr_for_try(valitr))
        
    @abstractmethod
    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ Make a result from value-iterator (abstract) """
        raise NotImplementedError()

class OneResSymbol(ResSymbolABC):
    """ Symbol which returns just one result """
    def preprocess_one_valitr(self, valitr: Iterator) -> Any:
        """ Prepare a value for `make_from_itr` (default implementation) """
        return list(valitr)[0]

    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ Make a result from value-iterator (Final) """
        _valitr = self.preprocess_one_valitr(valitr)
        if self.maker is None:
            yield _valitr
        else:
            yield self.maker(_valitr)

class MultiResSymbol(ResSymbolABC):
    """ Normal symbol ABC
        Returns a value created by `maker` argument
        Each values are given for the `maker` arguments
    """
    def preprocess_multi_valitr(self, valitr: Iterator) -> Iterator:
        """ Prepare a value for `make_from_itr` (default implementation) """
        return valitr

    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ Make a result from value-iterator (Final) """
        _valitr = self.preprocess_multi_valitr(valitr)
        if self.maker is None:
            yield tuple(_valitr)
        else:
            yield self.maker(*_valitr) # Give as arguments

class ManyResSymbol(MultiResSymbol):
    """ Normal symbol ABC
        Returns a sequenced value created by `maker` argument
        Iterator of values is given to the `maker` argument
    """
    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ Make a result from value-iterator (Final) """
        _valitr = self.preprocess_multi_valitr(valitr)
        if self.maker is None:
            yield tuple(_valitr) # Yield a iterator directly?
        else:
            yield self.maker(_valitr)

class AnyTypeResSymbol(OneResSymbol, MultiResSymbol):
    """ Symbol which returns any type of result(s) """
    @abstractproperty
    def is_no_res(self) -> bool:
        """ Returns if make no values or not """
        raise NotImplementedError()

    @abstractproperty
    def is_one_res(self) -> bool:
        """ Returns if make a one value or not """
        raise NotImplementedError()
    
    def tryitr(self, valitr: Iterator) -> Iterator:
        """ Process value-iterator (Override) """
        if self.is_no_res:
            yield from NoResSymbol.tryitr(self, valitr)
        else:
            yield from ResSymbolABC.tryitr(self, valitr)

    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ Make a result from values-iterator (Final) """
        if self.is_one_res:
            yield from OneResSymbol.make_from_itr(self, valitr)
        else:
            yield from MultiResSymbol.make_from_itr(self, valitr)

class NoResSymbol(SymbolABC):
    """ Symbol: Ignore on results
        (Returns no value)
    """
    def tryitr(self, valitr: Iterator) -> Iterator:
        """ Process value-iterator (Override, Final) """
        _ = list(self.itr_for_try(valitr))
        yield from () # Returns nothing

class CharABC(SymbolABC):
    """ Single character """
    @abstractmethod
    def is_valid_char(self, ch:CharType) -> bool:
        """ Returns if a character is valid """
        raise NotImplementedError()

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
        raise NotImplementedError()

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
        CharWithEscapeABC.__init__(self)
        self.escape_char = escape_char

    def is_escape_char(self, ch: CharType) -> bool:
        return ch == self.escape_char

class CharMixinABC():
    """ Symbol which requires character(s) in the __init__ """
    @abstractmethod
    def is_bytes(self) -> bool:
        """ Returns whether the self character(s) are bytes """

class OneCharMixin(CharMixinABC):
    """ Symbol which requires one character in the __init__ """
    def __init__(self, ch: CharType) -> None:
        CharMixinABC.__init__(self)
        self.ch = ch[0] if isinstance(ch, bytes) else ch

    def is_bytes(self) -> bool:
        """ Returns whether the self character(s) are bytes """
        return isinstance(self.ch, int)

class OneCharABC(CharABC, OneCharMixin):
    """ One Char ABC """
    def __init__(self, ch:CharType) -> None:
        CharABC.__init__(self)
        OneCharMixin.__init__(self, ch)

    def is_valid_char(self, ch:CharType) -> bool:
        """ Check a given character is a valid on the self symbol (Override) """
        return ch == self.ch

class Char(OneCharABC, NoResSymbol):
    """ Character (Ignored in results) """

    def __repr__(self) -> str:
        return '<Char:%s>' % self.ch

class ResCharABC(CharABC, OneResSymbol):
    """ Symbol which returns a character """
    def __init__(self, maker:Maker=None) -> None:
        CharABC.__init__(self)
        OneResSymbol.__init__(self, maker=maker)

class ExplChar(OneCharABC, ResCharABC):
    """ Character (Explicitly returns a character) """
    def __init__(self, ch:CharType, *, maker:Maker=None) -> None:
        OneCharABC.__init__(self, ch)
        ResCharABC.__init__(self, maker=maker)

    def __repr__(self) -> str:
        return '<ExplChar:%s>' % self.ch

class CharNot(ResCharABC, OneCharMixin):
    """ All characters except a specific character """
    def __init__(self, ch:CharType, *, maker:Maker=None) -> None:
        ResCharABC.__init__(self, maker=maker)
        OneCharMixin.__init__(self, ch)

    def is_valid_char(self, ch:CharType) -> bool:
        return ch != self.ch

    def __repr__(self) -> str:
        return '<CharNot:%s>' % self.ch

class CharNotWithEscape(CharWithSingleEscapeABC, CharNot):
    """ All characters except a specific character with escapes """
    def __init__(self, ch: CharType, escape_char: CharType, maker:Maker=None) -> None:
        CharWithSingleEscapeABC.__init__(self, escape_char=escape_char)
        CharNot.__init__(self, ch, maker=maker)

    def __repr__(self) -> str:
        return '<CharNotWithEscape:%s>' % self.ch

class CharSetMixin(CharMixinABC):
    """ Symbol which requires characters in the __init__ """
    def __init__(self, *chs: CharType) -> None:
        self.chset = set(chs)
        self._is_bytes = any(isinstance(ch, int) for ch in chs)

    def is_bytes(self) -> bool:
        return self._is_bytes

class Chars(ResCharABC, CharSetMixin):
    """ Specific set of characters """
    def __init__(self, *chs:CharType, maker:Maker=None) -> None:
        ResCharABC.__init__(self, maker=maker)
        CharSetMixin.__init__(self, *chs)

    def is_valid_char(self, ch:CharType) -> bool:
        return ch in self.chset

    def __repr__(self) -> str:
        return '<Chars:%s>' % '|'.join([str(bytes([ch])) if isinstance(ch, int) else ch for ch in self.chset])

class CharsNot(ResCharABC, CharSetMixin):
    """ All characters except specific set of characters """
    def __init__(self, *chs:CharType, maker:Maker=None) -> None:
        ResCharABC.__init__(self, maker=maker)
        CharSetMixin.__init__(self, *chs)

    def is_valid_char(self, ch:CharType) -> bool:
        return ch not in self.chset

    def __repr__(self) -> str:
        return '<Chars:%s>' % '|'.join([str(bytes([ch])) if isinstance(ch, int) else ch for ch in self.chset])

class CharsNotWithEscape(CharWithSingleEscapeABC, CharsNot):
    """ All characters except specific set of characters with escape sequences """
    def __init__(self, *chs: CharType, escape_char: CharType, maker:Maker=None) -> None:
        CharWithSingleEscapeABC.__init__(self, escape_char=escape_char)
        CharsNot.__init__(self, *chs, maker=maker)

    def __repr__(self) -> str:
        return '<CharsNotWithEscape:%s>' % '|'.join(self.chset)

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
        SymbolABC.__init__(self)
        self.symbols = list(map(to_symbol, symbols))
    
    def itr_for_try(self, chitr:SrcItr) -> Iterator:
        for i, sym in enumerate(self.symbols):
            self.debug('Seq: symbol #%d %s' % (i, sym))
            # self.debug_indent()
            yield from sym.tryitr(chitr)
            # self.debug_unindent()

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

class Except(OneResSymbol):
    """ Symbol except a specific symbol """
    def __init__(self, sym_base: SymbolLike, sym_except: SymbolLike):
        OneResSymbol.__init__(self, maker=None)
        self.sym_base   = to_symbol(sym_base)
        self.sym_except = to_symbol(sym_except)

    def itr_for_try(self, chitr: SrcItr) -> Iterator:
        try:
            with chitr as _chitr:
                _ = list(self.sym_except.tryitr(_chitr))
        except SymbolTryFailed:
            yield from self.sym_base.tryitr(chitr)
        else:
            raise SymbolTryFailed('Except-Symbol detected.')

class StrMaker(OneResSymbol):
    """ Symbol which makes string """
    def __init__(self, *, is_bytes: bool, maker: Maker):
        OneResSymbol.__init__(self, maker=maker)
        self.is_bytes = is_bytes

    def preprocess_one_valitr(self, valitr: Iterator) -> Any:
        return ''.join(valitr) if not self.is_bytes else bytes(valitr)

class StrABC(SeqABC):
    """ String (Sequence of characters) ABC """
    def __init__(self, chseq: CharSeq):
        SeqABC.__init__(self, *(ExplChar(ch) for ch in chseq))

class Str(StrABC, NoResSymbol):
    """ String (Ignored in results) """
    def __init__(self, chseq: CharSeq):
        StrABC.__init__(self, chseq)
        NoResSymbol.__init__(self)

class ExplStr(StrABC, StrMaker):
    """ String (Shown in results) """
    def __init__(self, chseq: CharSeq, maker: Maker=None):
        StrABC.__init__(self, chseq)
        StrMaker.__init__(self, is_bytes=isinstance(chseq, bytes), maker=maker)

class CustomStr(ExplStr):
    """ String (Ignored in results) """
    def __init__(self, chseq: CharSeq, *, maker: Maker):
        ExplStr.__init__(self, chseq, maker=maker)

class Keyword(CustomStr):
    """ String (Ignored in results) """
    def __init__(self, chseq: CharSeq, *, value: Any):
        """
            chseq: The string to find
            value: The The specific value which corresponds to `chseq`
                   (use `str` to return the original string)
        """
        CustomStr.__init__(self, chseq, maker=lambda _: value)

class RepABC(SymbolABC):
    """ Repeat symbols ABC """
    def __init__(self, *symbols:SymbolLike, child_maker:Maker=None, nmin:Optional[int]=None, nmax:Optional[int]=None):
        SymbolABC.__init__(self)
        self.child_symbol = Seq(*symbols, maker=child_maker)
        self.min = nmin
        self.max = nmax

    def itr_for_try(self, chitr:SrcItr) -> Iterator:
        i = 0
        for i in itertools.count() if self.max is None else range(self.max):
            try:
                with chitr as _chitr:
                    yield from self.child_symbol.tryitr(_chitr)
            except (SymbolTryFailed, StopSrcItr):
                break
        if self.min is not None and i < self.min:
            raise SymbolTryFailed()

class IgnoreRep(RepABC, NoResSymbol):
    """ Repeat symbols (Ignore results) """
    def __init__(self, *symbols: SymbolLike, child_maker: Maker = None, nmin: Optional[int] = None, nmax: Optional[int] = None):
        RepABC.__init__(self, *symbols, child_maker=child_maker, nmin=nmin, nmax=nmax)
        NoResSymbol.__init__(self)

class Rep(RepABC, ManyResSymbol):
    """ Repeat symbols """
    def __init__(self, *symbols: SymbolLike, child_maker: Maker = None, nmin: Optional[int] = None, nmax: Optional[int] = None, maker: Maker = None):
        RepABC.__init__(self, *symbols, child_maker=child_maker, nmin=nmin, nmax=nmax)
        ManyResSymbol.__init__(self, maker=maker)

class RepStr(RepABC, StrMaker):
    """ Repeat symbols and make a result as a string """
    def __init__(self, *symbols: SymbolLike, nmin: Optional[int]=1, nmax: Optional[int]=None, maker: Maker=None) -> None:
        RepABC.__init__(self, *symbols, nmin=nmin, nmax=nmax)
        StrMaker.__init__(self, is_bytes=False, maker=maker)

class RepBytes(RepABC, StrMaker):
    """ Repeat symbols and make a result as a bytes """
    def __init__(self, *symbols: SymbolLike, nmin: Optional[int]=1, nmax: Optional[int]=None, maker: Maker=None) -> None:
        RepABC.__init__(self, *symbols, nmin=nmin, nmax=nmax)
        StrMaker.__init__(self, is_bytes=True, maker=maker)

class Opt(Rep):
    """ Optional symbols """
    def __init__(self, *symbols: SymbolLike, child_maker: Maker = None, maker: Maker = None, none_val = Unspecified):
        Rep.__init__(self, *symbols, nmax=1, child_maker=child_maker, maker=maker)
        self.none_val = none_val
        
    def make_from_itr(self, valitr: Iterator) -> Iterator:
        """ Make a result from value-iterator (Override) """
        _valitr = self.preprocess_multi_valitr(valitr)
        if self.maker is None:
            if self.none_val is Unspecified:
                yield tuple(_valitr) # Yield a iterator directly?
            else:
                if _args := tuple(_valitr):
                    assert len(_args) == 1
                    yield _args[0]
                else:
                    yield self.none_val
        else:
            yield self.maker(_valitr)

class IgnoreOpt(IgnoreRep):
    """ Optioal (ignore) """
    def __init__(self, *symbols: SymbolLike):
        IgnoreRep.__init__(self, *symbols, nmax=1)

class OR(OneResSymbol):
    """ OR """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        OneResSymbol.__init__(self, maker=maker)
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
        self.symbols.append(to_symbol(symbol))

class Chain(SeqABC, ManyResSymbol):
    """ Chain sequences """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        SeqABC.__init__(self, *symbols)
        ManyResSymbol.__init__(self, maker=maker)

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
        if isinstance(v, (Iterator, tuple)):
            return ''.join(cls._to_str(_v) for _v in v)
        raise TypeError(v)

class ChainBytes(SeqABC, OneResSymbol):
    """ Chain characters """
    def __init__(self, *symbols:SymbolLike, maker:Maker=None):
        SeqABC.__init__(self, *symbols)
        OneResSymbol.__init__(self, maker=maker)

    def preprocess_one_valitr(self, valitr: Iterator) -> Any:
        return b''.join(self._to_bytes(v) for v in valitr)

    @classmethod
    def _to_bytes(cls, v) -> bytes:
        if isinstance(v, Iterator):
            return bytes(v)
        if isinstance(v, int):
            return bytes([v])
        if isinstance(v, bytes):
            return v
        if isinstance(v, tuple):
            return b''.join(cls._to_bytes(_v) for _v in v)
        raise TypeError(v)

class RepSep(Seq):
    """ Repeat with separator """
    def __init__(self, *symbols:SymbolLike, sep:SymbolLike, maker:Maker=None):
        val = symbols[0] if len(symbols) == 1 else Seq(*symbols)
        Seq.__init__(self, Chain(Rep(val, sep), Opt(val), maker=maker))
