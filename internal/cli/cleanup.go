package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/console"
	"github.com/irskep/autowt/internal/hooks"
	"github.com/irskep/autowt/internal/model"
	"github.com/irskep/autowt/internal/prompt"
	"github.com/irskep/autowt/internal/ui"
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

	// Determine mode. Skip mode selection when specific worktrees are given.
	mode := model.CleanupMode(modeStr)
	if modeStr == "" && len(worktreeArgs) == 0 {
		isTTY := term.IsTerminal(int(os.Stdin.Fd()))
		if !isTTY {
			return fmt.Errorf("no TTY detected. Please specify --mode explicitly when running in scripts or CI. Available modes: all, remoteless, merged, interactive, github")
		}

		if !a.Config.HasUserConfiguredCleanupMode() {
			// First-run prompt.
			console.Section("Select your default cleanup mode:")
			console.Plain("  1. interactive - Choose which worktrees to remove")
			console.Plain("  2. merged      - Remove branches merged into main")
			console.Plain("  3. remoteless  - Remove branches without remote tracking")
			if a.GitHub.IsAvailable() {
				console.Plain("  4. github      - Remove branches with merged/closed PRs")
			}
			fmt.Fprint(os.Stderr, "Choice [1]: ")
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
			console.Infof("Saving '%s' as your default cleanup mode...", mode)
			if err := a.Config.SaveCleanupMode(mode); err != nil {
				console.Warningf("failed to save preference: %v", err)
			}
			console.Info("You can change this later using 'autowt config' or by editing config.toml")
		} else {
			mode = cfg.Cleanup.DefaultMode
		}
	}

	// GitHub mode: check gh availability early.
	if mode == model.CleanupModeGitHub && !a.GitHub.IsAvailable() {
		return fmt.Errorf("GitHub cleanup requires the 'gh' CLI tool. Install it from: https://cli.github.com/")
	}

	// Fetch branches.
	console.Info("Fetching branches...")
	if err := a.Git.FetchBranches(repoPath); err != nil {
		console.Warningf("Failed to fetch latest branches: %v", err)
	}

	console.Info("Checking branch status...")

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
		console.Info("No secondary worktrees found.")
		return nil
	}

	// If specific worktrees were named, handle them directly (bypass mode selection).
	if len(worktreeArgs) > 0 {
		secondary = filterWorktreesByArgs(secondary, worktreeArgs)
		if len(secondary) == 0 {
			return fmt.Errorf("none of the specified worktrees were found")
		}
		statuses := a.Git.AnalyzeBranchesForCleanup(repoPath, secondary)
		return executeCleanup(a, statuses, mode, repoPath, projectHookCfg, dryRun, force)
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

	// Display categorized branch status.
	displayBranchStatus(mode, statuses)

	// Select branches for cleanup.
	toCleanup := selectBranchesForCleanup(mode, statuses)
	if len(toCleanup) == 0 {
		// Offer interactive fallback if in TTY.
		isTTY := term.IsTerminal(int(os.Stdin.Fd()))
		if mode != model.CleanupModeInteractive && isTTY && !a.Opts.AutoConfirm {
			if prompt.ConfirmNo("No branches found for cleanup. Enter interactive mode?", false) {
				toCleanup = interactiveSelection(statuses)
			}
		}
		if len(toCleanup) == 0 {
			console.Info("No worktrees selected for cleanup.")
			return nil
		}
	}

	return executeCleanup(a, toCleanup, mode, repoPath, projectHookCfg, dryRun, force)
}

