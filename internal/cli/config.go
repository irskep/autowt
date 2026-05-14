package cli

import (
	"fmt"
	"os"

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
				return showConfig()
			}
			// TODO: interactive config TUI via bubbletea
			fmt.Fprintln(os.Stderr, "Interactive config editor not yet implemented.")
			fmt.Fprintln(os.Stderr, "Use 'autowt config --show' to view current settings,")
			fmt.Fprintf(os.Stderr, "or edit %s directly.\n", newApp().Config.GlobalConfigFile)
			return nil
		},
	}

	cmd.Flags().BoolVar(&flagShow, "show", false, "Show current configuration values")

	return cmd
}

func showConfig() error {
	a := newApp()

	repoPath, _ := a.Git.FindRepoRoot("")
	cfg, err := a.Config.Load(repoPath, nil)
	if err != nil {
		return err
	}

	fmt.Printf("Terminal mode:       %s\n", cfg.Terminal.Mode)
	fmt.Printf("Always new session:  %v\n", cfg.Terminal.AlwaysNew)
	if cfg.Terminal.Program != "" {
		fmt.Printf("Terminal program:    %s\n", cfg.Terminal.Program)
	}
	fmt.Printf("Directory pattern:   %s\n", cfg.Worktree.DirectoryPattern)
	fmt.Printf("Auto fetch:          %v\n", cfg.Worktree.AutoFetch)
	if cfg.Worktree.BranchPrefix != "" {
		fmt.Printf("Branch prefix:       %s\n", cfg.Worktree.BranchPrefix)
	}
	fmt.Printf("Default cleanup:     %s\n", cfg.Cleanup.DefaultMode)
	if cfg.Scripts.SessionInit != "" {
		fmt.Printf("Session init:        %s\n", cfg.Scripts.SessionInit)
	}
	fmt.Printf("Global config:       %s\n", a.Config.GlobalConfigFile)

	return nil
}
