// Package cli defines the cobra command tree for autowt.
package cli

import (
	"fmt"
	"log/slog"
	"os"
	"strings"

	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/git"
	"github.com/irskep/autowt/internal/prompt"
	"github.com/irskep/autowt/internal/versioncheck"
	"github.com/spf13/cobra"
)

// version is set at build time via ldflags.
var version = "dev"

var (
	flagDebug       bool
	flagAutoConfirm bool
)

func newRootCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "autowt",
		Short: "Git worktree manager",
		Long: `Git worktree manager. Available as: autowt, awt

Use subcommands like 'ls', 'cleanup', 'config', or 'switch'.
Or simply run 'autowt <branch>' to switch to a branch.`,
		// No subcommand -> list worktrees. If args are present,
		// treat the first one as a branch name (dynamic command).
		Args: cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) > 0 {
				return runDynamicBranch(args[0], args[1:])
			}
			return runLs()
		},
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	cmd.PersistentFlags().BoolVar(&flagDebug, "debug", false, "Enable debug logging")
	cmd.PersistentFlags().BoolVarP(&flagAutoConfirm, "yes", "y", false, "Automatically confirm all prompts")

	cmd.PersistentPreRun = func(cmd *cobra.Command, args []string) {
		level := slog.LevelWarn
		if flagDebug {
			level = slog.LevelDebug
		}
		slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: level})))

		// Propagate auto-confirm to the prompt package.
		prompt.AutoConfirm = flagAutoConfirm

		// Version update check (rate-limited, non-blocking).
		stateDir := config.DefaultStateDir()
		versioncheck.Print(versioncheck.Check(version, stateDir))
	}

	// Pop AUTOWT_SHELL_INTEGRATION_FILE from env early.
	shellIntegrationFile = os.Getenv("AUTOWT_SHELL_INTEGRATION_FILE")
	os.Unsetenv("AUTOWT_SHELL_INTEGRATION_FILE")

	cmd.Version = version
	cmd.SetVersionTemplate("{{.Version}}\n")

	// Register built-in subcommands.
	builtinGroup := &cobra.Group{ID: "builtin", Title: "Commands:"}
	customGroup := &cobra.Group{ID: "custom", Title: "Custom Scripts:"}
	cmd.AddGroup(builtinGroup, customGroup)

	for _, sub := range []*cobra.Command{
		newLsCmd(),
		newSwitchCmd(),
		newCleanupCmd(),
		newConfigCmd(),
		newShellInitCmd(),
		newHookCmd(),
	} {
		sub.GroupID = "builtin"
		cmd.AddCommand(sub)
	}

	// Register custom scripts from config as subcommands.
	registerCustomScriptCommands(cmd, customGroup.ID)

	return cmd
}

// registerCustomScriptCommands loads config and adds cobra commands for
// each custom script. Errors are silently ignored (config may not exist).
func registerCustomScriptCommands(parent *cobra.Command, groupID string) {
	loader := config.NewLoader()
	gitSvc := git.NewService()

	// Try to find the repo root for project config.
	repoPath, _ := gitSvc.FindRepoRoot("")

	cfg, err := loader.Load(repoPath, nil)
	if err != nil {
		return
	}
	for name, cs := range cfg.Scripts.Custom {
		sub := newCustomScriptCmd(name, cs.Description)
		sub.GroupID = groupID
		parent.AddCommand(sub)
	}
}

func newCustomScriptCmd(name, description string) *cobra.Command {
	var (
		flagTerminal          string
		flagAfterInit         string
		flagIgnoreSameSession bool
		flagFrom              string
		flagDir               string
	)

	help := description
	if help == "" {
		help = fmt.Sprintf("Run custom script '%s'", name)
	}

	cmd := &cobra.Command{
		Use:   fmt.Sprintf("%s [args...]", name),
		Short: help,
		Args:  cobra.ArbitraryArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			// Build the script spec: "name arg1 arg2 ..."
			spec := name
			if len(args) > 0 {
				spec += " " + strings.Join(args, " ")
			}

			return runSwitch(switchOpts{
				CustomScript:      spec,
				Terminal:          flagTerminal,
				AfterInit:         flagAfterInit,
				IgnoreSameSession: flagIgnoreSameSession,
				From:              flagFrom,
				Dir:               flagDir,
				FromDynamic:       true,
			})
		},
	}

	cmd.Flags().StringVar(&flagTerminal, "terminal", "", "How to open the worktree terminal")
	cmd.Flags().StringVar(&flagAfterInit, "after-init", "", "Command to run after session_init")
	cmd.Flags().BoolVar(&flagIgnoreSameSession, "ignore-same-session", false, "Always create new terminal")
	cmd.Flags().StringVar(&flagFrom, "from", "", "Source branch/commit to create worktree from")
	cmd.Flags().StringVar(&flagDir, "dir", "", "Directory path for the new worktree")

	return cmd
}

// Execute runs the root command. Unknown subcommands are treated as branch names.
func Execute() error {
	root := newRootCmd()

	err := root.Execute()
	if err != nil {
		// Check if the error is "unknown command" — treat as branch name.
		if isUnknownCommandError(err) {
			branch := os.Args[1]
			return runDynamicBranch(branch, os.Args[2:])
		}
		fmt.Fprintln(os.Stderr, err)
	}
	return err
}

func isUnknownCommandError(err error) bool {
	if err == nil || len(os.Args) < 2 {
		return false
	}
	msg := err.Error()
	return strings.Contains(msg, "unknown command") || strings.Contains(msg, "unknown flag")
}
