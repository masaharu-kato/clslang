"""
"""

import pytest
from clslang.symbol import OR, Chain, ChainChars, CharNot, Chars, ExplChar, IgnoreOpt, Opt, RepSep, RepStr, Seq, Str

def make_json():
    DIGIT = Chars(*(chr(i) for i in range(ord('0'), ord('9')+1)))
    WS = IgnoreOpt(RepStr(Chars(' ')))

    Value = OR()
    Value.add(String := Seq('"', RepStr(CharNot('"')), '"'))
    Value.add(Number := ChainChars(Opt(ExplChar('-')), RepStr(DIGIT), Opt(ExplChar('.'), RepStr(DIGIT))))
    Value.add(Object := Seq('{', RepSep(String, ':', Value, sep=',', maker=dict), '}', ws=WS))
    Value.add(Array  := Seq('[', RepSep(Value, sep=',', ws=WS, maker=list), ']', ws=WS))
    Value.add(True_  := Str('true', value=True))
    Value.add(False_ := Str('false', value=False))
    Value.add(None_  := Str('null', value=None))

    return Value

def main():
    JSON = make_json()
    while True:
        text = input()
        if not text:
            break
        print(JSON.trystr(text))
    
if __name__ == '__main__':
    main()
