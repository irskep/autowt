// Package github provides integration with the GitHub CLI (gh).
package github

// Service handles GitHub-specific operations via the gh CLI.
type Service struct{}

// NewService creates a new GitHub Service.
func NewService() *Service {
	return &Service{}
}
