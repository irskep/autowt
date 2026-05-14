package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/irskep/autowt/internal/hooks"
	"github.com/irskep/autowt/internal/model"
	"github.com/irskep/autowt/internal/prompt"
	"github.com/spf13/cobra"
	"golang.org/x/term"
)

func newCleanupCmd() *cobra.Command {
	var (
		flagMode   string
		flagDryRun bool
		flagForce  bool
	)

	cmd := &cobra.Command{
		Use:     "cleanup [worktrees...]",
		Aliases: []string{"cl", "clean", "prune", "rm", "remove", "del", "delete"},
		Short:   "Remove worktrees or clean up merged/remoteless ones",
		RunE: func(cmd *cobra.Command, args []string) error {
			return runCleanup(flagMode, flagDryRun, flagForce, args)
		},
	}

	cmd.Flags().StringVar(&flagMode, "mode", "", "Cleanup mode (all, remoteless, merged, interactive, github)")
	cmd.Flags().BoolVar(&flagDryRun, "dry-run", false, "Show what would be removed without actually removing")
	cmd.Flags().BoolVar(&flagForce, "force", false, "Force remove worktrees with modified files")

	return cmd
}

func runCleanup(modeStr string, dryRun, force bool, worktreeArgs []string) error {
	a := newApp()

	repoPath, err := a.Git.FindRepoRoot("")
	if err != nil {
		return fmt.Errorf("not in a git repository")
	}

	cfg, err := a.Config.Load(repoPath, nil)
	if err != nil {
		return err
	}
	projectHookCfg := a.Config.LoadProjectHookConfig(repoPath)

	// Determine mode.
	mode := model.CleanupMode(modeStr)
	if modeStr == "" {
		isTTY := term.IsTerminal(int(os.Stdin.Fd()))
		if !isTTY {
			return fmt.Errorf("no TTY detected. Please specify --mode explicitly when running in scripts or CI. Available modes: all, remoteless, merged, interactive, github")
		}

		if !a.Config.HasUserConfiguredCleanupMode() {
			// First-run prompt.
			fmt.Println("Select your default cleanup mode:")
			fmt.Println("  1. interactive - Choose which worktrees to remove")
			fmt.Println("  2. merged      - Remove branches merged into main")
			fmt.Println("  3. remoteless  - Remove branches without remote tracking")
			if a.GitHub.IsAvailable() {
				fmt.Println("  4. github      - Remove branches with merged/closed PRs")
			}
			fmt.Print("Choice [1]: ")
			var choice string
			fmt.Scanln(&choice)
			switch strings.TrimSpace(choice) {
			case "2":
				mode = model.CleanupModeMerged
			case "3":
				mode = model.CleanupModeRemoteless
			case "4":
				mode = model.CleanupModeGitHub
			default:
				mode = model.CleanupModeInteractive
			}
			fmt.Fprintf(os.Stderr, "\nSaving '%s' as your default cleanup mode...\n", mode)
			if err := a.Config.SaveCleanupMode(mode); err != nil {
				fmt.Fprintf(os.Stderr, "Warning: failed to save preference: %v\n", err)
			}
			fmt.Fprintln(os.Stderr, "You can change this later using 'autowt config' or by editing config.toml")
		} else {
			mode = cfg.Cleanup.DefaultMode
		}
	}

	// GitHub mode: check gh availability early.
	if mode == model.CleanupModeGitHub && !a.GitHub.IsAvailable() {
		return fmt.Errorf("GitHub cleanup requires the 'gh' CLI tool. Install it from: https://cli.github.com/")
	}

	// Fetch branches.
	fmt.Fprintln(os.Stderr, "Fetching branches...")
	if err := a.Git.FetchBranches(repoPath); err != nil {
		fmt.Fprintln(os.Stderr, "Warning: Failed to fetch latest branches")
	}

	fmt.Fprintln(os.Stderr, "Checking branch status...")

	worktrees, err := a.Git.ListWorktrees(repoPath)
	if err != nil {
		return err
	}

	// Filter out primary worktrees.
	var secondary []model.WorktreeInfo
	for _, wt := range worktrees {
		if wt.Path != repoPath && !wt.IsPrimary {
			secondary = append(secondary, wt)
		}
	}

	if len(secondary) == 0 {
		fmt.Fprintln(os.Stderr, "No secondary worktrees found.")
		return nil
	}

	// If specific worktrees were named, filter to those.
	if len(worktreeArgs) > 0 {
		secondary = filterWorktreesByArgs(secondary, worktreeArgs)
		if len(secondary) == 0 {
			return fmt.Errorf("none of the specified worktrees were found")
		}
	}

	// Analyze branches.
	var statuses []model.BranchStatus
	if mode == model.CleanupModeGitHub {
		statuses, err = a.GitHub.AnalyzeBranchesForCleanup(repoPath, secondary, func(path string) bool {
			return a.Git.HasUncommittedChanges(path)
		})
		if err != nil {
			return err
		}
	} else {
		statuses = a.Git.AnalyzeBranchesForCleanup(repoPath, secondary)
	}

	// Select branches for cleanup.
	toCleanup := selectBranchesForCleanup(mode, statuses)
	if len(toCleanup) == 0 {
		// Offer interactive fallback if in TTY.
		isTTY := term.IsTerminal(int(os.Stdin.Fd()))
		if mode != model.CleanupModeInteractive && isTTY && !flagAutoConfirm {
			if prompt.ConfirmDefaultNo("No branches found for cleanup. Enter interactive mode?") {
				toCleanup = interactiveSelection(statuses)
			}
		}
		if len(toCleanup) == 0 {
			fmt.Fprintln(os.Stderr, "No worktrees selected for cleanup.")
			return nil
		}
	}

	// Confirm.
	dryPrefix := ""
	if dryRun {
		dryPrefix = "[DRY RUN] "
	}

	fmt.Fprintf(os.Stderr, "\n%sWorktrees to be removed:\n", dryPrefix)
	for _, bs := range toCleanup {
		fmt.Fprintf(os.Stderr, "- %s (%s)\n", bs.Branch, bs.Path)
	}
	fmt.Fprintln(os.Stderr)

	if mode != model.CleanupModeInteractive && !flagAutoConfirm {
		action := "cleanup"
		if dryRun {
			action = "dry run"
		}
		if !prompt.ConfirmDefaultYes(fmt.Sprintf("Proceed with %s?", action)) {
			fmt.Fprintln(os.Stderr, "Cleanup cancelled.")
			return nil
		}
	}

	// Run pre_cleanup hooks.
	if !dryRun {
		globalHookCfg := a.Config.LoadGlobalHookConfig()
		globalScripts, projectScripts := hooks.ExtractScripts(globalHookCfg, projectHookCfg, hooks.PreCleanup)
		if len(globalScripts) > 0 || len(projectScripts) > 0 {
			for _, bs := range toCleanup {
				fmt.Fprintf(os.Stderr, "Running pre_cleanup hooks for %s\n", bs.Branch)
				a.Hooks.RunHooks(globalScripts, projectScripts, hooks.PreCleanup, bs.Path, repoPath, bs.Branch)
			}
		}
	}

	// Remove worktrees.
	fmt.Fprintf(os.Stderr, "%sRemoving worktrees...\n", dryPrefix)
	var removedBranches []string
	removedCount := 0

	for _, bs := range toCleanup {
		if dryRun {
			fmt.Fprintf(os.Stderr, "%sWould remove %s\n", dryPrefix, bs.Branch)
			removedBranches = append(removedBranches, bs.Branch)
			removedCount++
		} else {
			if err := a.Git.RemoveWorktree(repoPath, bs.Path, force); err != nil {
				fmt.Fprintf(os.Stderr, "Failed to remove %s: %v\n", bs.Branch, err)
			} else {
				fmt.Fprintf(os.Stderr, "Removed %s\n", bs.Branch)
				removedBranches = append(removedBranches, bs.Branch)
				removedCount++
			}
		}
	}

	// Delete local branches.
	deletedCount := 0
	if len(removedBranches) > 0 {
		shouldDelete := flagAutoConfirm
		if !flagAutoConfirm {
			fmt.Fprintf(os.Stderr, "\n%sThe following local branches will be deleted:\n", dryPrefix)
			for _, b := range removedBranches {
				fmt.Fprintf(os.Stderr, "  - %s\n", b)
			}
			action := "Delete"
			if dryRun {
				action = "Simulate deleting"
			}
			shouldDelete = prompt.ConfirmDefaultYes(fmt.Sprintf("%s these local branches?", action))
		}

		if shouldDelete {
			fmt.Fprintf(os.Stderr, "%sDeleting local branches...\n", dryPrefix)
			for _, b := range removedBranches {
				if dryRun {
					fmt.Fprintf(os.Stderr, "%sWould delete branch %s\n", dryPrefix, b)
					deletedCount++
				} else {
					if err := a.Git.DeleteBranch(repoPath, b); err != nil {
						fmt.Fprintf(os.Stderr, "Failed to delete branch %s: %v\n", b, err)
					} else {
						fmt.Fprintf(os.Stderr, "Deleted branch %s\n", b)
						deletedCount++
					}
				}
			}
		}
	}

	// Run post_cleanup hooks.
	if !dryRun {
		globalHookCfg := a.Config.LoadGlobalHookConfig()
		globalScripts, projectScripts := hooks.ExtractScripts(globalHookCfg, projectHookCfg, hooks.PostCleanup)
		if len(globalScripts) > 0 || len(projectScripts) > 0 {
			for _, bs := range toCleanup {
				fmt.Fprintf(os.Stderr, "Running post_cleanup hooks for %s\n", bs.Branch)
				a.Hooks.RunHooks(globalScripts, projectScripts, hooks.PostCleanup, bs.Path, repoPath, bs.Branch)
			}
		}
	}

	// Summary.
	verb := "Removed"
	if dryRun {
		verb = "Would remove"
	}
	summary := fmt.Sprintf("\n%s%s %d worktrees", dryPrefix, verb, removedCount)
	if deletedCount > 0 {
		deleteVerb := "deleted"
		if dryRun {
			deleteVerb = "would delete"
		}
		summary += fmt.Sprintf(" and %s %d local branches", deleteVerb, deletedCount)
	}
	fmt.Fprintln(os.Stderr, summary+".")

	return nil
}

