
from clslang.symbol import OR, Chain, CharNot, CharsNot, ExplChar, ExplStr, Opt, Rep, RepStr, Seq

def main():
    rule = Seq(ExplChar('('), RepStr(CharNot(')')), ExplChar(')'))
    res = rule.trystr('(hoge)')

    # sep = ','
    # bch = '('
    # ech = ')'
    # Val = RepStr(CharsNot(sep, ech))
    # rule = Seq(bch, Chain(Rep(Val, sep), Opt(Val)), ech)
    # res = rule.trystr('(hoge,fuga,piyo)')
    
    print(res)

if __name__ == '__main__':
    main()
