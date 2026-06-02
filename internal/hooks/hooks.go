// Package hooks handles lifecycle hook execution for autowt.
package hooks

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/irskep/autowt/internal/config"
	"github.com/irskep/autowt/internal/model"
	"github.com/irskep/autowt/internal/shellcmd"
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

// IsValidType reports whether hookType is one of the supported hook type names.
func IsValidType(hookType string) bool {
	for _, valid := range AllTypes {
		if hookType == valid {
			return true
		}
	}
	return false
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

	timeout := r.Timeout
	if timeout == 0 {
		timeout = 60 * time.Second
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	if err := shellcmd.Run(ctx, script, workDir, env, os.Stdout, os.Stderr); err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			return fmt.Errorf("%s hook timed out after %s", hookType, timeout)
		}
		return fmt.Errorf("%s hook failed: %w", hookType, err)
	}
	return nil
}

// RunHooks executes global then project hooks in sequence.
// Returns the first error encountered.
func (r *Runner) RunHooks(globalScripts, projectScripts []string, hookType, worktreeDir, mainRepoDir, branchName string) error {
	all := MergeScripts(globalScripts, projectScripts)
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

// MergeScripts returns a new slice containing global scripts followed by project scripts.
func MergeScripts(globalScripts, projectScripts []string) []string {
	all := make([]string, 0, len(globalScripts)+len(projectScripts))
	all = append(all, globalScripts...)
	all = append(all, projectScripts...)
	return all
}

// MergeForCustomScript merges global/project hooks with a custom script's hooks.
func MergeForCustomScript(globalScripts, projectScripts []string, cs *model.CustomScript, hookType string) []string {
	if cs == nil {
		return MergeScripts(globalScripts, projectScripts)
	}
	customHook := customScriptHookField(*cs, hookType)
	if customHook == "" {
		return MergeScripts(globalScripts, projectScripts)
	}
	if cs.InheritHooks {
		all := MergeScripts(globalScripts, projectScripts)
		return append(all, customHook)
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
