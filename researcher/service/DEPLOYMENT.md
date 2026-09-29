# Standalone deployment: persistent-host profile

The selected runtime is now the [Codex SDK](CODEX_SDK.md), superseding the managed
runtime in the earlier [GitHub release plan](../../docs/product/github-release-plan-2026-09-29.md).
The first reference topology is one persistent Linux coordinator. It is not
instructions for putting local SQLite on an ephemeral Actions runner. See the
[locked SDK deployment profile](deploy/CODEX_RUNTIME.md) for tool-free versus
native-tool prerequisites. Remote durable admission and separately scoped
publication still require their own release evidence. Secret-free release CI does
not activate a production coordinator.

Status: implementation templates, **not a deployed or production-certified service**.
The runtime is the repository-owned Python service. Codex tasks, desktop
automations, launchd and an interactive developer are not runtime dependencies.
No cloud vendor, account, region, VM size, image digest or operating budget has
been selected. Do not infer permission to provision a billable resource from
these templates.

## Initial topology

Use one dedicated Linux VM with local persistent disk. Run one foreground
coordinator, a separate loopback operator API, and optionally the read-only
Control Center on the same host/network namespace. The API participates in
SQLite transactions for admission and pause; only the coordinator executes
research work and external effects. This is not a multi-host or highly available
deployment.

```text
operator via restricted SSH tunnel
  -> Control Center 127.0.0.1:3000 (server-side operator credential)
  -> research API 127.0.0.1:8787
  -> local SQLite transactions and private artifacts

foreground Organization -> configured retrieval APIs
                        -> Codex SDK threads -> budget gateway -> OpenAI
                        -> frozen candidate and evaluation receipts (no auto-publication)
```

The coordinator owns scheduling; there is no second cron or desktop scheduler.
The [daily retrieval-only configuration](DAILY_RETRIEVAL.md) uses this same
coordinator and state boundary. It can run with zero model calls and produces
discovery digests, not accepted evidence or automatic skill updates. Its free
example is for a bounded canary, not permission to enable unattended execution.
`serve` admits due slots and executes bounded jobs. Run only one coordinator for
a state directory. A process lock and transactional reservations reject overlap;
they do not provide cross-host leader election. Do not put SQLite on NFS, an
object-store mount, a shared network filesystem or an ephemeral container layer.

For the funded OpenAI pilot, the separate
[organization coordinator](ORGANIZATION.md) connects retrieval windows to the
[pipeline](RESEARCH_PIPELINE.md). Keep a single persistent
[campaign authority](OPENAI_CAMPAIGN.md) alongside the retrieval Store. All
model roles and evaluation arms use that authority, not per-job budget directories.
The organization consumes only retrieval-mode source configurations, explicit
schedule-to-skill mappings, and an optional independently supplied evaluation
dataset. A proposed candidate with no dataset stops at `awaiting_dataset`.
It never publishes, promotes, manufactures gold or creates/resets its allowance.
Do not also enable OpenAI on the older native compatibility worker against a
separate budget while claiming the campaign ceiling covers both. A Linux service
UID and read-only release are necessary but do not enforce an account-wide API
ceiling against other credential holders.

The [artifact-complete recovery runbook](../runbooks/service-recovery.md) now
provides capture/candidate/session closure and an explicit budget-authority
profile. It replaces SQLite-only inspection backups for restoration tests.
Restored stores remain paused. Encrypt backup storage/transport and fence the
original writer; the bundle itself is deliberately not an encryption product.

The Control Center's current service reader accepts only the exact URL
`http://127.0.0.1:8787`, requires `HOSTNAME=127.0.0.1` and rejects external Host
headers. Keep the UI and API on the same host network namespace. A service DNS
name in a Docker bridge is **not currently supported by that reader**. Public
cloud ingress requires a separate reviewed TLS and user-authentication design;
a bearer token in browser JavaScript or `NEXT_PUBLIC_*` is not that design.

## Release and state boundaries

| Location | Owner / access | Contents |
| --- | --- | --- |
| `/srv/context-research/release` or container `/repo` | Operator-owned, service read-only | Clean standalone clone at an approved full commit SHA, including its local `.git` directory |
| `/opt/context-research` | Operator-owned, service read-only | Pinned Python runtime/venv, dependency locks for the selected profile, deployment launcher |
| `/etc/context-research` or container `/config` | Operator-managed, service readable only as required | Reviewed JSON configuration and release identity; private credential sources are separate |
| `/var/lib/context-research` or container `/state` | Service UID 10001, directory mode `0700` | SQLite database/WAL, effect receipts, captures and frozen artifacts |
| Private temporary directory | Service-only, bounded | Transient trusted runtime work; not the durable state store |

