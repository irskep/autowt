// Package hooks handles lifecycle hook execution for autowt.
package hooks

import (
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"strings"
	"time"

	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/model"
)

// HookType constants.
const (
	PreCreate       = "pre_create"
	PostCreate      = "post_create"
	PostCreateAsync = "post_create_async"
	SessionInit     = "session_init"
	PreCleanup      = "pre_cleanup"
	PostCleanup     = "post_cleanup"
	PreSwitch       = "pre_switch"
	PostSwitch      = "post_switch"
)

// AllTypes lists every valid hook type name.
var AllTypes = []string{
	PreCreate, PostCreate, PostCreateAsync, SessionInit,
	PreCleanup, PostCleanup, PreSwitch, PostSwitch,
}

// Runner executes lifecycle hooks with proper environment variables.
type Runner struct {
	Timeout time.Duration // per-hook timeout; defaults to 60s
}

// NewRunner creates a Runner with default settings.
func NewRunner() *Runner {
	return &Runner{Timeout: 60 * time.Second}
}

// RunHook executes a single hook script. Returns nil on success.
func (r *Runner) RunHook(script, hookType, worktreeDir, mainRepoDir, branchName string) error {
	if strings.TrimSpace(script) == "" {
		return nil
	}

	slog.Info("Executing hook", "type", hookType)

	env := r.prepareEnv(hookType, worktreeDir, mainRepoDir, branchName)

	// pre_create and post_cleanup run in the main repo (worktree may not exist).
	workDir := worktreeDir
	if hookType == PreCreate || hookType == PostCleanup {
		workDir = mainRepoDir
	}

	cmd := exec.Command("sh", "-c", script)
	cmd.Dir = workDir
	cmd.Env = env
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	timeout := r.Timeout
	if timeout == 0 {
		timeout = 60 * time.Second
	}

	done := make(chan error, 1)
	go func() { done <- cmd.Run() }()

	select {
	case err := <-done:
		if err != nil {
			return fmt.Errorf("%s hook failed: %w", hookType, err)
		}
		return nil
	case <-time.After(timeout):
		if cmd.Process != nil {
			_ = cmd.Process.Kill()
		}
		return fmt.Errorf("%s hook timed out after %s", hookType, timeout)
	}
}

// RunHooks executes global then project hooks in sequence.
// Returns the first error encountered.
func (r *Runner) RunHooks(globalScripts, projectScripts []string, hookType, worktreeDir, mainRepoDir, branchName string) error {
	all := append(globalScripts, projectScripts...)
	for _, script := range all {
		if err := r.RunHook(script, hookType, worktreeDir, mainRepoDir, branchName); err != nil {
			return err
		}
	}
	return nil
}

func (r *Runner) prepareEnv(hookType, worktreeDir, mainRepoDir, branchName string) []string {
	env := os.Environ()
	env = append(env,
		"AUTOWT_WORKTREE_DIR="+worktreeDir,
		"AUTOWT_MAIN_REPO_DIR="+mainRepoDir,
		"AUTOWT_BRANCH_NAME="+branchName,
		"AUTOWT_HOOK_TYPE="+hookType,
	)
	return env
}

// ExtractScripts returns the global and project hook scripts for a given type.
func ExtractScripts(global, project config.HookConfig, hookType string) (globalScripts, projectScripts []string) {
	g := hookField(global, hookType)
	p := hookField(project, hookType)
	if g != "" {
		globalScripts = append(globalScripts, g)
	}
	if p != "" {
		projectScripts = append(projectScripts, p)
	}
	return
}

// MergeForCustomScript merges global/project hooks with a custom script's hooks.
func MergeForCustomScript(globalScripts, projectScripts []string, cs *model.CustomScript, hookType string) []string {
	if cs == nil {
		return append(globalScripts, projectScripts...)
	}
	customHook := customScriptHookField(*cs, hookType)
	if customHook == "" {
		return append(globalScripts, projectScripts...)
	}
	if cs.InheritHooks {
		return append(append(globalScripts, projectScripts...), customHook)
	}
	return []string{customHook}
}

func hookField(hc config.HookConfig, hookType string) string {
	switch hookType {
	case PreCreate:
		return hc.PreCreate
	case PostCreate:
		return hc.PostCreate
	case PostCreateAsync:
		return hc.PostCreateAsync
	case SessionInit:
		return hc.SessionInit
	case PreCleanup:
		return hc.PreCleanup
	case PostCleanup:
		return hc.PostCleanup
	case PreSwitch:
		return hc.PreSwitch
	case PostSwitch:
		return hc.PostSwitch
	default:
		return ""
	}
}

func customScriptHookField(cs model.CustomScript, hookType string) string {
	switch hookType {
	case PreCreate:
		return cs.PreCreate
	case PostCreate:
		return cs.PostCreate
	case PostCreateAsync:
		return cs.PostCreateAsync
	case SessionInit:
		return cs.SessionInit
	case PreCleanup:
		return cs.PreCleanup
	case PostCleanup:
		return cs.PostCleanup
	case PreSwitch:
		return cs.PreSwitch
	case PostSwitch:
		return cs.PostSwitch
	default:
		return ""
	}
}
