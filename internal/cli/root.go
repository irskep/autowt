// Package cli defines the cobra command tree for autowt.
package cli

import (
	"fmt"
	"os"

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
		// No subcommand -> list worktrees.
		RunE: func(cmd *cobra.Command, args []string) error {
			return runLs()
		},
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	cmd.PersistentFlags().BoolVar(&flagDebug, "debug", false, "Enable debug logging")
	cmd.PersistentFlags().BoolVarP(&flagAutoConfirm, "yes", "y", false, "Automatically confirm all prompts")

	// Pop AUTOWT_SHELL_INTEGRATION_FILE from env early.
	shellIntegrationFile = os.Getenv("AUTOWT_SHELL_INTEGRATION_FILE")
	os.Unsetenv("AUTOWT_SHELL_INTEGRATION_FILE")

	cmd.Version = version
	cmd.SetVersionTemplate("{{.Version}}\n")

	// Register subcommands.
	cmd.AddCommand(
		newLsCmd(),
		newSwitchCmd(),
		newCleanupCmd(),
		newConfigCmd(),
		newShellInitCmd(),
		newHookCmd(),
	)

	return cmd
}

// Execute runs the root command. Unknown subcommands are treated as branch names.
func Execute() error {
	root := newRootCmd()

	// Intercept unknown subcommand errors and treat them as branch names.
	root.SetFlagErrorFunc(func(cmd *cobra.Command, err error) error {
		return err
	})

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
	return len(msg) > 0 && (contains(msg, "unknown command") || contains(msg, "unknown flag"))
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && searchString(s, substr)
}

func searchString(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
