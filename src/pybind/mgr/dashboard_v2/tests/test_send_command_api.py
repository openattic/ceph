from unittest import TestCase

from ..models.send_command_api import undoable, undo_transaction


class UndoTest(TestCase):
    class Test(object):
        def __init__(self):
            self.val = 0

        @undoable
        def add(self, x):
            self.val += x
            yield self.val
            self.val -= x

        @undoable
        def multi(self, x):
            self.val *= x
            yield self.val
            self.val /= x

        @undoable
        def minus(self, x):
            self.val -= x
            yield self.val
            self.add(x)

        @undoable
        def div(self):
            self.val /= 0
            yield self.val
            assert False

    def test_exception(self):
        test = UndoTest.Test()
        test.add(100)
        with undo_transaction(test, NotImplementedError):
            self.assertEqual(test.val, 100)
            test.add(4)
            self.assertEqual(test.val, 104)
            test.add(2)
            self.assertEqual(test.val, 106)
            raise NotImplementedError()
        self.assertEqual(test.val, 100)

    def test_success(self):
        test = UndoTest.Test()
        test.add(100)
        self.assertEqual(test.val, 100)
        with undo_transaction(test, NotImplementedError):
            self.assertEqual(test.val, 100)
            self.assertEqual(test.add(4), 104)
            self.assertEqual(test.val, 104)
            test.add(2)
            self.assertEqual(test.val, 106)
        self.assertEqual(test.val, 106)

    def test_unknown_exception(self):
        test = UndoTest.Test()
        try:
            with undo_transaction(test, NotImplementedError):
                self.assertEqual(test.val, 0)
                test.add(4)
                self.assertEqual(test.val, 4)
                raise ValueError()
        except ValueError:
            self.assertEqual(test.val, 4)
            return
        self.fail('no exception')

    def test_broken_undo(self):
        test = UndoTest.Test()
        try:
            with undo_transaction(test, NotImplementedError):
                test.add(4)
                self.assertEqual(test.val, 4)
                test.multi(0)
                self.assertEqual(test.val, 0)
                raise NotImplementedError()
        except NotImplementedError:
            self.fail('wrong type')
        except ZeroDivisionError:
            return
        self.fail('no exception')

    def test_undoable_undo(self):
        with undo_transaction(UndoTest.Test(), NotImplementedError) as test:
            self.assertEqual(test.val, 0)
            test.add(4)
            self.assertEqual(test.val, 4)
            self.assertEqual(test.minus(1), 3)
            self.assertEqual(test.val, 3)
            raise NotImplementedError()
        self.assertEqual(test.val, 0)

    def test_exception_in_func(self):
        test = UndoTest.Test()
        test.add(100)
        with undo_transaction(test, ZeroDivisionError):
            test.add(4)
            test.div()
            self.fail('div by 0')
        self.assertEqual(test.val, 100)

    def test_re_raise(self):
        try:
            with undo_transaction(UndoTest.Test(), ValueError, re_raise_exception=True):
                raise ValueError()
        except ValueError:
            return
        self.fail('no exception')
