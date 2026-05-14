package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

func newShellInitCmd() *cobra.Command {
	var flagDryRun bool

	cmd := &cobra.Command{
		Use:       "shell-init [bash|zsh|fish]",
		Short:     "Generate shell integration code",
		Args:      cobra.MaximumNArgs(1),
		ValidArgs: []string{"bash", "zsh", "fish"},
		RunE: func(cmd *cobra.Command, args []string) error {
			_ = flagDryRun

			// TODO: implement
			fmt.Println("shell-init: not yet implemented")
			return nil
		},
	}

	cmd.Flags().BoolVar(&flagDryRun, "dry-run", false, "Print commands instead of eval'ing them")

	return cmd
}
