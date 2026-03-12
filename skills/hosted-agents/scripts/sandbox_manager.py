"""
Sandbox Manager for Hosted Agent Infrastructure

This module demonstrates patterns for managing sandboxed agent execution
environments with pre-built images, warm pools, and session snapshots.

Note: This is pseudocode demonstrating concepts. Adapt for your specific
infrastructure (Modal, Fly.io, etc.).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from enum import Enum
import asyncio


class SandboxState(Enum):
    """Sandbox lifecycle states."""
    CREATING = "creating"
    SYNCING = "syncing"
    READY = "ready"
    EXECUTING = "executing"
    SNAPSHOTTING = "snapshotting"
    TERMINATED = "terminated"


@dataclass
class UserIdentity:
    """User identity for commit attribution."""
    id: str
    name: str
    email: str
    github_token: str


@dataclass
class SandboxConfig:
    """Configuration for sandbox creation."""
    repo_url: str
    base_image: str
    memory_mb: int = 4096
    cpu_cores: int = 2
    disk_gb: int = 10
    timeout_hours: int = 4


@dataclass
class Sandbox:
    """Represents a sandboxed execution environment."""
    id: str
    config: SandboxConfig
    state: SandboxState
    created_at: datetime
    snapshot_id: Optional[str] = None
    current_user: Optional[UserIdentity] = None
    
    # Event handlers
    on_state_change: Optional[Callable[[SandboxState], None]] = None
    
    async def execute_command(self, command: str) -> dict:
        """Execute a command in the sandbox."""
        # Implementation depends on infrastructure
        # Returns {"stdout": str, "stderr": str, "exit_code": int}
        pass
    
    async def read_file(self, path: str) -> str:
        """Read a file from the sandbox filesystem."""
        pass
    
    async def write_file(self, path: str, content: str) -> None:
        """Write a file to the sandbox filesystem."""
        pass
    
    async def snapshot(self) -> str:
        """Create a snapshot of current filesystem state."""
        self.state = SandboxState.SNAPSHOTTING
        # Create snapshot and return ID
        snapshot_id = await self._create_snapshot()
        self.snapshot_id = snapshot_id
        self.state = SandboxState.READY
        return snapshot_id
    
    async def restore(self, snapshot_id: str) -> None:
        """Restore sandbox to a previous snapshot."""
        pass
    
    async def terminate(self) -> None:
        """Terminate the sandbox."""
        self.state = SandboxState.TERMINATED


@dataclass  
class RepositoryImage:
    """Pre-built image for a repository."""
    repo_url: str
    image_id: str
    commit_sha: str
    built_at: datetime
    
    def is_stale(self, max_age: timedelta = timedelta(minutes=30)) -> bool:
        """Check if image is older than max age."""
        return datetime.utcnow() - self.built_at > max_age


class ImageBuilder:
    """Builds and manages repository images."""
    
    def __init__(self, github_app_token_provider: Callable[[], str]):
        self.token_provider = github_app_token_provider
        self.images: dict[str, RepositoryImage] = {}
    
    async def build_image(self, repo_url: str) -> RepositoryImage:
        """Build a new image for a repository."""
        print(f"Building image for {repo_url}...")
        
        # Get fresh token for clone
        token = self.token_provider()
        
        # These operations run in build environment
        build_steps = [
            # Clone repository
            f"git clone https://x-access-token:{token}@github.com/{repo_url} /workspace",
            
            # Install dependencies
            "cd /workspace && npm install",
            
            # Run build
            "cd /workspace && npm run build",
            
            # Warm caches by running once
            "cd /workspace && npm run dev &",
            "sleep 5",  # Let dev server start
            "cd /workspace && npm test -- --run || true",  # Run tests to warm cache
        ]
        
        # Execute build steps (infrastructure-specific)
        for step in build_steps:
            await self._execute_build_step(step)
        
        # Get current commit
        commit_sha = await self._get_commit_sha()
        
        # Create and store image
        image = RepositoryImage(
            repo_url=repo_url,
            image_id=await self._finalize_image(),
            commit_sha=commit_sha,
            built_at=datetime.utcnow()
        )
        
        self.images[repo_url] = image
        return image
    
    def get_latest_image(self, repo_url: str) -> Optional[RepositoryImage]:
        """Get the most recent image for a repository."""
        return self.images.get(repo_url)
    
    async def _execute_build_step(self, command: str) -> None:
        """Execute a build step (infrastructure-specific)."""
        pass
    
    async def _get_commit_sha(self) -> str:
        """Get current HEAD commit SHA."""
        pass
    
    async def _finalize_image(self) -> str:
        """Finalize and store the image, return image ID."""
        pass


@dataclass
class WarmSandbox:
    """A pre-warmed sandbox ready for use."""
    sandbox: Sandbox
    repo_url: str
    created_at: datetime
    image_version: str
    is_claimed: bool = False
    sync_complete: bool = False


class WarmPoolManager:
    """Manages pools of pre-warmed sandboxes."""
    
    def __init__(
        self,
        image_builder: ImageBuilder,
        target_pool_size: int = 3,
        max_age: timedelta = timedelta(minutes=25)
    ):
        self.image_builder = image_builder
        self.target_size = target_pool_size
        self.max_age = max_age
        self.pools: dict[str, list[WarmSandbox]] = {}
    
    async def get_warm_sandbox(self, repo_url: str) -> Optional[WarmSandbox]:
        """Get a pre-warmed sandbox if available."""
        if repo_url not in self.pools:
            return None
        
        for warm in self.pools[repo_url]:
            if not warm.is_claimed and self._is_valid(warm):
                warm.is_claimed = True
                return warm
        
        return None
    
    def _is_valid(self, warm: WarmSandbox) -> bool:
        """Check if a warm sandbox is still valid."""
        age = datetime.utcnow() - warm.created_at
        if age > self.max_age:
            return False
        
        # Check if image is still current
        current = self.image_builder.get_latest_image(warm.repo_url)
        if not current or current.image_id != warm.image_version:
            return False
        
        return True
    
    async def maintain_pool(self, repo_url: str) -> None:
        """Ensure pool has target number of warm sandboxes."""
        if repo_url not in self.pools:
            self.pools[repo_url] = []
        
        # Remove invalid sandboxes
        valid = [w for w in self.pools[repo_url] if self._is_valid(w)]
        self.pools[repo_url] = valid
        
        # Count available (unclaimed) sandboxes
        available = len([w for w in valid if not w.is_claimed])
        needed = self.target_size - available
        
        # Create new warm sandboxes
        for _ in range(max(0, needed)):
            warm = await self._create_warm_sandbox(repo_url)
            self.pools[repo_url].append(warm)
    
    async def _create_warm_sandbox(self, repo_url: str) -> WarmSandbox:
        """Create a new warm sandbox."""
        image = self.image_builder.get_latest_image(repo_url)
        if not image:
            raise ValueError(f"No image available for {repo_url}")
        
        # Create sandbox from image
        sandbox = await self._create_sandbox_from_image(image)
        
        warm = WarmSandbox(
            sandbox=sandbox,
            repo_url=repo_url,
            created_at=datetime.utcnow(),
            image_version=image.image_id,
            sync_complete=False
        )
        
        # Start syncing to latest in background
        asyncio.create_task(self._sync_to_latest(warm))
        
        return warm
    
    async def _sync_to_latest(self, warm: WarmSandbox) -> None:
        """Sync sandbox to latest commit on base branch."""
        await warm.sandbox.execute_command("git fetch origin main")
        await warm.sandbox.execute_command("git reset --hard origin/main")
        warm.sync_complete = True
    
    async def _create_sandbox_from_image(self, image: RepositoryImage) -> Sandbox:
        """Create a sandbox from an image (infrastructure-specific)."""
        pass


class SandboxManager:
    """
    Main manager for sandbox lifecycle.
    
    Coordinates image building, warm pools, and session management.
    """
    
    def __init__(
        self,
        repositories: list[str],
        github_app_token_provider: Callable[[], str],
        build_interval: timedelta = timedelta(minutes=30)
    ):
        self.repositories = repositories
        self.image_builder = ImageBuilder(github_app_token_provider)
        self.warm_pool = WarmPoolManager(self.image_builder)
        self.build_interval = build_interval
        self.active_sessions: dict[str, Sandbox] = {}
    
    async def start_build_loop(self) -> None:
        """Start the background image build loop."""
        while True:
            for repo in self.repositories:
                try:
                    await self.image_builder.build_image(repo)
                    await self.warm_pool.maintain_pool(repo)
                except Exception as e:
                    print(f"Failed to build {repo}: {e}")
            
            await asyncio.sleep(self.build_interval.total_seconds())
    
    async def start_session(
        self,
        repo_url: str,
        user: UserIdentity,
        snapshot_id: Optional[str] = None
    ) -> Sandbox:
        """Start a new session for a user."""
        
        # Try to get from warm pool first
        warm = await self.warm_pool.get_warm_sandbox(repo_url)
        
        if warm:
            sandbox = warm.sandbox
            # Wait for sync if not complete
            if not warm.sync_complete:
                await self._wait_for_sync(warm)
        elif snapshot_id:
            # Restore from previous session snapshot
            sandbox = await self._restore_from_snapshot(snapshot_id)
        else:
            # Cold start from latest image
            sandbox = await self._cold_start(repo_url)
        
        # Configure for user
        await self._configure_for_user(sandbox, user)
        
        # Track session
        session_id = f"{user.id}_{datetime.utcnow().isoformat()}"
        self.active_sessions[session_id] = sandbox
        
        return sandbox
    
    async def on_user_typing(self, user: UserIdentity, repo_url: str) -> None:
        """
        Called when user starts typing a prompt.
        
        Predictively warms a sandbox so it's ready when they submit.
        """
        # Check if we have a warm sandbox available
        warm = await self.warm_pool.get_warm_sandbox(repo_url)
        
        if not warm:
            # Start warming one now
            asyncio.create_task(self.warm_pool.maintain_pool(repo_url))
    
    async def end_session(self, session_id: str) -> Optional[str]:
        """End a session and return snapshot ID for potential follow-up."""
        if session_id not in self.active_sessions:
            return None
        
        sandbox = self.active_sessions[session_id]
        
        # Create snapshot before terminating
        snapshot_id = await sandbox.snapshot()
        
        # Terminate sandbox
        await sandbox.terminate()
        
        del self.active_sessions[session_id]
        
        return snapshot_id
    
    async def _configure_for_user(
        self,
        sandbox: Sandbox,
        user: UserIdentity
    ) -> None:
        """Configure sandbox for a specific user."""
        sandbox.current_user = user
        
        # Set git identity
        await sandbox.execute_command(
            f'git config user.name "{user.name}"'
        )
        await sandbox.execute_command(
            f'git config user.email "{user.email}"'
        )
    
    async def _wait_for_sync(self, warm: WarmSandbox) -> None:
        """Wait for sync to complete."""
        while not warm.sync_complete:
            await asyncio.sleep(0.1)
    
    async def _restore_from_snapshot(self, snapshot_id: str) -> Sandbox:
        """Restore a sandbox from a snapshot."""
        pass
    
    async def _cold_start(self, repo_url: str) -> Sandbox:
        """Start a sandbox from cold (no warm pool available)."""
        pass


class AgentSession:
    """
    Represents an agent session with file read/write coordination.
    
    Implements the pattern where reads are allowed before sync completes,
    but writes are blocked until sync is done.
    """
    
    def __init__(self, sandbox: Sandbox):
        self.sandbox = sandbox
        self.sync_complete = False
        self.pending_writes: list[tuple[str, str]] = []
    
    async def read_file(self, path: str) -> str:
        """
        Read a file - allowed even before sync completes.
        
        In large repos, files being worked on are unlikely to have
        changed in the last 30 minutes since image build.
        """
        return await self.sandbox.read_file(path)
    
    async def write_file(self, path: str, content: str) -> None:
        """
        Write a file - blocks until sync is complete.
        
        This prevents writing to files that might be updated by sync.
        """
        if not self.sync_complete:
            # Queue the write
            self.pending_writes.append((path, content))
            await self._wait_for_sync()
            return
        
        await self.sandbox.write_file(path, content)
    
    def mark_sync_complete(self) -> None:
        """Called when git sync is complete."""
        self.sync_complete = True
    
    async def _wait_for_sync(self) -> None:
        """Wait for sync to complete, then flush pending writes."""
        while not self.sync_complete:
            await asyncio.sleep(0.1)
        
        # Flush pending writes
        for path, content in self.pending_writes:
            await self.sandbox.write_file(path, content)
        self.pending_writes.clear()


# Example usage
async def main():
    """Example of using the sandbox manager."""
    
    def get_github_token() -> str:
        """Get GitHub App installation token."""
        # Implementation: call GitHub API to get installation token
        return "ghs_xxxx"
    
    manager = SandboxManager(
        repositories=[
            "myorg/frontend",
            "myorg/backend",
            "myorg/shared-libs"
        ],
        github_app_token_provider=get_github_token
    )
    
    # Start background build loop
    asyncio.create_task(manager.start_build_loop())
    
    # Simulate user session
    user = UserIdentity(
        id="user123",
        name="Alice Developer",
        email="alice@example.com",
        github_token="gho_user_token"
    )
    
    # User starts typing - predictively warm
    await manager.on_user_typing(user, "myorg/frontend")
    
    # User submits prompt - get sandbox
    sandbox = await manager.start_session("myorg/frontend", user)
    
    # Create session wrapper for read/write coordination
    session = AgentSession(sandbox)
    
    # Agent can read immediately
    readme = await session.read_file("/workspace/README.md")
    
    # Agent work happens here...
    
    # End session and get snapshot for follow-up
    snapshot_id = await manager.end_session(f"{user.id}_{sandbox.created_at}")
    print(f"Session ended, snapshot: {snapshot_id}")


if __name__ == "__main__":
    asyncio.run(main())
