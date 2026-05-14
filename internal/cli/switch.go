package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/irskep/autowt/internal/branch"
	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/hooks"
	"github.com/irskep/autowt/internal/model"
	"github.com/irskep/autowt/internal/prompt"
	"github.com/irskep/autowt/internal/ui"
	"github.com/spf13/cobra"
)

func newSwitchCmd() *cobra.Command {
	var (
		flagTerminal          string
		flagAfterInit         string
		flagIgnoreSameSession bool
		flagFrom              string
		flagCustomScript      string
		flagDir               string
	)

	cmd := &cobra.Command{
		Use:     "switch [branch]",
		Aliases: []string{"sw", "checkout", "co", "goto", "go"},
		Short:   "Switch to or create a worktree for the specified branch",
		Args:    cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return runInteractiveSwitch()
			}

			return runSwitch(switchOpts{
				Branch:            args[0],
				Terminal:          flagTerminal,
				AfterInit:         flagAfterInit,
				IgnoreSameSession: flagIgnoreSameSession,
				From:              flagFrom,
				CustomScript:      flagCustomScript,
				Dir:               flagDir,
				FromDynamic:       false,
			})
		},
	}

	cmd.Flags().StringVar(&flagTerminal, "terminal", "", "How to open the worktree terminal (tab, window, inplace, echo, vscode, cursor)")
	cmd.Flags().StringVar(&flagAfterInit, "after-init", "", "Command to run after session_init script completes")
	cmd.Flags().BoolVar(&flagIgnoreSameSession, "ignore-same-session", false, "Always create new terminal, ignore existing sessions")
	cmd.Flags().StringVar(&flagFrom, "from", "", "Source branch/commit to create worktree from")
	cmd.Flags().StringVar(&flagCustomScript, "custom-script", "", "Custom script to run with arguments")
	cmd.Flags().StringVar(&flagDir, "dir", "", "Directory path for the new worktree")

	return cmd
}

func runInteractiveSwitch() error {
	a := newApp()

	repoPath, err := a.Git.FindRepoRoot("")
	if err != nil {
		return fmt.Errorf("not in a git repository")
	}

	worktrees, err := a.Git.ListWorktrees(repoPath)
	if err != nil {
		return err
	}

	fmt.Fprintln(os.Stderr, "Fetching branches...")
	a.Git.FetchBranches(repoPath)

	// Get all local branches.
	allBranches := getAllLocalBranches(repoPath)

	result, err := ui.RunSwitchTUI(worktrees, allBranches)
	if err != nil {
		return err
	}
	if result == nil {
		return nil
	}

	return runSwitch(switchOpts{
		Branch:      result.Branch,
		FromDynamic: result.IsNew,
	})
}

func getAllLocalBranches(repoPath string) []string {
	out, err := exec.Command("git", "-C", repoPath, "branch", "--format=%(refname:short)").Output()
	if err != nil {
		return nil
	}
	var branches []string
	for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		line = strings.TrimSpace(line)
		if line != "" && !strings.HasPrefix(line, "*") {
			branches = append(branches, line)
		}
	}
	return branches
}

// runDynamicBranch handles unknown subcommands as branch names.
func runDynamicBranch(branchName string, extraArgs []string) error {
	// Parse flags from extraArgs.
	opts := switchOpts{
		Branch:      branchName,
		FromDynamic: true,
	}
	// Simple flag parsing for dynamic commands.
	for i := 0; i < len(extraArgs); i++ {
		switch extraArgs[i] {
		case "-y", "--yes":
			flagAutoConfirm = true
		case "--debug":
			flagDebug = true
		case "--terminal":
			if i+1 < len(extraArgs) {
				i++
				opts.Terminal = extraArgs[i]
			}
		case "--from":
			if i+1 < len(extraArgs) {
				i++
				opts.From = extraArgs[i]
			}
		case "--dir":
			if i+1 < len(extraArgs) {
				i++
				opts.Dir = extraArgs[i]
			}
		case "--after-init":
			if i+1 < len(extraArgs) {
				i++
				opts.AfterInit = extraArgs[i]
			}
		case "--ignore-same-session":
			opts.IgnoreSameSession = true
		}
	}

	return runSwitch(opts)
}

type switchOpts struct {
	Branch            string
	Terminal          string
	AfterInit         string
	IgnoreSameSession bool
	From              string
	CustomScript      string
	Dir               string
	FromDynamic       bool
}