func filterWorktreesByArgs(worktrees []model.WorktreeInfo, args []string) []model.WorktreeInfo {
	argSet := make(map[string]bool)
	for _, a := range args {
		argSet[a] = true
	}
	var result []model.WorktreeInfo
	for _, wt := range worktrees {
		if argSet[wt.Branch] || argSet[wt.Path] {
			result = append(result, wt)
		}
	}
	return result
}

func selectBranchesForCleanup(mode model.CleanupMode, statuses []model.BranchStatus) []model.BranchStatus {
	switch mode {
	case model.CleanupModeAll:
		return filterClean(dedup(append(
			filterByCondition(statuses, func(bs model.BranchStatus) bool { return !bs.HasRemote }),
			append(
				filterByCondition(statuses, func(bs model.BranchStatus) bool { return bs.IsIdentical }),
				filterByCondition(statuses, func(bs model.BranchStatus) bool { return bs.IsMerged })...,
			)...,
		)))
	case model.CleanupModeRemoteless:
		return filterClean(filterByCondition(statuses, func(bs model.BranchStatus) bool { return !bs.HasRemote }))
	case model.CleanupModeMerged:
		return filterClean(dedup(append(
			filterByCondition(statuses, func(bs model.BranchStatus) bool { return bs.IsIdentical }),
			filterByCondition(statuses, func(bs model.BranchStatus) bool { return bs.IsMerged })...,
		)))
	case model.CleanupModeGitHub:
		return filterClean(filterByCondition(statuses, func(bs model.BranchStatus) bool { return bs.IsMerged }))
	case model.CleanupModeInteractive:
		return interactiveSelection(statuses)
	default:
		return nil
	}
}