func executeCleanup(a *app, toCleanup []model.BranchStatus, mode model.CleanupMode, repoPath string, projectHookCfg config.HookConfig, dryRun, force bool) error {
	dryPrefix := ""
	if dryRun {
		dryPrefix = "[DRY RUN] "
	}

	console.Section(fmt.Sprintf("%sWorktrees to be removed:", dryPrefix))
	for _, bs := range toCleanup {
		console.Plain(fmt.Sprintf("- %s (%s)", bs.Branch, model.FormatPath(bs.Path)))
	}
	console.Plain("")

	if mode != model.CleanupModeInteractive && !a.Opts.AutoConfirm {
		action := "cleanup"
		if dryRun {
			action = "dry run"
		}
		if !prompt.ConfirmYes(fmt.Sprintf("Proceed with %s?", action), a.Opts.AutoConfirm) {
			console.Info("Cleanup cancelled.")
			return nil
		}
	}

	// Run pre_cleanup hooks.
	if dryRun {
		console.Info("[DRY RUN] Would run pre_cleanup hooks")
	} else {
		globalHookCfg := a.Config.LoadGlobalHookConfig()
		globalScripts, projectScripts := hooks.ExtractScripts(globalHookCfg, projectHookCfg, hooks.PreCleanup)
		if len(globalScripts) > 0 || len(projectScripts) > 0 {
			for _, bs := range toCleanup {
				console.Infof("Running pre_cleanup hooks for %s", bs.Branch)
				a.Hooks.RunHooks(globalScripts, projectScripts, hooks.PreCleanup, bs.Path, repoPath, bs.Branch)
			}
		}
	}

	// Remove worktrees.
	console.Infof("%sRemoving worktrees...", dryPrefix)
	var removedBranches []string
	removedCount := 0

	for _, bs := range toCleanup {
		if dryRun {
			console.Infof("%sWould remove %s", dryPrefix, bs.Branch)
			removedBranches = append(removedBranches, bs.Branch)
			removedCount++
		} else {
			err := a.Git.RemoveWorktree(repoPath, bs.Path, force)
			if err != nil && !force {
				// Offer interactive retry with --force for dirty worktrees.
				console.Errorf("Git error: %v", err)
				if prompt.ConfirmNo("Retry with --force to remove worktree with modified files?", false) {
					err = a.Git.RemoveWorktree(repoPath, bs.Path, true)
				}
			}
			if err != nil {
				console.Errorf("Failed to remove %s: %v", bs.Branch, err)
			} else {
				console.Successf("Removed %s", bs.Branch)
				removedBranches = append(removedBranches, bs.Branch)
				removedCount++
			}
		}
	}

	// Delete local branches.
	deletedCount := 0
	if len(removedBranches) > 0 {
		shouldDelete := a.Opts.AutoConfirm
		if !a.Opts.AutoConfirm {
			console.Section(fmt.Sprintf("%sThe following local branches will be deleted:", dryPrefix))
			for _, b := range removedBranches {
				console.Plain(fmt.Sprintf("  - %s", b))
			}
			action := "Delete"
			if dryRun {
				action = "Simulate deleting"
			}
			shouldDelete = prompt.ConfirmYes(fmt.Sprintf("%s these local branches?", action), a.Opts.AutoConfirm)
		}

		if shouldDelete {
			console.Infof("%sDeleting local branches...", dryPrefix)
			for _, b := range removedBranches {
				if dryRun {
					console.Infof("%sWould delete branch %s", dryPrefix, b)
					deletedCount++
				} else {
					if err := a.Git.DeleteBranch(repoPath, b); err != nil {
						console.Errorf("Failed to delete branch %s: %v", b, err)
					} else {
						console.Successf("Deleted branch %s", b)
						deletedCount++
					}
				}
			}
		}
	}

	// Run post_cleanup hooks.
	if dryRun {
		console.Info("[DRY RUN] Would run post_cleanup hooks")
	} else {
		globalHookCfg := a.Config.LoadGlobalHookConfig()
		globalScripts, projectScripts := hooks.ExtractScripts(globalHookCfg, projectHookCfg, hooks.PostCleanup)
		if len(globalScripts) > 0 || len(projectScripts) > 0 {
			for _, bs := range toCleanup {
				console.Infof("Running post_cleanup hooks for %s", bs.Branch)
				a.Hooks.RunHooks(globalScripts, projectScripts, hooks.PostCleanup, bs.Path, repoPath, bs.Branch)
			}
		}
	}

	// Summary.
	if removedCount == 0 {
		console.Infof("\n%sCleanup complete. No worktrees were removed.", dryPrefix)
	} else {
		verb := "Removed"
		if dryRun {
			verb = "Would remove"
		}
		summary := fmt.Sprintf("\n%sCleanup complete. %s %d worktrees", dryPrefix, verb, removedCount)
		if deletedCount > 0 {
			deleteVerb := "deleted"
			if dryRun {
				deleteVerb = "would delete"
			}
			summary += fmt.Sprintf(" and %s %d local branches", deleteVerb, deletedCount)
		}
		console.Success(summary + ".")
	}

	return nil
}

func displayBranchStatus(mode model.CleanupMode, statuses []model.BranchStatus) {
	if mode == model.CleanupModeGitHub {
		var merged, open []string
		for _, bs := range statuses {
			if bs.IsMerged {
				merged = append(merged, bs.Branch)
			} else {
				open = append(open, bs.Branch)
			}
		}
		if len(merged) > 0 {
			console.Info("Branches with merged or closed PRs:")
			for _, b := range merged {
				console.Plain(fmt.Sprintf("- %s", b))
			}
			console.Plain("")
		}
		if len(open) > 0 {
			console.Info("Branches with open or no PRs (will be kept):")
			for _, b := range open {
				console.Plain(fmt.Sprintf("- %s", b))
			}
			console.Plain("")
		}
		return
	}

	var remoteless, identical, merged []string
	for _, bs := range statuses {
		if !bs.HasRemote {
			remoteless = append(remoteless, bs.Branch)
		}
		if bs.IsIdentical {
			identical = append(identical, bs.Branch)
		}
		if bs.IsMerged {
			merged = append(merged, bs.Branch)
		}
	}
	if len(remoteless) > 0 {
		console.Info("Branches without remotes:")
		for _, b := range remoteless {
			console.Plain(fmt.Sprintf("- %s", b))
		}
		console.Plain("")
	}
	if len(identical) > 0 {
		console.Info("Branches identical to main:")
		for _, b := range identical {
			console.Plain(fmt.Sprintf("- %s", b))
		}
		console.Plain("")
	}
	if len(merged) > 0 {
		console.Info("Branches that were merged:")
		for _, b := range merged {
			console.Plain(fmt.Sprintf("- %s", b))
		}
		console.Plain("")
	}
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
		console.Infof("Skipping %d worktree(s) with uncommitted changes", dirtyCount)
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
	isTTY := term.IsTerminal(int(os.Stdin.Fd()))
	if !isTTY {
		return textInteractiveSelection(statuses)
	}

	selected, err := ui.RunCleanupTUI(statuses)
	if err != nil {
		// Fall back to text-based selection on TUI error.
		return textInteractiveSelection(statuses)
	}
	return selected
}

func textInteractiveSelection(statuses []model.BranchStatus) []model.BranchStatus {
	console.Section("\nInteractive cleanup mode")
	console.Info("Select worktrees to remove:")
	console.Plain("")

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

		if prompt.ConfirmNo(fmt.Sprintf("%d. Remove %s%s?", i+1, bs.Branch, suffix), false) {
			selected = append(selected, bs)
		}
	}

	if len(selected) > 0 {
		console.Infof("Selected %d worktrees for removal.", len(selected))
	}
	return selected
}