Use a dedicated non-login `context-research` user and group with numeric ID
10001. Review account-ID collisions before provisioning. Do not mount the host
Docker socket, SSH-agent socket, home directory or unrelated repository clones.
Never place provider credentials or private captures in the release clone.

`workflow.git_head()` currently needs Git and `.git`, so a source tarball alone
is insufficient. Use a full independent clone, not a Git worktree whose `.git`
file points outside the mounted directory. Do not reuse the development checkout.
Do not update the release in place while processes are running.

The [launcher](deploy/launch.py) requires `RESEARCH_RELEASE_COMMIT` to be a full
40-character lowercase commit SHA, checks HEAD, rejects tracked, untracked and
ignored working-tree changes, verifies the installed dependency locks match
the release, and requires nonroot execution. The core lock is always required;
`RESEARCH_INSTALL_MCP=1` additionally requires `RESEARCH_MCP_DEPENDENCY_LOCK` to
identify the installed optional lock. If that optional path is supplied, it is
verified even when the profile is `0`. These environment values are trusted
operator configuration, not a package attestation. It rejects a writable release root
or `.git` directory. **The host must still enforce read-only mounts/paths for the
entire release.** These preflight checks are not a filesystem attestation or a
replacement for a reviewed release manifest, dependency audit and source export.
They also do not accept any draft specification or confer promotion authority.

## Linux/systemd option

The immediate deployment templates are [coordinator](deploy/context-research.service)
and [operator API](deploy/context-research-api.service). They are not installed or
enabled by this repository. Before using them, the operator must:

1. Provision the dedicated user, reviewed OS/Python 3.12 patch release, Git, CA
   certificates and local persistent disk. Record exact runtime/package versions.
2. Materialize the clean reviewed clone at `/srv/context-research/release` as an
   operator-owned real directory. Keep `.git` local and readable. Make all source
   read-only to UID 10001.
3. Create `/opt/context-research/venv`, install with the release's hash-locked
   requirements, and copy the identical lock and reviewed launcher into
   `/opt/context-research`. Do this as provisioning, not inside an agent turn:

   ```sh
   python3.12 -m venv /opt/context-research/venv
   /opt/context-research/venv/bin/python -m pip install --require-hashes --only-binary=:all: -r /srv/context-research/release/requirements-dev.txt
   /opt/context-research/venv/bin/python -m pip check
   ```

   Organization execution also requires an isolated mandatory SDK environment:

   ```sh
   python3.12 -m venv /opt/context-research/codex-venv
   /opt/context-research/codex-venv/bin/python -m pip install --require-hashes --only-binary=:all: -r /srv/context-research/release/researcher/service/deploy/requirements-codex-linux.txt
   /opt/context-research/codex-venv/bin/python -m pip check
   ```

   Provision an identical lock at `/opt/context-research/requirements-codex-linux.txt`.
   Set `RESEARCH_CODEX_PYTHON=/opt/context-research/codex-venv/bin/python` and
   `RESEARCH_CODEX_DEPENDENCY_LOCK=/opt/context-research/requirements-codex-linux.txt`
   in reviewed `release.env`. Run the [actual runtime and loopback integration
   gates](deploy/CODEX_RUNTIME.md). The launcher requires this SDK lock even when
   optional MCP is disabled. The lock covers CPython 3.12 Linux ARM64 and AMD64.

   The existing lock includes validation dependencies that are broader than a
   minimal service environment. Reusing one audited lock avoids inventing a
   second unresolved dependency set. A smaller separately generated runtime lock
   is an optimization requiring equivalent import and validation tests.

   For a deployment that will use registered MCP tools, install **both** locks
   together into the clean venv instead of the core-only install command:

   ```sh
   /opt/context-research/venv/bin/python -m pip install --require-hashes --only-binary=:all: -r /srv/context-research/release/requirements-dev.txt -r /srv/context-research/release/researcher/service/requirements-mcp.txt
   /opt/context-research/venv/bin/python -m pip check
   ```

   Copy the exact optional lock to `/opt/context-research/requirements-mcp.txt`,
   alongside the mandatory core lock. Set `RESEARCH_INSTALL_MCP=1` and
   `RESEARCH_MCP_DEPENDENCY_LOCK=/opt/context-research/requirements-mcp.txt` in
   the shared `release.env`. Core-only native installs leave both MCP variables
   unset. The optional profile pins `mcp==1.30.0` and `httpx==0.28.1`; the bridge
   requires protocol revision `2025-11-25`. Installing these packages does not
   enable any MCP registration or bypass its endpoint, schema, credential or
   budget checks. Do not upgrade the SDK independently of the reviewed lock and
   protocol contract. Run the real-SDK mocked-transport suite with the optional
   profile; passing it does not establish interoperability with a live server.
