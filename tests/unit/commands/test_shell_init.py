"""Tests for shell-init command."""

from autowt.commands.shell_init import get_shell_init_script


class TestGetShellInitScript:
    def test_bash_contains_mktemp(self):
        script = get_shell_init_script("bash")
        assert "mktemp" in script

    def test_bash_contains_eval(self):
        script = get_shell_init_script("bash")
        assert "eval " in script
        assert "AUTOWT_SHELL_INTEGRATION_FILE" in script

    def test_bash_dry_run_prints_instead_of_eval(self):
        script = get_shell_init_script("bash", dry_run=True)
        assert "dry-run" in script
        assert "would eval" in script
        assert 'eval "$eval_cmd"' not in script

    def test_zsh_matches_bash(self):
        bash = get_shell_init_script("bash")
        zsh = get_shell_init_script("zsh")
        assert bash == zsh

    def test_zsh_dry_run_matches_bash_dry_run(self):
        bash = get_shell_init_script("bash", dry_run=True)
        zsh = get_shell_init_script("zsh", dry_run=True)
        assert bash == zsh

    def test_fish_contains_mktemp(self):
        script = get_shell_init_script("fish")
        assert "mktemp" in script

    def test_fish_uses_fish_syntax(self):
        script = get_shell_init_script("fish")
        assert "function autowt" in script
        assert "set -l tmpfile" in script
        assert "set -lx AUTOWT_SHELL_INTEGRATION_FILE" in script

    def test_fish_dry_run_prints_instead_of_eval(self):
        script = get_shell_init_script("fish", dry_run=True)
        assert "dry-run" in script
        assert "would eval" in script

    def test_fish_contains_eval(self):
        script = get_shell_init_script("fish")
        assert "eval " in script

    def test_bash_includes_awt_alias(self):
        script = get_shell_init_script("bash")
        assert "alias awt=autowt" in script

    def test_fish_includes_awt_wrapper(self):
        script = get_shell_init_script("fish")
        assert "function awt" in script

    def test_bash_cleans_up_tmpfile(self):
        script = get_shell_init_script("bash")
        assert "trap" in script
        assert "rm -f" in script

    def test_fish_cleans_up_tmpfile(self):
        script = get_shell_init_script("fish")
        assert "rm -f" in script

    def test_unsupported_shell_raises(self):
        try:
            get_shell_init_script("powershell")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "powershell" in str(e)
