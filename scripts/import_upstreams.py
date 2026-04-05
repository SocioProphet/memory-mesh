from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f'{path} did not parse into a mapping')
    return data


def fetch_json(url: str) -> Any:
    with urllib.request.urlopen(url) as response:  # noqa: S310 - controlled by pinned manifest sources
        return json.loads(response.read().decode('utf-8'))


def resolve_pypi(package: str, version: str) -> list[dict[str, Any]]:
    url = f'https://pypi.org/pypi/{urllib.parse.quote(package)}/{urllib.parse.quote(version)}/json'
    data = fetch_json(url)
    artifacts = []
    for item in data.get('urls', []):
        artifacts.append(
            {
                'filename': item.get('filename'),
                'url': item.get('url'),
                'packagetype': item.get('packagetype'),
                'python_version': item.get('python_version'),
                'sha256': (item.get('digests') or {}).get('sha256'),
            }
        )
    return artifacts


def resolve_npm(package: str, version: str) -> list[dict[str, Any]]:
    encoded_name = urllib.parse.quote(package, safe='@/')
    url = f'https://registry.npmjs.org/{encoded_name}/{urllib.parse.quote(version)}'
    data = fetch_json(url)
    dist = data.get('dist') or {}
    return [
        {
            'filename': dist.get('tarball', '').rstrip('/').split('/')[-1] or f'{package}-{version}.tgz',
            'url': dist.get('tarball'),
            'shasum': dist.get('shasum'),
            'integrity': dist.get('integrity'),
        }
    ]


def resolve_source(source: dict[str, Any]) -> dict[str, Any]:
    ecosystem = source['ecosystem']
    package = source['package']
    version = source['version']
    if ecosystem == 'pypi':
        artifacts = resolve_pypi(package, version)
    elif ecosystem == 'npm':
        artifacts = resolve_npm(package, version)
    else:
        raise ValueError(f'Unsupported ecosystem: {ecosystem}')
    return {
        'id': source['id'],
        'ecosystem': ecosystem,
        'package': package,
        'version': version,
        'source_url': source['source_url'],
        'mirror_strategy': source['mirror_strategy'],
        'runtime_role': source['runtime_role'],
        'artifacts': artifacts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Resolve upstream artifacts for the importer pipeline')
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, default=Path('third_party/resolved.upstreams.json'))
    args = parser.parse_args()

    manifest = load_yaml(args.manifest)
    resolved = {
        'schema_version': 1,
        'project': manifest.get('project'),
        'owner': manifest.get('owner'),
        'resolved': [],
    }

    try:
        for source in manifest.get('sources', []):
            resolved['resolved'].append(resolve_source(source))
    except Exception as exc:
        print(f'ERROR: failed to resolve upstreams: {exc}', file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(resolved, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(f'Wrote resolved upstreams to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
