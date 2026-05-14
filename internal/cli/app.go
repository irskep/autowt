package cli

import (
	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/git"
	"github.com/irskep/autowt/internal/github"
	"github.com/irskep/autowt/internal/hooks"
	"github.com/irskep/autowt/internal/terminal"
)

// app holds all services used by CLI commands.
type app struct {
	Git      *git.Service
	GitHub   *github.Service
	Terminal *terminal.Service
	Hooks    *hooks.Runner
	Config   *config.Loader
}

// newApp creates a fully initialized app.
func newApp() *app {
	return &app{
		Git:      git.NewService(),
		GitHub:   github.NewService(),
		Terminal: terminal.NewService(),
		Hooks:    hooks.NewRunner(),
		Config:   config.NewLoader(),
	}
}

// shellIntegrationFile is the path set by shell integration, or empty.
var shellIntegrationFile string
