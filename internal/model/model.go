// Package model defines shared types used across the autowt CLI.
package model

import (
	"os"
	"path/filepath"
	"strings"
)

// TerminalMode controls how worktree switches are presented to the user.
type TerminalMode string

const (
	TerminalModeTab     TerminalMode = "tab"
	TerminalModeWindow  TerminalMode = "window"
	TerminalModeInplace TerminalMode = "inplace"
	TerminalModeEcho    TerminalMode = "echo"
	TerminalModeVSCode  TerminalMode = "vscode"
	TerminalModeCursor  TerminalMode = "cursor"
)

// CleanupMode controls how worktrees are selected for cleanup.
type CleanupMode string

const (
	CleanupModeAll         CleanupMode = "all"
	CleanupModeRemoteless  CleanupMode = "remoteless"
	CleanupModeMerged      CleanupMode = "merged"
	CleanupModeInteractive CleanupMode = "interactive"
	CleanupModeGitHub      CleanupMode = "github"
)

// WorktreeInfo describes a single git worktree.
type WorktreeInfo struct {
	Branch    string
	Path      string
	IsCurrent bool
	IsPrimary bool
}

// BranchStatus holds analysis results used by the cleanup command.
type BranchStatus struct {
	Branch                string
	HasRemote             bool
	IsMerged              bool
	IsIdentical           bool
	Path                  string
	HasUncommittedChanges bool
}

// CustomScript defines a custom command with optional hook overrides.
type CustomScript struct {
	Description      string
	BranchName       string // shell command whose stdout becomes the branch
	InheritHooks     bool
	PreCreate        string
	PostCreate       string
	PostCreateAsync  string
	SessionInit      string
	PreCleanup       string
	PostCleanup      string
	PreSwitch        string
	PostSwitch       string
}

// DisplayPath returns a human-friendly version of the worktree path.
func (w WorktreeInfo) DisplayPath() string {
	return FormatPath(w.Path)
}

// FormatPath returns a human-friendly path, replacing the home directory
// prefix with ~ and preferring relative paths from cwd.
func FormatPath(path string) string {
	// Try relative to cwd first.
	if cwd, err := os.Getwd(); err == nil {
		if rel, err := filepath.Rel(cwd, path); err == nil && !strings.HasPrefix(rel, "..") {
			return rel
		}
	}
	// Try relative to home.
	if home, err := os.UserHomeDir(); err == nil {
		if rel, err := filepath.Rel(home, path); err == nil && !strings.HasPrefix(rel, "..") {
			return "~/" + rel
		}
	}
	return path
}
