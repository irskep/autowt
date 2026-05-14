package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/irskep/autowt/internal/model"
	"github.com/spf13/cobra"
	"golang.org/x/term"
)

func newLsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:     "ls",
		Aliases: []string{"list", "ll"},
		Short:   "List all worktrees and their status",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runLs()
		},
	}
	return cmd
}

func runLs() error {
	a := newApp()

	repoPath, err := a.Git.FindRepoRoot("")
	if err != nil {
		return fmt.Errorf("not in a git repository")
	}

	worktrees, err := a.Git.ListWorktrees(repoPath)
	if err != nil {
		return err
	}

	if flagDebug {
		fmt.Println("  Debug Information:")
		fmt.Printf("    Config file: %s\n", a.Config.GlobalConfigFile)
		fmt.Printf("    Git repository root: %s\n", repoPath)
		fmt.Println()
	}

	if len(worktrees) == 0 {
		fmt.Println("  No worktrees found.")
		return nil
	}

	currentDir, _ := os.Getwd()
	currentWT := a.Git.GetCurrentWorktree(currentDir, worktrees)

	// Sort: primary first, then alphabetically by branch.
	sortWorktrees(worktrees)

	termWidth := 80
	if w, _, err := term.GetSize(int(os.Stdout.Fd())); err == nil && w > 0 {
		termWidth = w
	}

	fmt.Println("  Worktrees:")
	for _, wt := range worktrees {
		isCurrent := currentWT != nil && currentWT.Path == wt.Path
		line := formatWorktreeLine(wt, isCurrent, termWidth)
		fmt.Println(line)
	}
	fmt.Println()
	fmt.Println("Use 'autowt <branch>' to switch to a worktree or create a new one.")
	return nil
}

func sortWorktrees(wts []model.WorktreeInfo) {
	// Simple insertion sort (small lists).
	for i := 1; i < len(wts); i++ {
		for j := i; j > 0 && worktreeLess(wts[j], wts[j-1]); j-- {
			wts[j], wts[j-1] = wts[j-1], wts[j]
		}
	}
}

func worktreeLess(a, b model.WorktreeInfo) bool {
	if a.IsPrimary != b.IsPrimary {
		return a.IsPrimary
	}
	return a.Branch < b.Branch
}

func formatWorktreeLine(wt model.WorktreeInfo, isCurrent bool, termWidth int) string {
	displayPath := wt.DisplayPath()

	indicator := "  "
	if isCurrent {
		indicator = "→ "
	}
	left := indicator + displayPath

	mainTag := ""
	mainTagLen := 0
	if wt.IsPrimary {
		mainTag = " (main worktree)"
		mainTagLen = len(mainTag)
	}

	arrow := ""
	padding := "  "
	if isCurrent {
		arrow = " ←"
		padding = ""
	}
	right := wt.Branch + arrow + padding

	contentLen := len(left) + mainTagLen + len(right)
	minSpacing := 2

	if contentLen+minSpacing <= termWidth {
		gap := termWidth - contentLen
		return left + mainTag + strings.Repeat(" ", gap) + right
	}

	// Two-line format.
	line1 := left + mainTag
	line2 := "    " + wt.Branch
	return line1 + "\n" + line2
}
