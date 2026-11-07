"""Test-only on-disk SQLite so concurrent HTTP threads use separate connections."""
import copy
import os
from pathlib import Path
import tempfile

from config.settings import *  # noqa: F403

DATABASES = copy.deepcopy(DATABASES)  # noqa: F405
DATABASES['default']['TEST'] = {
    'NAME': os.environ.get('PART3_TEST_DATABASE', str(Path(tempfile.gettempdir()) / f'pms-part3-{os.getpid()}.sqlite3')),
}
