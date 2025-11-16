"""Hook-specific test helpers."""

from pathlib import Path

from tests.fixtures.service_builders import MockServices


def assert_hook_called_with(
    services: MockServices,
    expected_global_scripts: list[str],
    expected_project_scripts: list[str],
    expected_hook_type: str,
    expected_worktree_dir: Path,
    expected_repo_dir: Path,
    expected_branch: str,
    call_index: int = 0,
) -> None:
    """Assert that hooks.run_hooks was called with expected parameters.

    Args:
        services: MockServices instance
        expected_global_scripts: Expected global scripts list
        expected_project_scripts: Expected project scripts list
        expected_hook_type: Expected hook type
        expected_worktree_dir: Expected worktree directory
        expected_repo_dir: Expected repo directory
        expected_branch: Expected branch name
        call_index: Which call to check (default: 0 for first call)

    Example:
        def test_hooks_called(mock_services):
            run_pre_create_hooks(mock_services, ...)

            from tests.helpers.services import assert_hook_called_with
            assert_hook_called_with(
                mock_services,
                ["echo 'global'"],
                ["echo 'project'"],
                HookType.PRE_CREATE,
                Path("/worktree"),
                Path("/repo"),
                "my-branch",
            )
    """
    assert len(services.hooks.run_hooks_calls) > call_index, (
        f"Expected at least {call_index + 1} hook calls, "
        f"but got {len(services.hooks.run_hooks_calls)}"
    )

    call_args = services.hooks.run_hooks_calls[call_index]
    assert call_args[0] == expected_global_scripts, "Global scripts mismatch"
    assert call_args[1] == expected_project_scripts, "Project scripts mismatch"
    assert call_args[2] == expected_hook_type, "Hook type mismatch"
    assert call_args[3] == expected_worktree_dir, "Worktree dir mismatch"
    assert call_args[4] == expected_repo_dir, "Repo dir mismatch"
    assert call_args[5] == expected_branch, "Branch name mismatch"


def assert_hooks_not_called(services: MockServices) -> None:
    """Assert that hooks.run_hooks was never called.

    Args:
        services: MockServices instance

    Example:
        def test_no_hooks(mock_services):
            run_something_without_hooks(mock_services)

            from tests.helpers.services import assert_hooks_not_called
            assert_hooks_not_called(mock_services)
    """
    assert len(services.hooks.run_hooks_calls) == 0, (
        f"Expected no hook calls, but got {len(services.hooks.run_hooks_calls)}"
    )
