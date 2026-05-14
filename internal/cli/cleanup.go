package cli

import (
	"fmt"

	"github.com/spf13/cobra"
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
			_ = flagMode
			_ = flagDryRun
			_ = flagForce

			// TODO: implement
			fmt.Println("cleanup: not yet implemented")
			return nil
		},
	}

	cmd.Flags().StringVar(&flagMode, "mode", "", "Cleanup mode (all, remoteless, merged, interactive, github)")
	cmd.Flags().BoolVar(&flagDryRun, "dry-run", false, "Show what would be removed without actually removing")
	cmd.Flags().BoolVar(&flagForce, "force", false, "Force remove worktrees with modified files")

	return cmd
}
