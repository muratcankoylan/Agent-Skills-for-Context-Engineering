# Reproduce the failing Linux SDK native-write gate

This is a diagnostic recipe, not a production image or a successful deployment
profile. It uses synthetic local HTTP responses and no provider credentials.
The recorded second run executed 25 tests: 24 passed, one native workspace-write
test failed, no errors or skips. Do not change the expected result to make this
environment pass. The fixed SDK sandbox helper also failed to create a namespace.

The immutable ARM64 dependency image already existed locally. It was not pulled
or rebuilt. Its ID is pinned below. The [eight-package wheel lock](linux-arm64-sdk-requirements.txt)
is Linux aarch64 / CPython 3.12 only, not a cross-platform lock. The
[test launcher](verify-sdk-worker.py) requires both exact SDK packages, a nonempty
real-SDK suite, all discovered tests executed and no skipped tests.

From the repository root, download only public dependency wheels into a new task
directory. This step needs network; the actual test container does not:

```sh
task_sdk_dir=$(mktemp -d)
python -m pip download --only-binary=:all: --require-hashes \
  --platform manylinux_2_17_aarch64 --platform manylinux2014_aarch64 \
  --implementation cp --python-version 3.12 --abi cp312 \
  --dest "$task_sdk_dir/wheels" \
  -r docs/product/verification-2026-09-29/linux-arm64-sdk-requirements.txt
```

Send only the reviewed test sources and wheels over stdin. No repository bind
mount, home directory, secret file, Docker socket or production state is exposed
inside the test container. The Docker client below uses the local desktop engine;
select the appropriate explicitly reviewed local context on another workstation.

```sh
tar -cf - \
  -C "$task_sdk_dir" wheels \
  -C "$PWD/docs/product/verification-2026-09-29" \
    linux-arm64-sdk-requirements.txt verify-sdk-worker.py \
  -C "$PWD" researcher/__init__.py researcher/service/__init__.py \
    researcher/service/codex_worker.py researcher/service/tests/__init__.py \
    researcher/service/tests/test_codex_worker.py \
| docker --context desktop-linux run --rm -i --network none --read-only \
    --cap-drop ALL --security-opt no-new-privileges --memory 2g --cpus 2 \
    --pids-limit 256 \
    --tmpfs /tmp:rw,nosuid,nodev,exec,size=1024m,mode=1777 \
    --tmpfs /workspace:rw,nosuid,nodev,exec,size=64m,uid=10001,gid=10001,mode=0700 \
    --entrypoint /bin/sh \
    sha256:38f3946ce5f963777b8f7f65ed65f1e1b78e226a198298dfca731e6e9d1c639b \
    -c 'set -eu
mkdir /tmp/proof
tar -xf - -C /tmp/proof
/usr/local/bin/python -m venv /tmp/proof/venv
/tmp/proof/venv/bin/python -m pip install --no-index --no-cache-dir \
  --only-binary=:all: --require-hashes --find-links /tmp/proof/wheels \
  -r /tmp/proof/linux-arm64-sdk-requirements.txt
/tmp/proof/venv/bin/python -m pip check
cd /tmp/proof
env -i PATH=/usr/bin:/bin TMPDIR=/workspace \
  CODEX_WORKER_TEST_PYTHON=/tmp/proof/venv/bin/python PYTHONDONTWRITEBYTECODE=1 \
  /tmp/proof/venv/bin/python -B verify-sdk-worker.py'
```

The measured source worker SHA-256 was
`7ac21600120dd3cb2a76a3eb3a7967eeea70e5c38eaa4c0cdbad3e9966103351`;
the second-run test module was
`3f1021555d03bfdebb885669d0325b841726a43ed14817f402bf1cd3a8a876fb`.
The runtime reports Python 3.12.14, UID 10001 and aarch64. Namespace denial is a
real admission failure for this native-tool profile, not an inferred model issue.
The test launcher exits nonzero and labels `production_ready=false`.

See [the verification report](../runtime-tracing-verification-2026-09-29.md) for
the successful macOS and integration tests and the exact limits of this result.
