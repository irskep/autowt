// Package hooks handles lifecycle hook execution for autowt.
package hooks

// Runner executes lifecycle hooks with environment variables.
type Runner struct{}

// NewRunner creates a new hook Runner.
func NewRunner() *Runner {
	return &Runner{}
}