func runSwitch(opts switchOpts) error {
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

	// Resolve session init script.
	sessionInitScript := cfg.Scripts.SessionInit
	if projectHookCfg.SessionInit != "" {
		sessionInitScript = projectHookCfg.SessionInit
	}

	// Resolve custom script.
	var customScript *model.CustomScript
	if opts.CustomScript != "" {
		cs, scriptArgs, ok := resolveCustomScript(cfg, opts.CustomScript)
		if ok {
			customScript = &cs

			if cs.BranchName != "" {
				// Dynamic branch name from command.
				fmt.Fprintf(os.Stderr, "Generating branch name: %s\n", cs.BranchName)
				dynamicBranch, err := executeBranchNameCommand(cs.BranchName, repoPath)
				if err != nil {
					return fmt.Errorf("failed to resolve dynamic branch name: %w", err)
				}
				fmt.Fprintf(os.Stderr, "Branch: %s\n", dynamicBranch)
				opts.Branch = dynamicBranch
			} else if opts.Branch == "" && len(scriptArgs) > 0 {
				// Simple format: first arg is the branch name.
				opts.Branch = scriptArgs[0]
			}
		}
	}

	if opts.Branch == "" {
		return fmt.Errorf("no branch name provided")
	}

	// Resolve branch-or-path argument.
	resolved, err := a.Git.ResolveWorktreeArgument(opts.Branch, func(name string) bool {
		fmt.Fprintf(os.Stderr, "Directory '%s' exists locally.\n", name)
		return prompt.ConfirmDefaultYes(fmt.Sprintf("Did you mean to switch to branch '%s'? (no = use directory './%s')", name, name))
	})
	if err != nil {
		return err
	}
	opts.Branch = resolved

	// Apply branch prefix.
	worktrees, err := a.Git.ListWorktrees(repoPath)
	if err != nil {
		return err
	}

	canonicalBranch := resolveCanonicalBranch(a, cfg, opts.Branch, worktrees, repoPath)
	opts.Branch = canonicalBranch

	// Determine terminal mode.
	termMode := cfg.Terminal.Mode
	if shellIntegrationFile != "" {
		termMode = model.TerminalModeEcho
	} else if opts.Terminal != "" {
		termMode = model.TerminalMode(opts.Terminal)
	}

	// Check if worktree already exists.
	for _, wt := range worktrees {
		if wt.Branch == opts.Branch {
			return switchToExisting(a, wt, opts, cfg, projectHookCfg, termMode, customScript)
		}
	}

	// New worktree: confirm if dynamic command.
	if opts.FromDynamic && !flagAutoConfirm {
		if !prompt.ConfirmDefaultYes(fmt.Sprintf("Create a branch '%s' and worktree?", opts.Branch)) {
			fmt.Fprintln(os.Stderr, "Worktree creation cancelled.")
			return nil
		}
	}

	return createNewWorktree(a, opts, repoPath, cfg, projectHookCfg, termMode, sessionInitScript, customScript)
}

func switchToExisting(a *app, wt model.WorktreeInfo, opts switchOpts, cfg config.Config, projectHookCfg config.HookConfig, termMode model.TerminalMode, customScript *model.CustomScript) error {
	repoPath, _ := a.Git.FindRepoRoot("")

	// Check if already in this worktree.
	cwd, _ := os.Getwd()
	currentWT := a.Git.GetCurrentWorktree(cwd, []model.WorktreeInfo{wt})
	if currentWT != nil && currentWT.Path == wt.Path {
		fmt.Fprintf(os.Stderr, "Already in %s worktree\n", opts.Branch)
		return nil
	}

	// Run pre_switch hooks.
	runHookSet(a, hooks.PreSwitch, wt.Path, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)

	// Combine after_init and custom script session_init.
	afterInit := combineAfterInit(opts.AfterInit, customScript)

	err := a.Terminal.SwitchToWorktree(
		wt.Path, termMode, "", afterInit,
		opts.Branch, flagAutoConfirm, opts.IgnoreSameSession || cfg.Terminal.AlwaysNew,
		shellIntegrationFile,
	)
	if err != nil {
		return fmt.Errorf("failed to switch to %s worktree: %w", opts.Branch, err)
	}

	// Run post_switch hooks.
	runHookSet(a, hooks.PostSwitch, wt.Path, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)

	return nil
}

