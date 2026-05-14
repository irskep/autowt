package cli

import (
	"fmt"

	"github.com/irskep/autowt/internal/console"
	"github.com/irskep/autowt/internal/ui"
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
			return editConfig()
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

func editConfig() error {
	a := newApp()

	cfg, err := a.Config.LoadGlobalOnly()
	if err != nil {
		return err
	}

	result, err := ui.RunConfigTUI(cfg)
	if err != nil {
		return err
	}
	if result == nil {
		console.Info("Configuration edit cancelled.")
		return nil
	}

	if err := a.Config.SaveConfig(*result); err != nil {
		return fmt.Errorf("failed to save configuration: %w", err)
	}

	console.Success("Configuration saved.")
	return nil
}