4. Prepare `/etc/context-research/service.json` as retrieval-only configuration
   with credential **variable names**, finite source budgets and schedules.
   Prepare the schedule-to-skill organization policy and bind the **existing**
   cumulative OpenAI authority. Use [Organization](ORGANIZATION.md) and its
   systemd unit, not the retired native model workflow. Model/pricing identity
   belongs to `CodexCampaign`; review its expiring conservative price policy
   and account availability before activation.
5. Supply `release.env` with the approved `RESEARCH_RELEASE_COMMIT`, `worker.env`
   with only the configured provider/tool/GitHub credentials, and `operator.env`
   with only `RESEARCH_OPERATOR_TOKEN`. These private files must not be committed.
   Keep credential environment files root-owned mode `0600`; make only the JSON
   configuration readable by the service group (for example root:context-research
   mode `0640` under a mode `0750` configuration directory).
   Prefer a host/cloud secret agent that renders root-only files at activation;
   such secret-agent integration is not implemented here. The service currently
   consumes named environment values, not systemd credential files directly.
6. Initialize a **new** `0700` state directory as UID 10001 using the same launcher,
   release/config environment and `init --config ... --state ... --repo ...`.
   Initialization makes no provider call. Do not silently initialize over old state.
7. Run the release's unit/integration suite and verify these units on the chosen
   Linux/systemd version before installation:

   ```sh
   systemd-analyze verify researcher/service/deploy/context-research.service researcher/service/deploy/context-research-api.service
   ```

8. Install/enable units only after operator approval and passing canaries. The
   coordinator's `ExecStart` deliberately contains `--live`: starting that unit
   is a real source/model execution action, not a preview. Keep GitHub publishing
   and notification disabled for the initial provider canary.

The units use a static user, `ProtectSystem=strict`, read-only source/config,
private temporary directories, empty capabilities, restricted address families
and process/memory/CPU ceilings. These are containment proposals, not measured
capacity recommendations. Coordinator limits are 2 GiB RAM, 64 tasks and up to
two CPU cores; API limits are 256 MiB, 32 tasks and one quarter of a core. Measure
memory, queue latency and stalls before tightening or increasing them.

An operator can inspect status and job effects with the CLI or inspect structured
service output through journald. Keep logs private and configure retention at the
host layer. An alive API is not proof of research progress; monitor last event,
last successful cycle, unresolved effects, queue age, disk space and reserved
cost. These external alerts are not provisioned by the supplied units.

### Funded organization unit

Use [context-research-organization.service](deploy/context-research-organization.service)
**instead of** `context-research.service` for the shared-budget pipeline. The
units conflict deliberately; do not run both or add cron. The same release
launcher has one explicit `organization` selector and performs the same
nonroot, clean-release, dependency-lock and exact-HEAD preflight before either
runtime. This does not bypass the release requirements above.

Prepare these separate private locations before activation:

| Path | Role |
| --- | --- |
| `/etc/context-research/retrieval.json` | Retrieval-only schedules, bounded source requests, no model roles or GitHub writes |
| `/etc/context-research/organization.json` | Exact schedule-to-skill policy and finite cycle/evaluation bounds |
| `/etc/context-research/provider-literals.env` | Service-UID-owned mode `0600`, strict literal env syntax, only required source/OpenAI keys; read-only to the running unit |
| `/var/lib/context-research/retrieval` | Existing initialized source Store |
| `/var/lib/context-research/authority` | The one existing cumulative OpenAI authority, including prior and unresolved reservations |
| `/var/lib/context-research/organization` | Initialized organization manifest, job receipts and private pipeline directories |

The literal env file differs from systemd `EnvironmentFile`: it is read through
the strict application parser, not sourced or expanded, and provider keys are
not inherited by trusted candidate-validation subprocesses. A root-owned `0600`
file cannot be read by the service; provision this particular file as UID 10001
under the protected configuration directory, then mount/configure it read-only.
Keep the operator credential separate. Do not put keys in command arguments.

