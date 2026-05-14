package cli

import (
	"fmt"
	"os"

	"github.com/irskep/autowt/internal/console"
	"github.com/irskep/autowt/internal/hooks"
	"github.com/spf13/cobra"
)

func newHookCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "hook <hook_name>",
		Short: "Run a specific lifecycle hook",
		Long: `Run the configured global and project hooks for the given hook type.
Useful for integrating autowt's hook configuration with other worktree tools.`,
		Args:      cobra.ExactArgs(1),
		ValidArgs: hooks.AllTypes,
		RunE: func(cmd *cobra.Command, args []string) error {
			return runHook(args[0])
		},
	}
	return cmd
}

func runHook(hookName string) error {
	a := newApp()

	repoPath, err := a.Git.FindRepoRoot("")
	if err != nil {
		return fmt.Errorf("not in a git repository")
	}

	branchName, err := a.Git.GetCurrentBranch(repoPath)
	if err != nil {
		return fmt.Errorf("could not determine current branch: %w", err)
	}

	cwd, _ := os.Getwd()

	globalHookCfg := a.Config.LoadGlobalHookConfig()
	projectHookCfg := a.Config.LoadProjectHookConfig(repoPath)

	globalScripts, projectScripts := hooks.ExtractScripts(globalHookCfg, projectHookCfg, hookName)
	all := append(globalScripts, projectScripts...)

	if len(all) == 0 {
		console.Infof("No %s hooks configured", hookName)
		return nil
	}

	for _, script := range all {
		if err := a.Hooks.RunHook(script, hookName, cwd, repoPath, branchName); err != nil {
			return err
		}
	}

	return nil
}
