"""backup-data.sh reads its options before it writes anything."""

import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / 'backup-data.sh'


def test_unknown_option_stops_before_backing_up():
    result = subprocess.run(['bash', str(SCRIPT), '--bogus'], capture_output=True, text=True, timeout=30)
    assert result.returncode == 2
    assert 'Unknown option: --bogus' in result.stderr
    assert '--open' in result.stderr
    assert 'Backing up' not in result.stdout


def test_open_is_a_known_option():
    source = SCRIPT.read_text()
    assert '--open) OPEN_FOLDER=true' in source
    assert '[ "$OPEN_FOLDER" = true ]' in source
