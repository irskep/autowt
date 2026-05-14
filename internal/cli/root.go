// Package cli defines the cobra command tree for autowt.
package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

// version is set at build time via ldflags.
var version = "dev"

var (
	flagDebug      bool
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
			// TODO: list worktrees
			fmt.Println("autowt " + version)
			return nil
		},
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	cmd.PersistentFlags().BoolVarP(&flagDebug, "debug", "", false, "Enable debug logging")
	cmd.PersistentFlags().BoolVarP(&flagAutoConfirm, "yes", "y", false, "Automatically confirm all prompts")

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

// Execute runs the root command.
func Execute() error {
	return newRootCmd().Execute()
}
