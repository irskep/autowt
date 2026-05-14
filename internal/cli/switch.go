package cli

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/google/shlex"
	"github.com/irskep/autowt/internal/branch"
	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/console"
	"github.com/irskep/autowt/internal/hooks"
	"github.com/irskep/autowt/internal/model"
	"github.com/irskep/autowt/internal/prompt"
	"github.com/irskep/autowt/internal/terminal"
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
		Use:               "switch [branch]",
		Aliases:           []string{"sw", "checkout", "co", "goto", "go"},
		Short:             "Switch to or create a worktree for the specified branch",
		Args:              cobra.MaximumNArgs(1),
		ValidArgsFunction: completeBranches,
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

func completeBranches(cmd *cobra.Command, args []string, toComplete string) ([]string, cobra.ShellCompDirective) {
	if len(args) > 0 {
		return nil, cobra.ShellCompDirectiveNoFileComp
	}
	a := newApp()
	repoPath, err := a.Git.FindRepoRoot("")
	if err != nil {
		return nil, cobra.ShellCompDirectiveNoFileComp
	}
	worktrees, err := a.Git.ListWorktrees(repoPath)
	if err != nil {
		return nil, cobra.ShellCompDirectiveNoFileComp
	}
	var completions []string
	for _, wt := range worktrees {
		if strings.Contains(strings.ToLower(wt.Branch), strings.ToLower(toComplete)) {
			completions = append(completions, wt.Branch)
		}
	}
	return completions, cobra.ShellCompDirectiveNoFileComp
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

	console.Info("Fetching branches...")
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
			globalOpts.AutoConfirm = true
		case "--debug":
			globalOpts.Debug = true
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
				console.Infof("Generating branch name: %s", cs.BranchName)
				dynamicBranch, err := executeBranchNameCommand(cs.BranchName, repoPath)
				if err != nil {
					return fmt.Errorf("failed to resolve dynamic branch name: %w", err)
				}
				console.Infof("Branch: %s", dynamicBranch)
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
		console.Infof("Directory '%s' exists locally.", name)
		return prompt.ConfirmYes(fmt.Sprintf("Did you mean to switch to branch '%s'? (no = use directory './%s')", name, name), a.Opts.AutoConfirm)
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
	if a.Opts.ShellIntegrationFile != "" {
		termMode = model.TerminalModeEcho
	} else if opts.Terminal != "" {
		termMode = model.TerminalMode(opts.Terminal)
	}

	// Suppress styled output in echo mode (but not shell integration,
	// where stdout is a real TTY and the cd command goes to a file).
	if termMode == model.TerminalModeEcho && a.Opts.ShellIntegrationFile == "" {
		console.Suppressed = true
		defer func() { console.Suppressed = false }()
	}

	// Check if worktree already exists.
	for _, wt := range worktrees {
		if wt.Branch == opts.Branch {
			return switchToExisting(a, wt, opts, cfg, projectHookCfg, termMode, customScript)
		}
	}

	// New worktree: confirm if dynamic command.
	if opts.FromDynamic && !a.Opts.AutoConfirm {
		if !prompt.ConfirmYes(fmt.Sprintf("Create a branch '%s' and worktree?", opts.Branch), a.Opts.AutoConfirm) {
			console.Info("Worktree creation cancelled.")
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
		console.Infof("Already in %s worktree", opts.Branch)
		return nil
	}

	// Run pre_switch hooks.
	runHookSet(a, hooks.PreSwitch, wt.Path, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)

	// Combine after_init and custom script session_init.
	afterInit := combineAfterInit(opts.AfterInit, customScript)

	err := a.Terminal.SwitchToWorktree(terminal.SwitchOpts{
		WorktreePath:         wt.Path,
		Mode:                 termMode,
		AfterInit:            afterInit,
		BranchName:           opts.Branch,
		IgnoreSameSession:    opts.IgnoreSameSession || cfg.Terminal.AlwaysNew,
		ShellIntegrationFile: a.Opts.ShellIntegrationFile,
	})
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
		console.Info("Fetching branches...")
		if err := a.Git.FetchBranches(repoPath); err != nil {
			console.Warningf("Failed to fetch latest branches: %v", err)
		}
	}

	// Check remote branch availability.
	if opts.From == "" {
		exists, remoteName := a.Git.CheckRemoteBranchAvailability(repoPath, opts.Branch)
		if exists && !a.Opts.AutoConfirm {
			if !prompt.ConfirmYes(fmt.Sprintf("Branch '%s' exists on remote '%s'. Create a local worktree tracking the remote branch?", opts.Branch, remoteName), a.Opts.AutoConfirm) {
				console.Info("Worktree creation cancelled.")
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
			console.Infof("That branch's original worktree is now on a different branch ('%s')", wt.Branch)
			if !prompt.ConfirmYes(fmt.Sprintf("Create a new worktree at %s?", alt), a.Opts.AutoConfirm) {
				console.Info("Worktree creation cancelled.")
				return nil
			}
			worktreePath = alt
			break
		}
	}

	console.Infof("Creating worktree for %s...", opts.Branch)

	// Pre-create hooks.
	if err := runHookSet(a, hooks.PreCreate, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, true); err != nil {
		return fmt.Errorf("pre_create hooks failed, aborting: %w", err)
	}

	// Create the worktree.
	if err := a.Git.CreateWorktree(repoPath, opts.Branch, worktreePath, opts.From); err != nil {
		return fmt.Errorf("failed to create worktree for %s: %w", opts.Branch, err)
	}
	console.Successf("Worktree created at %s", worktreePath)

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
	err := a.Terminal.SwitchToWorktree(terminal.SwitchOpts{
		WorktreePath:         worktreePath,
		Mode:                 termMode,
		SessionInitScript:    sessionInitScript,
		AfterInit:            afterInit,
		BranchName:           opts.Branch,
		IgnoreSameSession:    opts.IgnoreSameSession || cfg.Terminal.AlwaysNew,
		ShellIntegrationFile: a.Opts.ShellIntegrationFile,
	})
	if err != nil {
		return fmt.Errorf("worktree created but failed to switch terminals: %w", err)
	}

	// Post-switch hooks.
	runHookSet(a, hooks.PostSwitch, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)

	// For tab/window: run async hooks after terminal switch.
	if !runsAsyncBeforeSwitch {
		runHookSet(a, hooks.PostCreateAsync, worktreePath, repoPath, cfg, projectHookCfg, opts.Branch, customScript, false)
	}

	console.Successf("Switched to new %s worktree", opts.Branch)
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
	parts, err := shlex.Split(spec)
	if err != nil {
		return model.CustomScript{}, nil, false
	}
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

func executeBranchNameCommand(cmdStr, repoPath string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	c := exec.CommandContext(ctx, "sh", "-c", cmdStr)
	c.Dir = repoPath
	out, err := c.Output()
	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return "", fmt.Errorf("branch_name command timed out after 30 seconds")
		}
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

	console.Infof("Running %s hooks for %s", hookType, branchName)
	for _, script := range merged {
		if err := a.Hooks.RunHook(script, hookType, worktreePath, repoPath, branchName); err != nil {
			if abortOnFailure {
				return err
			}
			console.Warningf("%s hook failed, continuing: %v", hookType, err)
		}
	}
	return nil
}
