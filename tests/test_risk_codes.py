"""Source guard for risk names shared by Cypher, Python, and the browser."""
from pathlib import Path
import re


def test_risk_codes_are_consistent_across_sources():
    root = Path(__file__).resolve().parents[1]
    allowed = {'NO OTHER AUTHOR', 'ONE OTHER AUTHOR', 'COVERED'}
    retired = ['ORPH' + 'ANED', 'AT ' + 'RISK']
    found = set()
    for directory in ['src/busfactor', 'web', 'queries']:
        for path in (root / directory).rglob('*'):
            if path.suffix not in {'.py', '.js', '.html', '.cypher'}:
                continue
            source = path.read_text(encoding='utf-8')
            assert not any(code in source for code in retired), str(path)
            for code in re.findall(r'''["'](NO OTHER AUTHOR|ONE OTHER AUTHOR|COVERED)["']''', source):
                found.add(code)
            for code in re.findall(r'''["']risk["']\s*:\s*["']([^"']+)["']''', source):
                assert code in allowed, (path, code)
    assert found == allowed
    graph_js = (root / 'web/graph.js').read_text(encoding='utf-8')
    assert 'node.no-other-author' in graph_js and 'node.one-other-author' in graph_js
