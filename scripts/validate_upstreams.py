from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

EXACT_VERSION_RE = re.compile(r"^[A-Za-z0-9_.!+-]+$")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f'{path} did not parse into a mapping')
    return data


def validate_exact_version(version: str) -> bool:
    if any(token in version for token in ('^', '~', '>=', '<=', '>', '<', '*', 'x', 'X', 'latest')):
        return False
    return bool(EXACT_VERSION_RE.match(version))


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get('schema_version') != 1:
        errors.append('schema_version must be 1')

    sources = data.get('sources')
    if not isinstance(sources, list) or not sources:
        errors.append('sources must be a non-empty list')
        return errors

    seen_ids: set[str] = set()
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            errors.append(f'sources[{index}] must be a mapping')
            continue

        source_id = str(source.get('id') or '').strip()
        if not source_id:
            errors.append(f'sources[{index}] missing id')
        elif source_id in seen_ids:
            errors.append(f'duplicate source id: {source_id}')
        else:
            seen_ids.add(source_id)

        for key in ('ecosystem', 'package', 'version', 'source_url', 'mirror_strategy', 'runtime_role'):
            if not str(source.get(key) or '').strip():
                errors.append(f'source {source_id or index} missing {key}')

        version = str(source.get('version') or '')
        if version and not validate_exact_version(version):
            errors.append(f'source {source_id or index} has non-exact version: {version}')

        if source.get('artifact_digest') in ('', 'TODO', 'todo'):
            errors.append(f'source {source_id or index} has placeholder artifact_digest; use null until imported')

    policies = data.get('policies') or {}
    if not isinstance(policies, dict):
        errors.append('policies must be a mapping')
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description='Validate memorymesh upstream lock manifest')
    parser.add_argument('manifest', type=Path)
    args = parser.parse_args()

    data = load_yaml(args.manifest)
    errors = validate_manifest(data)
    if errors:
        for err in errors:
            print(f'ERROR: {err}', file=sys.stderr)
        return 1

    print(f'OK: {args.manifest} validated with {len(data.get("sources", []))} pinned sources')
    unresolved = [s['id'] for s in data.get('sources', []) if s.get('artifact_digest') in (None, '', [])]
    if unresolved:
        print('INFO: unresolved artifact digests remain for:', ', '.join(unresolved))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
