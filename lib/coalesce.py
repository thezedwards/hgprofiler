'''
Utilities for ``None``-coalescing, in the spirit of `PEP-505
<https://www.python.org/dev/peps/pep-0505/>`__ but written in pure Python.
'''


import unittest
import unittest.mock


def call(obj, method, *args, **kwargs):
    '''
    Coalesced function call.

    If ``obj`` is ``None``, return ``None``. Otherwise, return
    ``obj.method(*args, **kwargs)``.
    '''

    if obj is None:
        return None
    else:
        fn = getattr(obj, method)
        return fn(*args, **kwargs)


def index(obj, key):
    '''
    Coalesced index access.

    If ``obj`` is ``None``, return ``None``. Otherwise, return ``obj[key]``.
    '''

    return None if obj is None else obj[key]


def first(*args):
    '''
    Return the first non-None argument in ``*args``, or if all arguments are
    ``None``, then return ``None``.

    If an argument is callable, the value returned by calling the argument is
    used, otherwise the argument itself is used. This behavior for callables
    allows a pseudo short-circuit using nullary functions or lambdas, e.g.

        coalesce(foo, bar, lambda: default_ctor)

    This means use ``foo`` if it is not None. If ``foo`` is ``None``, then try
    ``bar``. If ``bar`` is ``None`` then return the value of
    ``default_ctor()``.
    Note that ``default_ctor`` is not called unless both ``foo`` and ``bar``
    are both ``None``.
    '''

    for arg in args:
        eval_ = arg() if callable(arg) else arg
        if eval_ is not None:
            return eval_

    return None


def member(obj, member):
    '''
    Coalesced member access.

    If ``obj`` is ``None``, return ``None``. Otherwise, return ``obj.member``.
    '''

    return None if obj is None else getattr(obj, member)


class TestCoalesce(unittest.TestCase):
    ''' Tests for ``coalesce`` package. '''

    def test_call_none(self):
        ''' ``call`` returns ``None`` if ``obj`` is ``None``. '''
        obj = None
        self.assertIsNone(call(obj, ''))

    def test_call_not_none(self):
        ''' ``call`` returns ``obj.strip()`` if ``obj`` is not ``None``. '''
        obj = '  test string  '
        self.assertEquals('test string', call(obj, 'strip'))

    def test_first_zero_args(self):
        ''' ``first`` returns ``None`` if it receives zero arguments. '''
        self.assertIsNone(first())

    def test_first_multiple_args(self):
        '''
        ``first`` returns the first non-``None`` argument and invokes callable
        arguments.
        '''
        obj1 = 'foo'
        obj2 = 'bar'
        self.assertEquals('foo', first(obj1, obj2))

        obj1 = None
        self.assertEquals('bar', first(obj1, obj2))

        obj1 = lambda: 'foo'
        obj2 = 'bar'
        self.assertEquals('foo', first(obj1, obj2))

        obj1 = lambda: None
        obj2 = 'bar'
        self.assertEquals('bar', first(obj1, obj2))

        obj1 = None
        obj2 = None
        obj3 = 'baz'
        self.assertEquals('baz', first(obj1, obj2, obj3))

    def test_first_shortcircuit(self):
        '''
        ``first`` does not call an argument unless all previous arguments
        evaluated to ``None``.
        '''

        obj1 = unittest.mock.Mock(return_value='foo')
        obj2 = unittest.mock.Mock(return_value='bar')
        self.assertEquals('foo', first(obj1, obj2))
        self.assertEquals(1, obj1.call_count)
        self.assertEquals(0, obj2.call_count)

        obj1 = unittest.mock.Mock(return_value=None)
        obj2 = unittest.mock.Mock(return_value='bar')
        self.assertEquals('bar', first(obj1, obj2))
        self.assertEquals(1, obj1.call_count)
        self.assertEquals(1, obj2.call_count)

    def test_index_none(self):
        ''' ``index`` returns ``None`` if ``obj`` is ``None``. '''
        obj = None
        self.assertIsNone(index(obj, 'foo'))

    def test_index_not_none(self):
        ''' ``index`` returns ``obj['foo']`` if ``obj`` is not ``None``. '''
        obj = {'foo': 'bar'}
        self.assertEquals('bar', index(obj, 'foo'))

    def test_member_none(self):
        ''' ``member`` returns ``None`` if ``obj`` is ``None``. '''
        obj = None
        self.assertIsNone(member(obj, 'numerator'))

    def test_member_not_none(self):
        '''
            ``member`` returns ``obj.numerator`` if ``obj`` is not ``None``.
        '''
        obj = 5
        self.assertEquals(5, member(obj, 'numerator'))
