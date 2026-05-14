// Package config handles loading and merging configuration from
// global files, project files, environment variables, and CLI flags.
package config

import "github.com/irskep/autowt/internal/model"

// Config holds the fully resolved autowt configuration.
type Config struct {
	Terminal      TerminalConfig
	Worktree      WorktreeConfig
	Cleanup       CleanupConfig
	Scripts       ScriptsConfig
	Confirmations ConfirmationsConfig
}

// TerminalConfig controls terminal switching behavior.
type TerminalConfig struct {
	Mode      model.TerminalMode
	AlwaysNew bool
	Program   string // optional: force a specific terminal program
}

// WorktreeConfig controls worktree directory layout and behavior.
type WorktreeConfig struct {
	DirectoryPattern string
	AutoFetch        bool
	BranchPrefix     string // optional: prefix template for new branches
}

// CleanupConfig controls default cleanup behavior.
type CleanupConfig struct {
	DefaultMode model.CleanupMode
}

// ScriptsConfig holds lifecycle hook scripts and custom commands.
type ScriptsConfig struct {
	PreCreate       string
	PostCreate      string
	PostCreateAsync string
	SessionInit     string
	PreCleanup      string
	PostCleanup     string
	PreSwitch       string
	PostSwitch      string
	Custom          map[string]model.CustomScript
}

// ConfirmationsConfig controls which operations prompt for confirmation.
type ConfirmationsConfig struct {
	CleanupMultiple bool
	ForceOperations bool
}

// HookConfig is a hook-only view of configuration, used to prevent
// hook resolution from depending on unrelated runtime config.
type HookConfig struct {
	PreCreate       string
	PostCreate      string
	PostCreateAsync string
	SessionInit     string
	PreCleanup      string
	PostCleanup     string
	PreSwitch       string
	PostSwitch      string
}

// DefaultConfig returns a Config with built-in default values.
func DefaultConfig() Config {
	return Config{
		Terminal: TerminalConfig{
			Mode:      model.TerminalModeTab,
			AlwaysNew: false,
		},
		Worktree: WorktreeConfig{
			DirectoryPattern: "../{repo_name}-worktrees/{branch}",
			AutoFetch:        true,
		},
		Cleanup: CleanupConfig{
			DefaultMode: model.CleanupModeInteractive,
		},
		Scripts: ScriptsConfig{
			Custom: make(map[string]model.CustomScript),
		},
		Confirmations: ConfirmationsConfig{
			CleanupMultiple: true,
			ForceOperations: true,
		},
	}
}
