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

// DisplayPath returns a human-friendly version of the worktree path,
// replacing the home directory prefix with ~.
func (w WorktreeInfo) DisplayPath() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return w.Path
	}
	rel, err := filepath.Rel(home, w.Path)
	if err != nil || strings.HasPrefix(rel, "..") {
		return w.Path
	}
	return "~/" + rel
}