func createNewWorktree(a *app, opts switchOpts, repoPath string, cfg config.Config, projectHookCfg config.HookConfig, termMode model.TerminalMode, sessionInitScript string, customScript *model.CustomScript) error {
	// Fetch branches.
	if cfg.Worktree.AutoFetch {
		fmt.Fprintln(os.Stderr, "Fetching branches...")
		if err := a.Git.FetchBranches(repoPath); err != nil {
			fmt.Fprintln(os.Stderr, "Warning: Failed to fetch latest branches")
		}
	}

	// Check remote branch availability.
	if opts.From == "" {
		exists, remoteName := a.Git.CheckRemoteBranchAvailability(repoPath, opts.Branch)
		if exists && !flagAutoConfirm {
			if !prompt.ConfirmDefaultYes(fmt.Sprintf("Branch '%s' exists on remote '%s'. Create a local worktree tracking the remote branch?", opts.Branch, remoteName)) {
				fmt.Fprintln(os.Stderr, "Worktree creation cancelled.")
				return nil
			}
		}
	}

	// Generate worktree path.
	worktreePath := generateWorktreePath(a, repoPath, opts.Branch, opts.Dir, cfg)

	// Check for conflicting worktree at that path.
	worktrees, _ := a.Git.ListWorktrees(repoPath)
	for _, wt := range worktrees {
		if wt.Path == worktreePath && wt.Branch != opts.Branch {
			alt := generateAlternativePath(worktreePath, worktrees)
			fmt.Fprintf(os.Stderr, "That branch's original worktree is now on a different branch ('%s')\n", wt.Branch)
			if !prompt.ConfirmDefaultYes(fmt.Sprintf("Create a new worktree at %s?", alt)) {
				fmt.Fprintln(os.Stderr, "Worktree creation cancelled.")
				return nil
			}
			worktreePath = alt
			break
		}
	}

	fmt.Fprintf(os.Stderr, "Creating worktree for %s...\n", opts.Branch)

	// Pre-create hooks.
	if err := runHookSet(a, hooks.PreCreate, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, true); err != nil {
		return fmt.Errorf("pre_create hooks failed, aborting: %w", err)
	}

	// Create the worktree.
	if err := a.Git.CreateWorktree(repoPath, opts.Branch, worktreePath, opts.From); err != nil {
		return fmt.Errorf("failed to create worktree for %s: %w", opts.Branch, err)
	}
	fmt.Fprintf(os.Stderr, "Worktree created at %s\n", worktreePath)

	// Post-create hooks.
	if err := runHookSet(a, hooks.PostCreate, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, true); err != nil {
		return fmt.Errorf("post_create hooks failed: %w", err)
	}

	// Pre-switch hooks.
	runHookSet(a, hooks.PreSwitch, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)

	// For echo/inplace: run async hooks before terminal switch.
	runsAsyncBeforeSwitch := termMode == model.TerminalModeEcho || termMode == model.TerminalModeInplace
	if runsAsyncBeforeSwitch {
		runHookSet(a, hooks.PostCreateAsync, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)
	}

	// Switch terminal.
	afterInit := combineAfterInit(opts.AfterInit, customScript)
	err := a.Terminal.SwitchToWorktree(
		worktreePath, termMode, sessionInitScript, afterInit,
		opts.Branch, flagAutoConfirm, opts.IgnoreSameSession || cfg.Terminal.AlwaysNew,
		shellIntegrationFile,
	)
	if err != nil {
		return fmt.Errorf("worktree created but failed to switch terminals: %w", err)
	}

	// Post-switch hooks.
	runHookSet(a, hooks.PostSwitch, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)

	// For tab/window: run async hooks after terminal switch.
	if !runsAsyncBeforeSwitch {
		runHookSet(a, hooks.PostCreateAsync, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)
	}

	fmt.Fprintf(os.Stderr, "Switched to new %s worktree\n", opts.Branch)
	return nil
}

func generateWorktreePath(a *app, repoPath, branchName, customDir string, cfg config.Config) string {
	if customDir != "" {
		if filepath.IsAbs(customDir) {
			return customDir
		}
		cwd, _ := os.Getwd()
		return filepath.Join(cwd, customDir)
	}

	worktrees, _ := a.Git.ListWorktrees(repoPath)
	mainRepoPath := repoPath
	for _, wt := range worktrees {
		if wt.IsPrimary {
			mainRepoPath = wt.Path
			break
		}
	}

	repoName := filepath.Base(mainRepoPath)
	if strings.HasSuffix(repoName, ".git") {
		repoName = repoName[:len(repoName)-4]
	}

	safeBranch := branch.Sanitize(branchName)

	pattern := cfg.Worktree.DirectoryPattern
	pattern = strings.ReplaceAll(pattern, "{repo_dir}", mainRepoPath)
	pattern = strings.ReplaceAll(pattern, "{repo_name}", repoName)
	pattern = strings.ReplaceAll(pattern, "{repo_parent_dir}", filepath.Dir(mainRepoPath))
	pattern = strings.ReplaceAll(pattern, "{branch}", safeBranch)
	pattern = os.ExpandEnv(pattern)

	if filepath.IsAbs(pattern) {
		return filepath.Clean(pattern)
	}
	return filepath.Clean(filepath.Join(mainRepoPath, pattern))
}

