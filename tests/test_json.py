"""
"""

import pytest
from clslang.symbol import OR, Chain, ChainChars, CharNot, Chars, ExplChar, IgnoreOpt, Opt, RepSep, RepStr, Seq, Str, SymbolTryFailed

def make_json():
    DIGIT = Chars(*(chr(i) for i in range(ord('0'), ord('9')+1)))
    WS = IgnoreOpt(RepStr(Chars(' ')))

    Value = OR()
    Value.add(String := Seq('"', RepStr(CharNot('"')), '"'))
    Value.add(Number := ChainChars(Opt(ExplChar('-')), RepStr(DIGIT), Opt(ExplChar('.'), RepStr(DIGIT))))
    Value.add(Object := Seq('{', WS, RepSep(String, WS, ':', WS, Value, sep=(WS, ',', WS), maker=dict), WS, '}'))
    Value.add(Array  := Seq('[', WS, RepSep(Value, sep=(WS, ',', WS), maker=list), WS, ']'))
    Value.add(True_  := Str('true', value=True))
    Value.add(False_ := Str('false', value=False))
    Value.add(None_  := Str('null', value=None))
    JSON = Seq(WS, Value, WS)
    
    return JSON

def main():
    JSON = make_json()
    while True:
        text = input()
        if not text:
            break
        try:
            print(JSON.trystr(text))
        except SymbolTryFailed as e:
            print(e)
    
if __name__ == '__main__':
    main()
