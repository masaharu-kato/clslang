"""
    Automaton (State machine) classes
"""
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

Char = int
EOF = -1

Maker = Union[None, bool, Callable[[List[Char]], Any]]
CONTINUE = None
IGNORE = False
OUTPUT = True
State = Dict[Optional[Char], Tuple[Optional[dict], Maker]]

class StateFailed(Exception):
    """ State Failed Exception """

def state_try_str(start_state: State, seq: str) -> Iterator[Any]:
    return state_try_seq(start_state, (ord(ch) for ch in seq))

def state_try_seq(start_state: State, seq: Iterator[Char]) -> Iterator[Any]:
    c_state = start_state
    ch_stack: List[Char] = []
    for ch in seq:
        try:
            c_state, maker = c_state[ch] if ch in c_state else c_state[None]
        except KeyError as e:
            raise StateFailed() from e
        if maker is CONTINUE:
            ch_stack.append(ch)
        else:
            if maker is not IGNORE:
                if maker is OUTPUT:
                    yield bytes(ch_stack)
                else:
                    yield maker(ch_stack)
            ch_stack = []
        if c_state is None:
            return

StateName = str
CharLike = Union[Char, bytes, str]
StateWithRef = Dict[Optional[CharLike], Tuple[Optional[StateName], Maker]]

def make_state(rstates: Dict[StateName, StateWithRef]) -> State:
    states = {name: {} for name in rstates}
    for name, rstate in rstates.items():
        for chl, (refname, maker) in rstate.items():
            ch = None if chl is None else chl if isinstance(chl, Char) else chl[0] if isinstance(chl, bytes) else ord(chl[0])
            states[name][ch] = (states[refname] if refname is not None else None, maker)
    return list(states.values())[0]


def test():
    state = make_state({
        0: {'(': (1, IGNORE)},
        1: {'(': (1, IGNORE), ')': (2, OUTPUT), ',': (1, OUTPUT), None: (1, CONTINUE)},
        2: {EOF: (None, IGNORE)}
    })

    res = list(state_try_str(state, '(hoge,fugar,piyopiyo)'))
    print(res)
    assert res == [b'hoge', b'fugar', b'piyopiyo']

if __name__ == '__main__':
    test()
