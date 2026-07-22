import os

import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')


@pytest.fixture(scope='session')
def django_db_setup():
    """Use existing MongoDB/file fallback; no Django ORM database setup required."""
    pass
