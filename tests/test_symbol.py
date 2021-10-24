"""
    Test parsings on the symbol classes
"""
from clslang.srcitr import StopSrcItr
from clslang.symbol import OR, AnyChar, Chain, CharNot, Chars, CharsNot, CharsNotWithEscape, ExplChar, ExplStr, NotAllCharsUsed, Opt, Rep, RepSep, RepStr, Seq, SymbolTryFailed, Char

import pytest

@pytest.mark.parametrize('ch', ['a', 'f', 'z', '1', '5', '0', '.'])
def test_char(ch):
    """ Test an explicit single character parsing """
    rule = ExplChar(ch)
    assert rule.trystr(ch) == ch
    with pytest.raises(SymbolTryFailed):
        rule.trystr('x')

@pytest.mark.parametrize('chseq, ngchseq', [
    ('a', 'bc'),
    ('piyopiyo', 'piyoopiyo'),
    ('b13f', 'b13abc'),
    ('104.25', 'xyzabc'),
    ('-3.2e13', 'hogefuga'),
])
def test_charseq(chseq, ngchseq):
    """ Test a sequence of explicit single characters parsing """
    rule = ExplStr(chseq)
    assert rule.trystr(chseq) == chseq
    with pytest.raises(SymbolTryFailed):
        rule.trystr('xyzxyz')
    with pytest.raises(SymbolTryFailed):
        rule.trystr(ngchseq)

@pytest.mark.parametrize('chseqs, ngchseqs', [
    (('true',), ('false', 'none', 'empty')),
    (('hoge', 'piyoyo', 'fugea'), ('xxyzz', 'vjzjd')),
    (('123bcza', '3242bscx'), ('21f2cvv', 'oge', 'va', '9999')),
])
def test_or_charseq(chseqs, ngchseqs):
    """ Test OR parsing """
    rule = OR(*(ExplStr(chseq) for chseq in chseqs))
    for ngchseq in ngchseqs:
        with pytest.raises(SymbolTryFailed):
            rule.trystr(ngchseq)
    for chseq in chseqs:
        assert rule.trystr(chseq) == chseq
    for ngchseq in ngchseqs:
        with pytest.raises(SymbolTryFailed):
            rule.trystr(ngchseq)

@pytest.mark.parametrize('bch, ech, contents', [
    ('(', ')', ('hoge', 'fugaa', 'piyopiyo')),
    ('[', ']', ('pugar', 'ba32v', 'piyoo')),
    ('{', '}', ('bd', '123', 'vw459vvsw3', 'pipo')),
])
def test_brackets(bch, ech, contents):
    """ Test a bracket and child-values parsing """
    rule = Seq(ExplChar(bch), RepStr(CharNot(ech)), ExplChar(ech))
    for content in contents:
        assert rule.trystr(bch + content + ech)[1] == content
        with pytest.raises((SymbolTryFailed, StopSrcItr)):
            rule.trystr(bch + content)
        with pytest.raises(SymbolTryFailed):
            rule.trystr(content + ech)

list_test_params = ('bch, ech, sep, cts', [
    ('(', ')', ',', ()),
    ('(', ')', ',', ('one',)),
    ('(', ')', ',', ('hoge', 'fugaa')),
    ('(', ')', ',', ('hoge', 'fugaae', 'piyopiii')),
    ('[', ']', ' ', ('poga', 'efa,f23', 'fee232f')),
    ('{', '}', ',', ('bd', '123', 'vw459vv', 'pipo')),
])

@pytest.mark.parametrize(*list_test_params)
def test_legacy_sep_list_expl(bch, ech, sep, cts):
    """ Test a legacy list expression which rejects a trailing comma """
    rule = Seq(ExplChar(bch), Rep(RepStr(CharsNot(sep, ech)), ExplChar(sep)), ExplChar(ech))
    assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == (bch, tuple((ct, sep) for ct in cts), ech)

@pytest.mark.parametrize(*list_test_params)
def test_legacy_list_expl(bch, ech, sep, cts):
    """ Test a legacy list expression which accepts a trailing comma """
    Val = RepStr(CharsNot(sep, ech))
    rule = Seq(ExplChar(bch), Rep(Val, ExplChar(sep)), Opt(Val), ExplChar(ech))
    if cts:
        *_cts, lastct = cts
        assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == (bch, tuple((ct, sep) for ct in cts), (), ech)
        assert rule.trystr(bch + sep.join(cts) + ech) == (bch, tuple((ct, sep) for ct in _cts), (lastct,), ech)
    else:
        assert rule.trystr(bch + ech) == (bch, (), (), ech)

@pytest.mark.parametrize(*list_test_params)
def test_legacy_sep_list(bch, ech, sep, cts):
    """ Test a legacy list expression without separators which rejects a trailing comma """
    rule = Seq(Char(bch), Rep(RepStr(CharsNot(sep, ech)), Char(sep)), Char(ech))
    assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == cts

@pytest.mark.parametrize(*list_test_params)
def test_legacy_list(bch, ech, sep, cts):
    """ Test a legacy list expression without separators which accepts a trailing comma """
    Val = RepStr(CharsNot(sep, ech))
    rule = Seq(Char(bch), Rep(Val, Char(sep)), Opt(Val), Char(ech))
    if cts:
        *_cts, lastct = cts
        _cts = tuple(_cts)
        assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == (cts, ())
        assert rule.trystr(bch + sep.join(cts) + ech) == (_cts, (lastct,))
    else:
        assert rule.trystr(bch + ech) == ((), ())

