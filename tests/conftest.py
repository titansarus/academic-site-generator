import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EXAMPLE_SITE = ROOT / "examples" / "basic-site"


@pytest.fixture
def example_site_dir():
    return EXAMPLE_SITE
