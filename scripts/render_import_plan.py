from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f'{path} did not parse into a mapping')
    return data


def render_import_plan(data: dict[str, Any]) -> dict[str, Any]:
    jobs = []
    for source in data.get('sources', []):
        jobs.append(
            {
                'id': source['id'],
                'ecosystem': source['ecosystem'],
                'package': source['package'],
                'version': source['version'],
                'source_url': source['source_url'],
                'mirror_strategy': source['mirror_strategy'],
                'artifact_digest': source.get('artifact_digest'),
                'runtime_role': source['runtime_role'],
            }
        )
    return {
        'schema_version': 1,
        'project': data.get('project'),
        'owner': data.get('owner'),
        'jobs': jobs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Render importer plan from upstream lock manifest')
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()

    data = load_yaml(args.manifest)
    plan = render_import_plan(data)
    payload = json.dumps(plan, indent=2, sort_keys=True)

    if args.output:
        args.output.write_text(payload + "\n", encoding='utf-8')
        print(f'Wrote import plan to {args.output}')
    else:
        print(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
