package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

var allHookTypes = []string{
	"pre_create",
	"post_create",
	"post_create_async",
	"session_init",
	"pre_cleanup",
	"post_cleanup",
	"pre_switch",
	"post_switch",
}

func newHookCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:       "hook <hook_name>",
		Short:     "Run a specific lifecycle hook",
		Args:      cobra.ExactArgs(1),
		ValidArgs: allHookTypes,
		RunE: func(cmd *cobra.Command, args []string) error {
			// TODO: implement
			fmt.Printf("hook %s: not yet implemented\n", args[0])
			return nil
		},
	}
	return cmd
}
