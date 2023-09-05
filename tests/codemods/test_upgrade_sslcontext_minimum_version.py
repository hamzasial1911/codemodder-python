import pytest
from codemodder.codemods.upgrade_sslcontext_minimum_version import (
    UpgradeSSLContextMinimumVersion,
)
from tests.codemods.base_codemod_test import BaseSemgrepCodemodTest

INSECURE_VERSIONS = [
    "TLSv1",
    "TLSv1_1",
    "SSLv2",
    "SSLv3",
    "MINIMUM_SUPPORTED",
]


class TestUpgradeSSLContextMininumVersion(BaseSemgrepCodemodTest):
    codemod = UpgradeSSLContextMinimumVersion

    @pytest.mark.parametrize("version", INSECURE_VERSIONS)
    def test_upgrade_minimum_version(self, tmpdir, version):
        input_code = f"""import ssl

context = ssl.SSLContext()
context.minimum_version = ssl.TLSVersion.{version}
"""
        expexted_output = """import ssl

context = ssl.SSLContext()
context.minimum_version = ssl.TLSVersion.TLSv1_2
"""
        self.run_and_assert(tmpdir, input_code, expexted_output)

    def test_upgrade_minimum_version_add_import(self, tmpdir):
        input_code = """from ssl import SSLContext, TLSVersion

context = SSLContext()
context.minimum_version = TLSVersion.TLSv1
"""
        expexted_output = """from ssl import SSLContext
import ssl

context = SSLContext()
context.minimum_version = ssl.TLSVersion.TLSv1_2
"""
        self.run_and_assert(tmpdir, input_code, expexted_output)

    def test_bad_maximum_dont_update(self, tmpdir):
        """
        This codemod should not update maximum_version

        (Maybe that should be a job for a separate codemod)
        """
        input_code = """from ssl import SSLContext, TLSVersion

context = SSLContext()
context.maximum_version = TLSVersion.TLSv1
"""
        self.run_and_assert(tmpdir, input_code, input_code)

    def test_import_with_alias(self, tmpdir):
        input_code = """import ssl as whatever

context = whatever.SSLContext()
context.minimum_version = whatever.TLSVersion.SSLv3
"""
        expexted_output = """import ssl as whatever
import ssl

context = whatever.SSLContext()
context.minimum_version = ssl.TLSVersion.TLSv1_2
"""
        self.run_and_assert(tmpdir, input_code, expexted_output)
