"""Tests for shell-init command."""

from autowt.commands.shell_init import get_shell_init_script


class TestGetShellInitScript:
    def test_bash_dry_run_prints_instead_of_eval(self):
        script = get_shell_init_script("bash", dry_run=True)
        assert "dry-run" in script
        assert "would eval" in script
        assert 'eval "$eval_cmd"' not in script

    def test_fish_dry_run_prints_instead_of_eval(self):
        script = get_shell_init_script("fish", dry_run=True)
        assert "dry-run" in script
        assert "would eval" in script
        assert "eval $eval_cmd" not in script

    def test_zsh_matches_bash(self):
        assert get_shell_init_script("bash") == get_shell_init_script("zsh")

    def test_unsupported_shell_raises(self):
        try:
            get_shell_init_script("powershell")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "powershell" in str(e)
