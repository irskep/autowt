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

	console.Plain(fmt.Sprintf("Terminal mode:       %s", cfg.Terminal.Mode))
	console.Plain(fmt.Sprintf("Always new session:  %v", cfg.Terminal.AlwaysNew))
	if cfg.Terminal.Program != "" {
		console.Plain(fmt.Sprintf("Terminal program:    %s", cfg.Terminal.Program))
	}
	console.Plain(fmt.Sprintf("Directory pattern:   %s", cfg.Worktree.DirectoryPattern))
	console.Plain(fmt.Sprintf("Auto fetch:          %v", cfg.Worktree.AutoFetch))
	if cfg.Worktree.BranchPrefix != "" {
		console.Plain(fmt.Sprintf("Branch prefix:       %s", cfg.Worktree.BranchPrefix))
	}
	console.Plain(fmt.Sprintf("Default cleanup:     %s", cfg.Cleanup.DefaultMode))
	if cfg.Scripts.SessionInit != "" {
		console.Plain(fmt.Sprintf("Session init:        %s", cfg.Scripts.SessionInit))
	}
	console.Plain(fmt.Sprintf("Global config:       %s", a.Config.GlobalConfigFile))

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