func filterByCondition(statuses []model.BranchStatus, cond func(model.BranchStatus) bool) []model.BranchStatus {
	var result []model.BranchStatus
	for _, bs := range statuses {
		if cond(bs) {
			result = append(result, bs)
		}
	}
	return result
}

func filterClean(statuses []model.BranchStatus) []model.BranchStatus {
	var clean []model.BranchStatus
	dirtyCount := 0
	for _, bs := range statuses {
		if bs.HasUncommittedChanges {
			dirtyCount++
		} else {
			clean = append(clean, bs)
		}
	}
	if dirtyCount > 0 {
		fmt.Fprintf(os.Stderr, "Skipping %d worktree(s) with uncommitted changes\n", dirtyCount)
	}
	return clean
}

func dedup(statuses []model.BranchStatus) []model.BranchStatus {
	seen := make(map[string]bool)
	var result []model.BranchStatus
	for _, bs := range statuses {
		if !seen[bs.Branch] {
			result = append(result, bs)
			seen[bs.Branch] = true
		}
	}
	return result
}

func interactiveSelection(statuses []model.BranchStatus) []model.BranchStatus {
	// Simple text-based selection (TUI can be added later).
	fmt.Fprintln(os.Stderr, "\nInteractive cleanup mode")
	fmt.Fprintln(os.Stderr, "Select worktrees to remove:")
	fmt.Fprintln(os.Stderr)

	var selected []model.BranchStatus
	for i, bs := range statuses {
		info := []string{}
		if !bs.HasRemote {
			info = append(info, "no remote")
		}
		if bs.IsMerged {
			info = append(info, "merged")
		}
		suffix := ""
		if len(info) > 0 {
			suffix = fmt.Sprintf(" (%s)", strings.Join(info, ", "))
		}

		if prompt.ConfirmDefaultNo(fmt.Sprintf("%d. Remove %s%s?", i+1, bs.Branch, suffix)) {
			selected = append(selected, bs)
		}
	}

	if len(selected) > 0 {
		fmt.Fprintf(os.Stderr, "\nSelected %d worktrees for removal.\n", len(selected))
	}
	return selected
}
