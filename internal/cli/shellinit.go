package cli

import (
	"fmt"

	"github.com/irskep/autowt/internal/shellinit"
	"github.com/spf13/cobra"
)

func newShellInitCmd() *cobra.Command {
	var flagDryRun bool

	cmd := &cobra.Command{
		Use:       "shell-init [bash|zsh|fish]",
		Short:     "Generate shell integration code",
		Long: `Generate shell integration code.

Detects your shell automatically from $SHELL, or accepts an
explicit argument.

Prints a shell function that wraps the autowt binary so that
worktree switches cd in your current shell.

Setup:
  bash: eval "$(autowt shell-init)"       # add to ~/.bashrc
  zsh:  eval "$(autowt shell-init)"       # add to ~/.zshrc
  fish: autowt shell-init | source        # add to ~/.config/fish/config.fish`,
		Args:      cobra.MaximumNArgs(1),
		ValidArgs: shellinit.SupportedShells,
		RunE: func(cmd *cobra.Command, args []string) error {
			shell := ""
			if len(args) > 0 {
				shell = args[0]
			} else {
				shell = shellinit.DetectShell()
				if shell == "" {
					return fmt.Errorf("could not detect shell from $SHELL. Please specify one: autowt shell-init bash|zsh|fish")
				}
			}

			output, err := shellinit.Generate(shell, flagDryRun)
			if err != nil {
				return err
			}
			fmt.Print(output)
			return nil
		},
	}

	cmd.Flags().BoolVar(&flagDryRun, "dry-run", false, "Print commands instead of eval'ing them")

	return cmd
}
