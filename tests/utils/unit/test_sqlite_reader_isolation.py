"""Real SQLite with a cursor wrapper that fixes the thread interleaving only."""
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from simulator.utils.sqlite_handler import SqliteSaver

class ScheduledCursor:
    def __init__(self, cursor):
        self.cursor = cursor
        self.first_executed = threading.Event()
        self.second_attempted = threading.Event()
        self.second_executed = threading.Event()
        self.first_fetched = threading.Event()

    def execute(self, sql, parameters=()):
        result = self.cursor.execute(sql, parameters)
        if parameters == ('first',):
            self.first_executed.set()
            assert self.second_attempted.wait(2)
            # An unlocked reader can replace the cursor here. With the fix,
            # the second reader is waiting for the saver lock instead.
            self.second_executed.wait(0.15)
        elif parameters == ('second',):
            self.second_executed.set()
            assert self.first_fetched.wait(2)
        elif sql.startswith('INSERT'):
            self.second_executed.set()
        return result

    def fetchall(self):
        rows = self.cursor.fetchall()
        if threading.current_thread().name.startswith('first-reader'):
            self.first_fetched.set()
        return rows

    def __getattr__(self, name):
        return getattr(self.cursor, name)

@pytest.mark.parametrize('kind', ['dialog', 'thought', 'tool'])
def test_readers_do_not_consume_another_threads_result(tmp_path, kind):
    saver = SqliteSaver(str(tmp_path / 'checkpoint.sqlite'))
    for thread in ('first', 'second'):
        if kind == 'dialog': saver.insert_dialog(thread, 'Human', thread + '-message')
        elif kind == 'thought': saver.insert_thought(thread, thread + '-thought')
        else: saver.insert_tool(thread, 'lookup', thread + '-input', thread + '-output')
    scheduled = ScheduledCursor(saver.cursor)
    saver.cursor = scheduled
    read = getattr(saver, 'read_' + kind)
    def second():
        assert scheduled.first_executed.wait(2)
        scheduled.second_attempted.set()
        return read('second')
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix='first-reader') as a:
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix='second-reader') as b:
                first = a.submit(read, 'first')
                other = b.submit(second)
                first_rows, second_rows = first.result(timeout=5), other.result(timeout=5)
        assert first_rows is not None
        assert {row[0] for row in first_rows} == {'first'}
        assert second_rows is not None
        assert {row[0] for row in second_rows} == {'second'}
    finally:
        saver.exit()

@pytest.mark.parametrize('kind', ['dialog', 'thought', 'tool'])
def test_empty_result_remains_none(tmp_path, kind):
    saver = SqliteSaver(str(tmp_path / 'empty.sqlite'))
    try:
        assert getattr(saver, 'read_' + kind)('missing') is None
    finally:
        saver.exit()

@pytest.mark.parametrize('kind', ['dialog', 'thought', 'tool'])
def test_reader_keeps_result_while_writer_inserts(tmp_path, kind):
    saver = SqliteSaver(str(tmp_path / 'read-write.sqlite'))
    saver.insert_dialog('first', 'Human', 'message')
    saver.insert_thought('first', 'thought')
    saver.insert_tool('first', 'lookup', 'input', 'output')
    scheduled = ScheduledCursor(saver.cursor)
    saver.cursor = scheduled
    read = getattr(saver, 'read_' + kind)
    def writer():
        assert scheduled.first_executed.wait(2)
        scheduled.second_attempted.set()
        saver.insert_thought('other', 'new thought')
    try:
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix='first-reader') as a:
            with ThreadPoolExecutor(max_workers=1) as b:
                first = a.submit(read, 'first')
                write = b.submit(writer)
                rows = first.result(timeout=5)
                write.result(timeout=5)
        assert rows is not None
        assert {row[0] for row in rows} == {'first'}
        assert saver.read_thought('other') == [('other', 'new thought')]
    finally:
        saver.exit()
