package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

func newConfigCmd() *cobra.Command {
	var flagShow bool

	cmd := &cobra.Command{
		Use:     "config",
		Aliases: []string{"configure", "settings", "cfg", "conf"},
		Short:   "Configure autowt settings",
		RunE: func(cmd *cobra.Command, args []string) error {
			if flagShow {
				// TODO: show config
				fmt.Println("config --show: not yet implemented")
				return nil
			}
			// TODO: interactive config TUI
			fmt.Println("config: interactive mode not yet implemented")
			return nil
		},
	}

	cmd.Flags().BoolVar(&flagShow, "show", false, "Show current configuration values")

	return cmd
}
