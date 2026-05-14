package config

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/irskep/autowt/internal/model"
)

func TestLoadDefaults(t *testing.T) {
	loader := &Loader{
		AppDir:           t.TempDir(),
		GlobalConfigFile: filepath.Join(t.TempDir(), "nonexistent.toml"),
	}

	cfg, err := loader.Load("", nil)
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}

	if cfg.Terminal.Mode != model.TerminalModeTab {
		t.Errorf("default terminal mode = %q, want tab", cfg.Terminal.Mode)
	}
	if cfg.Worktree.DirectoryPattern != "../{repo_name}-worktrees/{branch}" {
		t.Errorf("default directory pattern = %q", cfg.Worktree.DirectoryPattern)
	}
	if cfg.Cleanup.DefaultMode != model.CleanupModeInteractive {
		t.Errorf("default cleanup mode = %q, want interactive", cfg.Cleanup.DefaultMode)
	}
}

func TestLoadGlobalConfig(t *testing.T) {
	dir := t.TempDir()
	cfgFile := filepath.Join(dir, "config.toml")

	err := os.WriteFile(cfgFile, []byte(`
[terminal]
mode = "echo"
always_new = true

[worktree]
branch_prefix = "alice/"

[cleanup]
default_mode = "merged"
`), 0o644)
	if err != nil {
		t.Fatal(err)
	}

	loader := &Loader{AppDir: dir, GlobalConfigFile: cfgFile}
	cfg, err := loader.Load("", nil)
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}

	if cfg.Terminal.Mode != model.TerminalModeEcho {
		t.Errorf("terminal mode = %q, want echo", cfg.Terminal.Mode)
	}
	if !cfg.Terminal.AlwaysNew {
		t.Error("expected always_new = true")
	}
	if cfg.Worktree.BranchPrefix != "alice/" {
		t.Errorf("branch_prefix = %q, want alice/", cfg.Worktree.BranchPrefix)
	}
	if cfg.Cleanup.DefaultMode != model.CleanupModeMerged {
		t.Errorf("cleanup mode = %q, want merged", cfg.Cleanup.DefaultMode)
	}
}

func TestLoadProjectOverridesGlobal(t *testing.T) {
	globalDir := t.TempDir()
	globalFile := filepath.Join(globalDir, "config.toml")
	os.WriteFile(globalFile, []byte(`
[terminal]
mode = "tab"

[scripts]
session_init = "global-init"
`), 0o644)

	projectDir := t.TempDir()
	os.WriteFile(filepath.Join(projectDir, "autowt.toml"), []byte(`
[scripts]
session_init = "project-init"
`), 0o644)

	loader := &Loader{AppDir: globalDir, GlobalConfigFile: globalFile}
	cfg, err := loader.Load(projectDir, nil)
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}

	// Project overrides global.
	if cfg.Scripts.SessionInit != "project-init" {
		t.Errorf("session_init = %q, want project-init", cfg.Scripts.SessionInit)
	}
	// Global terminal mode preserved.
	if cfg.Terminal.Mode != model.TerminalModeTab {
		t.Errorf("terminal mode = %q, want tab", cfg.Terminal.Mode)
	}
}

func TestLoadEnvOverridesFile(t *testing.T) {
	dir := t.TempDir()
	cfgFile := filepath.Join(dir, "config.toml")
	os.WriteFile(cfgFile, []byte(`
[terminal]
mode = "tab"
`), 0o644)

	t.Setenv("AUTOWT_TERMINAL_MODE", "window")

	loader := &Loader{AppDir: dir, GlobalConfigFile: cfgFile}
	cfg, err := loader.Load("", nil)
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}

	if cfg.Terminal.Mode != model.TerminalModeWindow {
		t.Errorf("terminal mode = %q, want window (from env)", cfg.Terminal.Mode)
	}
}

func TestLoadCustomScripts(t *testing.T) {
	dir := t.TempDir()
	cfgFile := filepath.Join(dir, "config.toml")
	os.WriteFile(cfgFile, []byte(`
[scripts.custom]
release = "npm run release"

[scripts.custom.bugfix]
branch_name = "gh issue view $1"
session_init = "npm install"
description = "Fix a bug"
inherit_hooks = false
`), 0o644)

	loader := &Loader{AppDir: dir, GlobalConfigFile: cfgFile}
	cfg, err := loader.Load("", nil)
	if err != nil {
		t.Fatalf("Load() error: %v", err)
	}

	if len(cfg.Scripts.Custom) != 2 {
		t.Fatalf("expected 2 custom scripts, got %d", len(cfg.Scripts.Custom))
	}

	release := cfg.Scripts.Custom["release"]
	if release.SessionInit != "npm run release" {
		t.Errorf("release.SessionInit = %q", release.SessionInit)
	}

	bugfix := cfg.Scripts.Custom["bugfix"]
	if bugfix.Description != "Fix a bug" {
		t.Errorf("bugfix.Description = %q", bugfix.Description)
	}
	if bugfix.InheritHooks {
		t.Error("expected bugfix.InheritHooks = false")
	}
	if bugfix.BranchName != "gh issue view $1" {
		t.Errorf("bugfix.BranchName = %q", bugfix.BranchName)
	}
}

func TestSaveAndLoadCleanupMode(t *testing.T) {
	dir := t.TempDir()
	cfgFile := filepath.Join(dir, "config.toml")

	loader := &Loader{AppDir: dir, GlobalConfigFile: cfgFile}

	if loader.HasUserConfiguredCleanupMode() {
		t.Error("should not have configured cleanup mode initially")
	}

	err := loader.SaveCleanupMode(model.CleanupModeGitHub)
	if err != nil {
		t.Fatalf("SaveCleanupMode() error: %v", err)
	}

	if !loader.HasUserConfiguredCleanupMode() {
		t.Error("should have configured cleanup mode after save")
	}

	cfg, err := loader.Load("", nil)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.Cleanup.DefaultMode != model.CleanupModeGitHub {
		t.Errorf("cleanup mode = %q, want github", cfg.Cleanup.DefaultMode)
	}
}