The supplied unit has no evaluation dataset. To run an independently reviewed
dataset, add its explicit `--dataset` argument during configuration **before**
organization initialization and bind those same bytes in its manifest. Never
default to public fixtures in unattended operation. A source or implementation
upgrade requires review of the bound organization state, not silent resumption
under different code.

Run `organization init`, `organization status`, then one explicit
`organization serve ... --live --env-file ... --max-cycles 1` using the argument
paths from the unit before enabling its recurring foreground process. `init`
does not initialize the source Store or budget authority. Moving the funded
authority to a cloud host requires original-writer fencing and verified
preservation of all reservations; a new host is not a new $100 authorization.
Exercise pause/restart and inspect the retained pipeline outcome before enabling
the unit. The organization directory and its pipeline artifacts are distinct
from the source Store and must be included in the selected host's encrypted,
quiesced backup plan; the Store recovery profile alone is not their backup.

The loopback API template's default state path targets the older single Store.
For this layout, explicitly configure its read-only status view with the
retrieval config and `/var/lib/context-research/retrieval`. Use organization
`status` and campaign `status` for combined progress and cumulative spending;
the Control Center's Store view is not a merged organization projection.
Public UI ingress and remote command authority are not enabled by this unit.

## Container runtime option

[Dockerfile](deploy/Dockerfile) creates a **runtime/dependency image**, not a
self-contained source release. It contains Python, Git, hash-locked dependencies
and the launcher. The actual service code, schemas, skills and `.git` come from
the approved read-only `/repo` mount. The image digest therefore does not attest
the source closure: record both image and release identities.

`BASE_IMAGE` has no default. Supply a reviewed official Python reference matching
`python:3.12.<patch>-slim-bookworm@sha256:<64 lowercase hex characters>`. Resolve
and audit its actual digest for the target architecture; no fictitious pin is
provided. The base tag **and** digest are required. Apt-installed packages are
resolved at image-build time, so retain the resulting image digest and package
inventory; fully reproducible OS package resolution is not yet implemented.

`INSTALL_MCP` accepts exactly `0` or `1` and defaults to `0`. The default installs
only the core dependencies. `1` installs the core and optional MCP lock together
with `--require-hashes --only-binary=:all:`, then runs `pip check`. Both lockfiles
are included in both image profiles and checked against the mounted release;
the optional file's presence does not mean its packages were installed. The
image records the selected value as `RESEARCH_INSTALL_MCP` and supplies
`RESEARCH_MCP_DEPENDENCY_LOCK`. Do not override those values to bypass preflight.
Retain the profile with the image identity in release evidence. A profile change
requires rebuilding the image, not installing dependencies into a running worker.

