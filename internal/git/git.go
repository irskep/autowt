// Package git provides git subprocess wrappers for worktree operations.
package git

// Service orchestrates git operations for autowt.
type Service struct{}

// NewService creates a new git Service.
func NewService() *Service {
	return &Service{}
}
