package cli

import (
	"fmt"

	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/git"
	"github.com/irskep/autowt/internal/github"
	"github.com/irskep/autowt/internal/hooks"
	"github.com/irskep/autowt/internal/prompt"
	"github.com/irskep/autowt/internal/terminal"
)

// opts holds global CLI options parsed from flags and environment.
type opts struct {
	Debug                bool
	AutoConfirm          bool
	ShellIntegrationFile string
}

// app holds all services and options used by CLI commands.
type app struct {
	Opts     opts
	Git      *git.Service
	GitHub   *github.Service
	Terminal *terminal.Service
	Hooks    *hooks.Runner
	Config   *config.Loader
}

// newApp creates a fully initialized app with the current global options.
func newApp() *app {
	o := globalOpts

	ts := terminal.NewService()
	ts.ConfirmSessionSwitch = func(branchName string) bool {
		name := branchName
		if name == "" {
			name = "Worktree"
		}
		return prompt.ConfirmYes(fmt.Sprintf("%s already has a session. Switch to it?", name), o.AutoConfirm)
	}

	return &app{
		Opts:     o,
		Git:      git.NewService(),
		GitHub:   github.NewService(),
		Terminal: ts,
		Hooks:    hooks.NewRunner(),
		Config:   config.NewLoader(),
	}
}
