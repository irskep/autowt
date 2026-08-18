// Package forge integrates with code-hosting CLIs (gh, glab) so autowt can
// read the state of the pull or merge request belonging to a branch.
package forge

import (
	"fmt"
	"os"
	"strings"

	"github.com/irskep/autowt/internal/model"
)

// Provider describes one code-hosting service and the CLI that talks to it.
type Provider interface {
	// Name is the human-readable service name, like "GitHub".
	Name() string
	// CLIName is the command line tool autowt shells out to, like "gh".
	CLIName() string
	// InstallURL points at instructions for installing that tool.
	InstallURL() string
	// RequestNoun is the singular name for a change request on this service,
	// like "pull request".
	RequestNoun() string
	// CleanupMode is the cleanup mode that selects this provider.
	CleanupMode() model.CleanupMode
	// UsernameVar is the branch prefix template variable holding the
	// authenticated username, like "github_username".
	UsernameVar() string
	// Available reports whether the CLI is on PATH.
	Available() bool
	// Username returns the authenticated username, or an empty string.
	Username() string
	// RequestStatus returns "merged", "closed", "open", or an empty string
	// when the branch has no request.
	RequestStatus(repoPath, branch string) string
	// matchesRemote reports whether a remote URL is hosted by this service.
	matchesRemote(remoteURL string) bool
}

// Providers returns every supported forge.
func Providers() []Provider {
	return []Provider{gitHub{}, gitLab{}}
}

// ForCleanupMode returns the provider a cleanup mode asks for.
func ForCleanupMode(mode model.CleanupMode) (Provider, bool) {
	for _, p := range Providers() {
		if p.CleanupMode() == mode {
			return p, true
		}
	}
	return nil, false
}

// Detect returns the provider hosting a repository's origin remote.
func Detect(repoPath string) (Provider, bool) {
	remote, err := gitOutput(repoPath, "remote", "get-url", "origin")
	if err != nil {
		return nil, false
	}
	for _, p := range Providers() {
		if p.matchesRemote(remote) {
			return p, true
		}
	}
	return nil, false
}

// AnalyzeBranchesForCleanup returns a BranchStatus per worktree, treating
// branches whose request is merged or closed as ready for removal.
func AnalyzeBranchesForCleanup(
	p Provider,
	repoPath string,
	worktrees []model.WorktreeInfo,
	hasUncommittedChanges func(string) bool,
) ([]model.BranchStatus, error) {
	if !p.Available() {
		return nil, MissingCLIError(p)
	}

	var statuses []model.BranchStatus
	for _, wt := range worktrees {
		state := p.RequestStatus(repoPath, wt.Branch)
		statuses = append(statuses, model.BranchStatus{
			Branch:                wt.Branch,
			HasRemote:             true,
			IsMerged:              state == "merged" || state == "closed",
			IsIdentical:           false,
			Path:                  wt.Path,
			HasUncommittedChanges: hasUncommittedChanges(wt.Path),
		})
	}
	return statuses, nil
}

// MissingCLIError explains that a provider's CLI needs to be installed.
func MissingCLIError(p Provider) error {
	return fmt.Errorf(
		"%s cleanup requires the '%s' CLI tool. Install it from: %s",
		p.Name(), p.CLIName(), p.InstallURL(),
	)
}

// statusFromStates reduces the states of a branch's requests to the most
// final one: merged beats closed, and closed beats open.
func statusFromStates(states []string) string {
	found := make(map[string]bool, len(states))
	for _, state := range states {
		found[normalizeState(state)] = true
	}
	for _, state := range []string{"merged", "closed", "open"} {
		if found[state] {
			return state
		}
	}
	return ""
}

// normalizeState maps service-specific state names onto autowt's names.
func normalizeState(state string) string {
	switch strings.ToLower(strings.TrimSpace(state)) {
	case "merged":
		return "merged"
	case "closed":
		return "closed"
	// GitLab reports open requests as "opened", and locks the ones under
	// discussion lock, which are still open.
	case "open", "opened", "locked":
		return "open"
	default:
		return ""
	}
}

// remoteHost extracts the hostname from a remote URL. It handles HTTPS
// (https://host/group/repo.git), SSH (ssh://git@host:22/group/repo.git), and
// scp-style (git@host:group/repo.git) remotes, and returns an empty string for
// local paths.
func remoteHost(remoteURL string) string {
	host := strings.TrimSpace(remoteURL)
	if i := strings.Index(host, "://"); i >= 0 {
		host = host[i+3:]
	}
	if i := strings.LastIndex(host, "@"); i >= 0 {
		host = host[i+1:]
	}
	if i := strings.IndexAny(host, ":/"); i >= 0 {
		host = host[:i]
	}
	return strings.ToLower(host)
}

// hostContains reports whether a remote URL's host contains a fragment, so
// that self-hosted instances like gitlab.example.com are recognized.
func hostContains(remoteURL, fragment string) bool {
	return strings.Contains(remoteHost(remoteURL), fragment)
}

// hostMatchesEnv reports whether a remote URL points at the host named by an
// environment variable, which is how gh and glab are aimed at self-hosted
// instances.
func hostMatchesEnv(remoteURL, envVar string) bool {
	host := remoteHost(os.Getenv(envVar))
	if host == "" {
		return false
	}
	return remoteHost(remoteURL) == host
}