func generateAlternativePath(basePath string, worktrees []model.WorktreeInfo) string {
	base := filepath.Base(basePath)
	parent := filepath.Dir(basePath)
	for suffix := 2; suffix <= 100; suffix++ {
		alt := filepath.Join(parent, fmt.Sprintf("%s-%d", base, suffix))
		conflict := false
		for _, wt := range worktrees {
			if wt.Path == alt {
				conflict = true
				break
			}
		}
		if !conflict {
			return alt
		}
	}
	return basePath
}

func resolveCanonicalBranch(a *app, cfg config.Config, branchName string, worktrees []model.WorktreeInfo, repoPath string) string {
	prefix := cfg.Worktree.BranchPrefix
	if prefix == "" {
		return branchName
	}

	// If exact match exists in worktrees, use it.
	for _, wt := range worktrees {
		if wt.Branch == branchName {
			return branchName
		}
	}

	// If exact match exists locally or remotely, use it.
	if a.Git.BranchExistsLocally(repoPath, branchName) || a.Git.BranchExistsRemotely(repoPath, branchName) {
		return branchName
	}

	// Build template context and apply prefix.
	context := map[string]string{
		"repo_name": filepath.Base(repoPath),
	}
	if username := a.GitHub.GetUsername(); username != "" {
		context["github_username"] = username
	}

	prefixed := branch.ApplyPrefix(branchName, prefix, context)
	if prefixed == branchName {
		return branchName
	}

	// If prefixed version exists, use it.
	for _, wt := range worktrees {
		if wt.Branch == prefixed {
			return prefixed
		}
	}

	// Apply prefix for new branches.
	return prefixed
}

func resolveCustomScript(cfg config.Config, spec string) (model.CustomScript, []string, bool) {
	parts := strings.Fields(spec)
	if len(parts) == 0 {
		return model.CustomScript{}, nil, false
	}
	name := parts[0]
	cs, ok := cfg.Scripts.Custom[name]
	if !ok {
		return model.CustomScript{}, nil, false
	}

	args := parts[1:]

	// Interpolate $1, $2, etc. from remaining arguments.
	if len(args) > 0 {
		cs.BranchName = branch.InterpolateArgs(cs.BranchName, args)
		cs.SessionInit = branch.InterpolateArgs(cs.SessionInit, args)
		cs.PreCreate = branch.InterpolateArgs(cs.PreCreate, args)
		cs.PostCreate = branch.InterpolateArgs(cs.PostCreate, args)
		cs.PostCreateAsync = branch.InterpolateArgs(cs.PostCreateAsync, args)
		cs.PreCleanup = branch.InterpolateArgs(cs.PreCleanup, args)
		cs.PostCleanup = branch.InterpolateArgs(cs.PostCleanup, args)
		cs.PreSwitch = branch.InterpolateArgs(cs.PreSwitch, args)
		cs.PostSwitch = branch.InterpolateArgs(cs.PostSwitch, args)
	}

	return cs, args, true
}

func executeBranchNameCommand(cmd, repoPath string) (string, error) {
	c := exec.Command("sh", "-c", cmd)
	c.Dir = repoPath
	out, err := c.Output()
	if err != nil {
		return "", err
	}
	raw := strings.TrimSpace(string(out))
	if raw == "" {
		return "", fmt.Errorf("branch_name command produced empty output")
	}
	return branch.NormalizeDynamic(raw), nil
}

func combineAfterInit(afterInit string, cs *model.CustomScript) string {
	var parts []string
	if afterInit != "" {
		parts = append(parts, afterInit)
	}
	if cs != nil && cs.SessionInit != "" {
		parts = append(parts, cs.SessionInit)
	}
	return strings.Join(parts, "; ")
}

func runHookSet(a *app, hookType, worktreePath, repoPath string, cfg config.Config, projectHookCfg config.HookConfig, branchName string, customScript *model.CustomScript, abortOnFailure bool) error {
	globalHookCfg := a.Config.LoadGlobalHookConfig()
	globalScripts, projectScripts := hooks.ExtractScripts(globalHookCfg, projectHookCfg, hookType)
	merged := hooks.MergeForCustomScript(globalScripts, projectScripts, customScript, hookType)

	if len(merged) == 0 {
		return nil
	}

	fmt.Fprintf(os.Stderr, "Running %s hooks for %s\n", hookType, branchName)
	for _, script := range merged {
		if err := a.Hooks.RunHook(script, hookType, worktreePath, repoPath, branchName); err != nil {
			if abortOnFailure {
				return err
			}
			fmt.Fprintf(os.Stderr, "Warning: %s hook failed, continuing: %v\n", hookType, err)
		}
	}
	return nil
}
