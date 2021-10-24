"""
    Source Iterator
"""
import copy
from typing import Generic, Iterable, Iterator, List, Optional, Sized, Type, TypeVar

CT = TypeVar('CT')

class StopSrcItr(Exception):
    """ SrcItr class stop iteration """

class ItrSeq(Generic[CT], Iterable[CT]):
    def __init__(self, itr:Iterator[CT]):
        self.itr = itr
        self.cache:list = []

    def __getitem__(self, index:int) -> CT:
        while len(self.cache) <= index:
            self.cache.append(next(self.itr))
        return self.cache[index]

class SrcItr(Generic[CT], Iterator[CT]):
    """ Source sequence iterator """
    def __init__(self, seq:List[CT], pos:int=0):
        self.seq = seq
        self.pos = pos
        self.child:Optional[SrcItr] = None
        # print('init... self:', id(self), ', parent:', id(self.parent) if self.parent else 'None')

    def __enter__(self) -> 'SrcItr':
        """ Start a new iterator """
        self.child = SrcItr(self.seq, self.pos)
        return self.child

    def __next__(self) -> CT:
        if self.is_eof():
            raise StopSrcItr()
        ch = self.seq[self.pos]
        self.pos += 1
        return ch

    def is_eof(self) -> bool:
        return self.pos >= len(self.seq)

    def __exit__(self, exc_type:Type[Exception], exc_value:Exception, trace):
        """ End this iterator """
        # print('exit... self:', id(self), ', parent:', id(self.parent) if self.parent else 'None')
        if self.child is not None:

            # Advance the position only if no exception occurs
            if not exc_type:
                self.pos = self.child.pos

            del self.child
            self.child = None

    def __repr__(self) -> str:
        return '<SrcItr#%d len=%d, pos=%d>' % (id(self), len(self.seq), self.pos)


def test_itr():
    seq = 'abcdefghijk'
    itr = SrcItr(seq)
    yield '0'
    yield next(itr)
    with itr as citr:
        yield '1'
        yield next(citr)
        yield next(citr)
    yield '2'
    yield next(itr)
    try:
        with itr as citr:
            yield '3'
            yield next(citr)
            yield next(citr)
            assert 0
    except AssertionError:
        pass
    yield '4'
    yield next(itr)
    try:
        with itr as citr:
            yield '5'
            yield next(citr)
            with citr as ccitr:
                yield '6'
                yield next(ccitr)
                yield next(ccitr)
                yield next(ccitr)
                assert 0
            with citr as ccitr:
                yield '7'
                yield next(ccitr)
                yield next(ccitr)
            yield '8'
            yield next(citr)
            yield next(citr)
            assert 0
    except AssertionError:
        pass
    yield '9'
    yield next(itr)

def main():
    res_seq  = ''.join(test_itr())
    true_seq = '0a1bc2d3ef4e5f6ghi9f'
    print(res_seq, true_seq)
    assert res_seq == true_seq

if __name__ == '__main__':
    main()
