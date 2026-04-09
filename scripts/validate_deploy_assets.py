from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]


def parse_yaml_file(path: Path) -> None:
    with path.open('r', encoding='utf-8') as fh:
        list(yaml.safe_load_all(fh))


def require(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f'missing required path: {path.relative_to(ROOT)}')


def require_executable(path: Path, errors: list[str]) -> None:
    require(path, errors)
    if path.exists() and not os.access(path, os.X_OK):
        errors.append(f'path is not executable: {path.relative_to(ROOT)}')


def validate_local(errors: list[str]) -> None:
    local_dir = ROOT / 'deploy' / 'local'
    require(local_dir / '.env.example', errors)
    require(local_dir / 'podman-compose.yaml', errors)
    require_executable(local_dir / 'scripts' / 'bootstrap-podman-m2.sh', errors)
    require_executable(local_dir / 'scripts' / 'smoke-local.sh', errors)
    require_executable(local_dir / 'scripts' / 'preflight-podman-m2.sh', errors)
    require_executable(local_dir / 'scripts' / 'collect-local-debug.sh', errors)
    require_executable(local_dir / 'scripts' / 'down-local.sh', errors)
    require_executable(local_dir / 'scripts' / 'status-local.sh', errors)
    require_executable(local_dir / 'scripts' / 'reset-local.sh', errors)
    require(ROOT / 'images' / 'memoryd.Dockerfile', errors)
    require(ROOT / 'services' / 'memoryd' / 'requirements.txt', errors)
    require(ROOT / 'Makefile', errors)

    compose_path = local_dir / 'podman-compose.yaml'
    if not compose_path.exists():
        return
    parse_yaml_file(compose_path)
    data = yaml.safe_load(compose_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        errors.append('deploy/local/podman-compose.yaml did not parse into a mapping')
        return
    services = data.get('services')
    if not isinstance(services, dict) or 'memoryd' not in services:
        errors.append('deploy/local/podman-compose.yaml missing memoryd service')
        return
    memoryd = services['memoryd']
    build = memoryd.get('build') or {}
    context = build.get('context')
    dockerfile = build.get('dockerfile')
    if not isinstance(context, str) or not isinstance(dockerfile, str):
        errors.append('memoryd build config is missing context or dockerfile')
        return
    context_dir = (compose_path.parent / context).resolve()
    dockerfile_path = (context_dir / dockerfile).resolve()
    if not dockerfile_path.exists():
        errors.append(f'memoryd dockerfile does not exist from compose build context: {dockerfile_path}')


def validate_kustomization(errors: list[str]) -> None:
    gke_dir = ROOT / 'deploy' / 'cloud' / 'gke-review'
    kustomization = gke_dir / 'kustomization.yaml'
    require(kustomization, errors)
    if not kustomization.exists():
        return
    parse_yaml_file(kustomization)
    data = yaml.safe_load(kustomization.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        errors.append('deploy/cloud/gke-review/kustomization.yaml did not parse into a mapping')
        return
    resources = data.get('resources') or []
    if not isinstance(resources, list):
        errors.append('deploy/cloud/gke-review/kustomization.yaml resources must be a list')
        return
    for item in resources:
        if isinstance(item, str):
            require(gke_dir / item, errors)


def validate_yaml_tree(paths: Iterable[Path], errors: list[str]) -> None:
    for path in paths:
        try:
            parse_yaml_file(path)
        except Exception as exc:
            errors.append(f'failed to parse YAML {path.relative_to(ROOT)}: {exc}')


def main() -> int:
    errors: list[str] = []
    validate_local(errors)
    validate_kustomization(errors)

    yaml_paths = sorted((ROOT / 'deploy').rglob('*.yaml'))
    validate_yaml_tree(yaml_paths, errors)

    if errors:
        for err in errors:
            print(f'ERROR: {err}', file=sys.stderr)
        return 1

    print('OK: deployment assets validated')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