Build from a sanitized review clone. The Dockerfile-specific
[ignore file](deploy/Dockerfile.dockerignore) excludes the repository except for
the two dependency locks and deployment build inputs. Never replace it with a broad
`COPY .` or send a private development tree to a remote builder. Docker documents
[digest pinning](https://docs.docker.com/build/building/best-practices/#pin-base-image-versions)
and [Dockerfile-specific context exclusions](https://docs.docker.com/build/concepts/context/#dockerignore-files).

```sh
# Set RESEARCH_BASE_IMAGE and RESEARCH_RUNTIME_IMAGE to reviewed references first.
docker build --build-arg "BASE_IMAGE=${RESEARCH_BASE_IMAGE:?reviewed base tag and digest required}" --tag "${RESEARCH_RUNTIME_IMAGE:?output image reference required}" --file researcher/service/deploy/Dockerfile .
```

For the optional MCP profile, add `--build-arg INSTALL_MCP=1` to that build
command and assign a distinct reviewed output image reference. The September 29
ARM64 MCP-enabled image build and network-disabled dependency smoke passed;
see the [exercise record](../../docs/product/production-exercise-2026-09-29.md)
for exact base/image digests and scope. That image test did not mount a release
or start a research worker.

Run the resulting reviewed image as UID/GID `10001:10001` with:

- Read-only root filesystem, all capabilities dropped and no-new-privileges.
- Read-only mounts for the complete release at `/repo` and approved config at
  `/config`; a separately provisioned local persistent state mount at `/state`
  owned by UID 10001 with mode `0700`.
- A bounded service-only tmpfs at `/tmp`, PID and memory limits, and an init/reaper.
- Explicit `RESEARCH_RELEASE_COMMIT`, provider credential variables from the
  selected secret mechanism, and no build-time secrets.
- `status`/`init` before `serve ... --live`. The default image command is `status`,
  not activation. The read-only mount and mandatory release checks intentionally
  make an unconfigured image fail closed.

Example argument form after volumes and credentials are provisioned:

```text
IMAGE init --config /config/service.json --state /state --repo /repo
IMAGE status --config /config/service.json --state /state --repo /repo
IMAGE serve --config /config/service.json --state /state --repo /repo --live
IMAGE api --config /config/service.json --state /state --repo /repo --host 127.0.0.1 --port 8787
```

The API and coordinator are separate processes; starting `serve` does not start
`api`. For this initial UI bridge, native processes on one VM are simpler than
container networking. A Linux host-network container is an explicit option for
shared loopback, but increases host-network exposure and is not a portable
Docker Desktop recipe. No cloud or public-network port mapping is recommended
without the missing ingress review. Never run two `serve` instances against
different copies of what is intended to be one state store.

## Credentials and effect activation

Use narrowly scoped provider credentials and a GitHub App installation token for
one approved repository. Secret expiry/rotation and App-token minting must be
supplied by the deployment; the current adapter accepts an explicit token, not an
automatically refreshed installation identity. The API needs a separate strong
operator token. It must not receive model/GitHub credentials merely for status.

The sample native units rely on root-controlled environment files as an interim
integration. They do not claim the stronger properties of systemd
[credential passing](https://systemd.io/CREDENTIALS/). Environment secrets remain
visible to appropriately privileged same-host processes; this is a trusted
single-tenant runtime, not isolation for adversarial agent-generated code.

Keep candidate execution data-only. No generated Python/shell, unregistered MCP
server, Docker socket or ambient developer settings are permitted. Native model
workers have deadlines, but that boundary is not a general executable sandbox.
The GitHub adapter creates a new branch and draft PR; it never merges, force-pushes,
releases or edits repository settings. Initial notification delivery and provider
calls must each be tested against explicitly approved accounts/destinations.

## Recovery and release blockers

The current `backup` command is an **inspection-only database copy**. It does not
include transitive artifacts, encrypted off-host retention, restored credential
boundaries or a tested live recovery procedure. **Do not restore that copy into a
live worker or describe it as disaster recovery.** A whole-volume copy without a
verified consistency barrier is not an acceptable substitute.

Unknown external effects remain reserved and require reconciliation. Restart is
not permission to retry an unacknowledged model request, branch, PR or notification.
There is no supported one-command recovery that erases unknown outcomes. Pause
admission, stop effect execution, inspect provider/GitHub receipts and preserve
the state lineage. The documented production restore gate remains blocked.

Before a release candidate can be called operationally ready, obtain evidence for:

1. Clean reviewed source closure, exact runtime/dependency/image identities and
   a reproducible installation on the chosen Linux platform.
2. Real provider/source/MCP canaries with cost ceilings and fault cases, followed
   by a draft-PR/notification canary in an approved repository.
3. Actual restart, process-kill, duplicate admission and unknown-effect tests on
   the deployment, not only injected adapter tests.
4. TLS/operator identity, egress policy, secret rotation, alerting and disk/log
   management appropriate to the selected host.
5. Encrypted complete backups and an independently verified isolated restore with
   artifact closure and effect reconciliation. Recovery objectives remain unset.
6. Independent scientific evaluation before accepting or promoting skill changes.

Upgrading source, configuration or schemas is a release operation. Stop the
coordinator before replacing the read-only release mount; retain prior images
and source identities. Configuration-digest changes currently require an explicit
migration. Do not delete the database to bypass that gate. Do not roll back code
over a forward-only schema or discard events accepted after a snapshot.

## Verification status

The actual MCP-enabled Docker build on Linux ARM64 passed after correcting a
shared dependency conflict. A read-only, nonroot, network-disabled container
verified imports, both embedded locks and `pip check`, without source, state,
credentials or published ports. The original failed build remains documented;
CI now resolves both locks in one transaction, and a regression test rejects
conflicting shared pins.

The [exercise record](../../docs/product/production-exercise-2026-09-29.md)
contains exact image identity and measurements. That initial check did not execute
the source release. Subsequent [SDK verification](../../docs/product/codex-sdk-migration-verification-2026-09-29.md)
records actual tool-free SDK source tests on ARM64 and AMD64, separately from
native-tool sandbox failures. Systemd units have not been activated/validated on
a target Linux host, and no cloud deployment was performed. Image
vulnerability review, Linux unit validation and hosted canary/soak results remain
separate release evidence. Do not generalize dependency-image success to those
untested boundaries.
