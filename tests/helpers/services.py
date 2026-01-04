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
    """Assert that hooks.run_hook was called with expected scripts.

    The implementation calls run_hook for each script individually (after merging
    global + project scripts). This helper verifies all expected scripts were called.

    Args:
        services: MockServices instance
        expected_global_scripts: Expected global scripts list
        expected_project_scripts: Expected project scripts list
        expected_hook_type: Expected hook type
        expected_worktree_dir: Expected worktree directory
        expected_repo_dir: Expected repo directory
        expected_branch: Expected branch name
        call_index: Unused, kept for backward compatibility

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
    expected_scripts = expected_global_scripts + expected_project_scripts
    assert len(services.hooks.run_hook_calls) >= len(expected_scripts), (
        f"Expected at least {len(expected_scripts)} hook calls, "
        f"but got {len(services.hooks.run_hook_calls)}"
    )

    # Verify each expected script was called with correct parameters
    for i, expected_script in enumerate(expected_scripts):
        call_args = services.hooks.run_hook_calls[i]
        assert call_args[0] == expected_script, f"Script mismatch at index {i}"
        assert call_args[1] == expected_hook_type, f"Hook type mismatch at index {i}"
        assert call_args[2] == expected_worktree_dir, f"Worktree dir mismatch at {i}"
        assert call_args[3] == expected_repo_dir, f"Repo dir mismatch at index {i}"
        assert call_args[4] == expected_branch, f"Branch name mismatch at index {i}"


def assert_hooks_not_called(services: MockServices) -> None:
    """Assert that hooks.run_hook was never called.

    Args:
        services: MockServices instance

    Example:
        def test_no_hooks(mock_services):
            run_something_without_hooks(mock_services)

            from tests.helpers.services import assert_hooks_not_called
            assert_hooks_not_called(mock_services)
    """
    assert len(services.hooks.run_hook_calls) == 0, (
        f"Expected no hook calls, but got {len(services.hooks.run_hook_calls)}"
    )
