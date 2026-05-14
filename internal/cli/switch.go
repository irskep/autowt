package cli

import (
	"fmt"

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
		Use:     "switch [branch]",
		Aliases: []string{"sw", "checkout", "co", "goto", "go"},
		Short:   "Switch to or create a worktree for the specified branch",
		Args:    cobra.MaximumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			_ = flagTerminal
			_ = flagAfterInit
			_ = flagIgnoreSameSession
			_ = flagFrom
			_ = flagCustomScript
			_ = flagDir

			if len(args) == 0 {
				// TODO: interactive TUI
				fmt.Println("switch: interactive mode not yet implemented")
				return nil
			}

			// TODO: implement switch
			fmt.Printf("switch: %s not yet implemented\n", args[0])
			return nil
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
