"""Tests for worktree path generation with custom directory patterns."""

from pathlib import Path
from unittest.mock import Mock, patch

from autowt.commands.checkout import _generate_worktree_path
from autowt.config import Config, WorktreeConfig
from autowt.models import WorktreeInfo


class TestWorktreePathGeneration:
    """Tests for worktree path generation using directory patterns."""

    def test_uses_default_directory_pattern(self):
        """Test that the function uses the default directory pattern correctly."""
        repo_path = Path("/home/user/Code/www/myprojectroot/base-repo")
        branch = "test-relative-pathing"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock default configuration
        default_config = Config()  # Uses default directory_pattern
        mock_state.load_config.return_value = default_config
        mock_services.state = mock_state

        # Mock the GitService to return a primary worktree
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should use default pattern: "../{repo_name}-worktrees/{branch}"
        # Pattern "../base-repo-worktrees" relative to "/myprojectroot/base-repo"
        # should resolve to "/myprojectroot/base-repo/../base-repo-worktrees" = "/myprojectroot/base-repo-worktrees"
        expected_path = Path(
            "/home/user/Code/www/myprojectroot/base-repo-worktrees/test-relative-pathing"
        )
        assert result_path == expected_path

    def test_uses_custom_directory_pattern(self):
        """Test that the function correctly uses custom directory_pattern configuration.

        This test verifies that the bug from GitHub issue #39 is fixed:
        https://github.com/irskep/autowt/issues/39

        When directory_pattern is set to "../worktrees/{branch}", the function should
        create paths like /parent/worktrees/branch-name.
        """
        repo_path = Path("/home/user/Code/www/myprojectroot/base-repo")
        branch = "test-relative-pathing"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock custom configuration
        custom_worktree_config = WorktreeConfig(
            directory_pattern="../worktrees/{branch}",
            auto_fetch=True,
        )
        custom_config = Config(worktree=custom_worktree_config)
        mock_state.load_config.return_value = custom_config
        mock_services.state = mock_state

        # Mock the GitService to return a primary worktree
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should use custom pattern: "../worktrees/{branch}"
        expected_path = Path(
            "/home/user/Code/www/myprojectroot/worktrees/test-relative-pathing"
        )
        assert result_path == expected_path

    def test_supports_repo_name_variable(self):
        """Test that {repo_name} variable is replaced correctly."""
        repo_path = Path("/home/user/Code/projects/my-awesome-project")
        branch = "feature-branch"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock default configuration (which uses {repo_name})
        default_config = Config()  # Uses "../{repo_name}-worktrees/{branch}"
        mock_state.load_config.return_value = default_config
        mock_services.state = mock_state

        # Mock the GitService
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should correctly replace {repo_name} with "my-awesome-project"
        # Pattern "../my-awesome-project-worktrees/feature-branch" relative to "/projects/my-awesome-project"
        # resolves to "/projects/my-awesome-project/../my-awesome-project-worktrees/feature-branch" = "/projects/my-awesome-project-worktrees/feature-branch"
        expected_path = Path(
            "/home/user/Code/projects/my-awesome-project-worktrees/feature-branch"
        )
        assert result_path == expected_path
        assert "my-awesome-project" in str(result_path)

    def test_supports_environment_variables(self):
        """Test that environment variables like $HOME are expanded correctly."""
        repo_path = Path("/home/user/Code/www/myprojectroot/base-repo")
        branch = "test-branch"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock configuration with environment variable
        custom_worktree_config = WorktreeConfig(
            directory_pattern="$HOME/worktrees/{repo_name}/{branch}",
            auto_fetch=True,
        )
        custom_config = Config(worktree=custom_worktree_config)
        mock_state.load_config.return_value = custom_config
        mock_services.state = mock_state

        # Mock the GitService
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
            patch.dict("os.environ", {"HOME": "/home/user"}),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should expand $HOME and use the pattern
        expected_path = Path("/home/user/worktrees/base-repo/test-branch")
        assert result_path == expected_path

    def test_handles_absolute_paths(self):
        """Test that absolute paths in directory_pattern work correctly."""
        repo_path = Path("/home/user/Code/www/myprojectroot/base-repo")
        branch = "test-branch"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock configuration with absolute path
        custom_worktree_config = WorktreeConfig(
            directory_pattern="/tmp/worktrees/{branch}",
            auto_fetch=True,
        )
        custom_config = Config(worktree=custom_worktree_config)
        mock_state.load_config.return_value = custom_config
        mock_services.state = mock_state

        # Mock the GitService
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should use absolute path directly
        expected_path = Path("/tmp/worktrees/test-branch")
        assert result_path == expected_path

    def test_supports_repo_parent_dir_variable(self):
        """Test that {repo_parent_dir} variable (parent directory) is replaced correctly."""
        repo_path = Path("/home/user/Code/projects/my-awesome-project")
        branch = "feature-branch"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock configuration using {repo_parent_dir} instead of relative paths
        custom_worktree_config = WorktreeConfig(
            directory_pattern="{repo_parent_dir}/worktrees/{branch}",
            auto_fetch=True,
        )
        custom_config = Config(worktree=custom_worktree_config)
        mock_state.load_config.return_value = custom_config
        mock_services.state = mock_state

        # Mock the GitService
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should use {repo_parent_dir} (parent directory) = "/home/user/Code/projects"
        expected_path = Path("/home/user/Code/projects/worktrees/feature-branch")
        assert result_path == expected_path

    def test_bare_repository_strips_git_suffix(self):
        """Test that bare repositories ending in .git have the suffix stripped from repo_name."""
        repo_path = Path("/scratch/demo/barerepo.git")
        branch = "foo"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock default configuration
        default_config = Config()  # Uses "../{repo_name}-worktrees/{branch}"
        mock_state.load_config.return_value = default_config
        mock_services.state = mock_state

        # Mock the GitService to return a primary worktree (bare repo itself)
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should strip .git suffix: barerepo.git -> barerepo
        # Pattern: "../barerepo-worktrees/foo"
        # Relative to: /scratch/demo/barerepo.git
        # Result: /scratch/demo/barerepo-worktrees/foo
        expected_path = Path("/scratch/demo/barerepo-worktrees/foo")
        assert result_path == expected_path

    def test_regular_repository_preserves_name(self):
        """Test that regular repositories (not ending in .git) preserve their full name."""
        repo_path = Path("/home/user/projects/my-project")
        branch = "feature"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock default configuration
        default_config = Config()  # Uses "../{repo_name}-worktrees/{branch}"
        mock_state.load_config.return_value = default_config
        mock_services.state = mock_state

        # Mock the GitService to return a primary worktree
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should preserve full name: my-project (no .git suffix to strip)
        # Pattern: "../my-project-worktrees/feature"
        expected_path = Path("/home/user/projects/my-project-worktrees/feature")
        assert result_path == expected_path

    def test_edge_case_repo_named_dot_git(self):
        """Test edge case where repository is literally named '.git'."""
        repo_path = Path("/home/user/weird/.git")
        branch = "test"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock default configuration
        default_config = Config()
        mock_state.load_config.return_value = default_config
        mock_services.state = mock_state

        # Mock the GitService
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should strip .git suffix: .git -> '' (empty string)
        # Pattern: "../-worktrees/test" (empty repo_name results in just "-worktrees")
        expected_path = Path("/home/user/weird/-worktrees/test")
        assert result_path == expected_path

    def test_edge_case_repo_ending_git_git(self):
        """Test edge case where repository ends in '.git.git'."""
        repo_path = Path("/home/user/repos/project.git.git")
        branch = "develop"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock default configuration
        default_config = Config()
        mock_state.load_config.return_value = default_config
        mock_services.state = mock_state

        # Mock the GitService
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should strip only the last .git suffix: project.git.git -> project.git
        # Pattern: "../project.git-worktrees/develop"
        expected_path = Path("/home/user/repos/project.git-worktrees/develop")
        assert result_path == expected_path

    def test_bare_repository_with_custom_pattern(self):
        """Test that bare repositories work correctly with custom directory patterns."""
        repo_path = Path("/srv/git/myapp.git")
        branch = "hotfix"

        # Create mock services
        mock_services = Mock()
        mock_state = Mock()

        # Mock custom configuration
        custom_worktree_config = WorktreeConfig(
            directory_pattern="{repo_parent_dir}/worktrees/{repo_name}/{branch}",
            auto_fetch=True,
        )
        custom_config = Config(worktree=custom_worktree_config)
        mock_state.load_config.return_value = custom_config
        mock_services.state = mock_state

        # Mock the GitService
        mock_worktree = WorktreeInfo(
            branch="main",
            path=repo_path,
            is_current=False,
            is_primary=True,
        )
        mock_services.git.list_worktrees.return_value = [mock_worktree]

        with (
            patch("autowt.commands.checkout.sanitize_branch_name", return_value=branch),
            patch("pathlib.Path.mkdir"),
        ):
            result_path = _generate_worktree_path(mock_services, repo_path, branch)

        # Should strip .git suffix and use custom pattern
        # repo_name: myapp.git -> myapp
        # repo_parent_dir: /srv/git
        # Pattern: "/srv/git/worktrees/myapp/hotfix"
        expected_path = Path("/srv/git/worktrees/myapp/hotfix")
        assert result_path == expected_path

    def test_custom_dir_absolute_path(self):
        """Test that custom_dir with absolute path overrides config pattern."""
        repo_path = Path("/home/user/Code/www/myprojectroot/base-repo")
        branch = "test-branch"
        custom_dir = "/tmp/my-custom-worktree"

        # Create mock services (shouldn't be called since custom_dir is provided)
        mock_services = Mock()

        with patch("pathlib.Path.mkdir"):
            result_path = _generate_worktree_path(
                mock_services, repo_path, branch, custom_dir
            )

        # Should use custom directory directly
        expected_path = Path("/tmp/my-custom-worktree")
        assert result_path == expected_path
        # Verify that config loading was not called since custom_dir was provided
        mock_services.state.load_config.assert_not_called()

    def test_custom_dir_relative_path(self):
        """Test that custom_dir with relative path works correctly."""
        repo_path = Path("/home/user/Code/www/myprojectroot/base-repo")
        branch = "test-branch"
        custom_dir = "my-worktree"

        # Create mock services (shouldn't be called since custom_dir is provided)
        mock_services = Mock()

        with (
            patch("pathlib.Path.mkdir"),
            patch("os.getcwd", return_value="/current/working/directory"),
        ):
            result_path = _generate_worktree_path(
                mock_services, repo_path, branch, custom_dir
            )

        # Should use custom directory relative to current working directory
        expected_path = Path("/current/working/directory/my-worktree")
        assert result_path == expected_path
        # Verify that config loading was not called since custom_dir was provided
        mock_services.state.load_config.assert_not_called()
