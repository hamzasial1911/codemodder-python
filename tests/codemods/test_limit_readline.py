from codemodder.codemods.limit_readline import LimitReadline
from tests.codemods.base_codemod_test import BaseCodemodTest


class TestLimitReadline(BaseCodemodTest):
    codemod = LimitReadline

    def test_rule_ids(self):
        assert self.codemod.RULE_IDS == ["limit-readline"]

    def test_file_readline(self, tmpdir):
        input_code = """file = open('some_file.txt')
file.readline()
"""
        expected = """file = open('some_file.txt')
file.readline(5_000_000)
"""
        self.run_and_assert(tmpdir, input_code, expected)

    def test_StringIO_readline(self, tmpdir):
        input_code = """import io
io.StringIO('some_string').readline()
"""

        expected = """import io
io.StringIO('some_string').readline(5_000_000)
"""

        self.run_and_assert(tmpdir, input_code, expected)

    def test_BytesIO_readline(self, tmpdir):
        input_code = """import io
io.BytesIO(b'some_string').readline()
"""

        expected = """import io
io.BytesIO(b'some_string').readline(5_000_000)
"""

        self.run_and_assert(tmpdir, input_code, expected)

    def test_taint_tracking(self, tmpdir):
        input_code = """file = open('some_file.txt')
arg = file
arg.readline(5_000_000)
"""

        expected = """file = open('some_file.txt')
arg = file
arg.readline(5_000_000)
"""

        self.run_and_assert(tmpdir, input_code, expected)
