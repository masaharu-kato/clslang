"""
"""
import os
import json
import pytest
from clslang.symbol import OR, Chain, ChainChars, CharNot, Chars, ExplChar, IgnoreOpt, Keyword, Named, Opt, RepSep, RepStr, Seq, Str, SymbolTryFailed

def make_json():
    DIGIT = Chars(*(chr(i) for i in range(ord('0'), ord('9')+1)))
    WS = IgnoreOpt(RepStr(Chars(' ')))

    Value = OR(finalize=False)
    Value.add(String := Named('String', Seq('"', RepStr(CharNot('"')), '"')))
    Value.add(Named('Real'  , ChainChars(Opt(ExplChar('-')), RepStr(DIGIT), ExplChar('.'), RepStr(DIGIT), maker=float)))
    Value.add(Named('Int'   , ChainChars(Opt(ExplChar('-')), RepStr(DIGIT), maker=int)))
    Value.add(Named('Object', Seq('{', WS, RepSep(String, WS, ':', WS, Value, sep=(WS, ',', WS), maker=dict), WS, '}')))
    Value.add(Named('Array ', Seq('[', WS, RepSep(Value, sep=(WS, ',', WS), maker=list), WS, ']')))
    Value.add(Named('True  ', Keyword('true', value=True)))
    Value.add(Named('False ', Keyword('false', value=False)))
    Value.add(Named('None  ', Keyword('null', value=None)))
    Value.finalize()
    JSON = Seq(WS, Value, WS)
    
    return JSON

JSON = make_json()
datatexts = [l.strip() for l in open(os.path.join(os.path.dirname(__file__), 'test_json_data.txt'))]

@pytest.mark.parametrize('datatext', datatexts)
def test_json(datatext):
    data = json.loads(datatext)
    assert JSON.trystr(datatext) == data

def main():
    JSON = make_json()
    while True:
        text = input()
        if not text:
            break
        try:
            res = JSON.trystr(text)
            print(res)
        except SymbolTryFailed as e:
            print('Exception: SymbolTryFailed:', e)
    
# def make_data():
#     svals = [
#         0, 1, 23, 78905, -9, -87, -65025,
#         1.0, 23.5, 789.05, -9, -0.87, -6502.5,
#         'a', 'bCD', 'hogefuga', 'piy123vad', '53401cm2',
#         True, False, None,
#     ]
#     svals1 = [*svals]
#     for i, v in enumerate(svals1):
#         svals.append([v])
#         svals.append({'key%d' % i: v})
#     svals2 = [*svals]
#     for i, (v1, v2) in enumerate(zip(svals2[:-1], svals2[1:])):
#         svals.append([v1, v2])
#         svals.append({'hoge%d' % i: v1, '%dfugar' % i: v2})
#     svals3 = [*svals]
#     for i, (v1, v2, v3) in enumerate(zip(svals3[:-2], svals3[1:-1], svals3[2:])):
#         svals.append([v1, v2, v3])
#         svals.append({'oe%d' % i: v1, '%dfug' % i: v2, 'p%diyopiyo' % i: v3})
    
#     return svals

if __name__ == '__main__':
    main()
    # for _data in make_data():
    #     print(json.dumps(_data))
