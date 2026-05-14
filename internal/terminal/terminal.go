// Package terminal handles terminal mode dispatch for worktree switching.
package terminal

// Service routes worktree switches to the appropriate terminal backend.
type Service struct{}

// NewService creates a new terminal Service.
func NewService() *Service {
	return &Service{}
}
