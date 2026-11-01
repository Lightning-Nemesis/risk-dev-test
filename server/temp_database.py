"""
Shared test helper: runs each test against its own throwaway database, so tests never touch the real test.db
"""
# Built-ins
import os
import tempfile
# 3rd-party
# Internal
import cpi
from cpi import Observation


class TempDatabaseMixin:
    """Add to a unittest.TestCase to give each test a fresh database with new sample data."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.original_db_file = cpi.db_file
        cpi.db_file = os.path.join(self.temp_dir.name, 'test.db')
        Observation.create_table()

    def tearDown(self):
        cpi.db_file = self.original_db_file
        self.temp_dir.cleanup()
