package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

func newLsCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:     "ls",
		Aliases: []string{"list", "ll"},
		Short:   "List all worktrees and their status",
		RunE: func(cmd *cobra.Command, args []string) error {
			// TODO: implement
			fmt.Println("ls: not yet implemented")
			return nil
		},
	}
	return cmd
}