@pytest.mark.parametrize(*list_test_params)
def test_general_list(bch, ech, sep, cts):
    """ Test a general list (with basic symbol classes) """
    Val = RepStr(CharsNot(sep, ech))
    rule = Seq(bch, Chain(Rep(Val, sep), Opt(Val)), ech)
    assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == cts
    assert rule.trystr(bch + sep.join(cts) + ech) == cts

@pytest.mark.parametrize(*list_test_params)
def test_repsep_list(bch, ech, sep, cts):
    """ Test a general list (with RepSep symbol class) """
    rule = Seq(bch, RepSep(RepStr(CharsNot(sep, ech)), sep=sep), ech)
    assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == cts
    assert rule.trystr(bch + sep.join(cts) + ech) == cts

@pytest.mark.parametrize(*list_test_params)
def test_py_list(bch, ech, sep, cts):
    """ Test a general list and make a python list """
    rule = Seq(bch, RepSep(RepStr(CharsNot(sep, ech)), sep=sep, maker=list), ech)
    assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == list(cts)
    assert rule.trystr(bch + sep.join(cts) + ech) == list(cts)
    
@pytest.mark.parametrize(*list_test_params)
def test_py_list_with_end(bch, ech, sep, cts):
    """ Test a general list and make a python list """
    rule = Seq(bch, RepSep(RepStr(AnyChar(), end=Chars(sep, ech)), sep=sep, maker=list), ech)
    assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == list(cts)
    assert rule.trystr(bch + sep.join(cts) + ech) == list(cts)

list_test_escaped_params = ('bch, ech, sep, esc_ch, cts, res_cts', [
    ('(', ')', ',', '\\', (), ()),
    ('(', ')', ',', '\\', ('on\\)e',), ('on)e',)),
    ('(', ')', ',', '\\', ('hoge', 'fug\\(a\\)a'), ('hoge', 'fug(a)a')),
    ('(', ')', ',', '.' , ('hoge', 'fug.)aae', 'piyo.piii'), ('hoge', 'fug)aae', 'piyopiii')),
    ('[', ']', ' ', '\\', ('poga', 'efa,f23', 'fee232f'), ('poga', 'efa,f23', 'fee232f')),
    ('{', '}', ',', '\\', ('bd', '\\{123', 'vw459vv\\}', 'pipo'), ('bd', '{123', 'vw459vv}', 'pipo')),
])

@pytest.mark.parametrize(*list_test_escaped_params)
def test_list_test_escaped_params(bch, ech, sep, esc_ch, cts, res_cts):
    """ Test a list parsing which includes escape sequences """
    rule = Seq(bch, RepSep(RepStr(CharsNotWithEscape(sep, ech, escape_char=esc_ch)), sep=sep, maker=list), ech)
    assert rule.trystr(bch + ''.join(ct + sep for ct in cts) + ech) == list(res_cts)
    assert rule.trystr(bch + sep.join(cts) + ech) == list(res_cts)

@pytest.mark.parametrize('num, suffix', [
    ('0143365', 'hogefuga'),
    ('435', 'jbs931'),
    ('8423', '.45'),
])
def test_use_all(num, suffix):
    """ Test `use_all` option on the `trystr` method """
    rule = RepStr(Chars(*'0123456789'))
    assert rule.trystr(num, use_all=False) == num
    assert rule.trystr(num, use_all=True) == num
    assert rule.trystr(num + suffix, use_all=False) == num
    with pytest.raises(NotAllCharsUsed):
        assert rule.trystr(num + suffix, use_all=True)

single_content_paramas = ('prefix, main, suffix', [
    ('hoge', '32145', 'fuga'),
    ('(', '1fe4vz', ')'),
    ('beg', 'Content', 'end'),
])
@pytest.mark.parametrize(*single_content_paramas)
def test_or_without_none(prefix, main, suffix):
    """ Test Opt symbol (without none_val specification) """
    rule = Seq(prefix, Opt(ExplStr(main)), suffix)
    assert rule.trystr(prefix + main + suffix) == (main, )
    assert rule.trystr(prefix + suffix) == ()
    
@pytest.mark.parametrize(*single_content_paramas)
def test_or_with_none(prefix, main, suffix):
    """ Test Opt symbol (with none_val specification) """
    rule = Seq(prefix, Opt(ExplStr(main), none_val=None), suffix)
    assert rule.trystr(prefix + main + suffix) == main
    assert rule.trystr(prefix + suffix) == None

@pytest.mark.parametrize('text', ['hoge', 'fugar', 'piyopiyo'])
def test_quoted_string(text):
    """ Test quoted string """
    rule = Seq('"', RepStr(AnyChar(), end='"'), '"')
    assert rule.trystr('"%s"' % text) == text

if __name__ == '__main__':
    # test_legacy_list_expl('(', ')', ',', ('hoge', 'fuga'))
    test_py_list_with_end('(', ')', ',', ('hoge', 'fugar', 'piyopiyo'))
