// Package terminal handles terminal mode dispatch for worktree switching.
package terminal

import (
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"strings"

	atdetect "github.com/irskep/automate-terminal/detect"
	atexec "github.com/irskep/automate-terminal/exec"
	atterminal "github.com/irskep/automate-terminal/terminal"
	"github.com/irskep/autowt/internal/model"
)

// Service routes worktree switches to the appropriate terminal backend.
type Service struct {
	runner   *atexec.Runner
	terminal atterminal.Terminal

	// ConfirmSessionSwitch is called to ask the user whether to switch to
	// an existing session. If nil, switches happen without prompting.
	// Not safe for concurrent use.
	ConfirmSessionSwitch func(branchName string) bool
}

// NewService creates a terminal Service, detecting the current terminal.
func NewService() *Service {
	runner := &atexec.Runner{}
	return &Service{
		runner:   runner,
		terminal: atdetect.Detect(runner),
	}
}

// SwitchOpts bundles all parameters for SwitchToWorktree.
type SwitchOpts struct {
	WorktreePath         string
	Mode                 model.TerminalMode
	SessionInitScript    string
	AfterInit            string
	BranchName           string
	IgnoreSameSession    bool
	ShellIntegrationFile string
}

// SwitchToWorktree switches to a worktree using the given mode.
func (s *Service) SwitchToWorktree(o SwitchOpts) error {
	mode := o.Mode

	// Override to echo if test env var is set.
	if os.Getenv("AUTOWT_TEST_FORCE_ECHO") != "" {
		mode = model.TerminalModeEcho
	}

	switch mode {
	case model.TerminalModeEcho:
		return s.echoCommands(o.WorktreePath, o.SessionInitScript, o.AfterInit, o.ShellIntegrationFile)
	case model.TerminalModeInplace:
		return s.inplaceCommands(o.WorktreePath, o.SessionInitScript, o.AfterInit)
	case model.TerminalModeTab:
		return s.tabMode(o)
	case model.TerminalModeWindow:
		return s.windowMode(o)
	case model.TerminalModeVSCode:
		return s.editorMode("code", "VSCode", o.WorktreePath, o.SessionInitScript, o.AfterInit)
	case model.TerminalModeCursor:
		return s.editorMode("cursor", "Cursor", o.WorktreePath, o.SessionInitScript, o.AfterInit)
	default:
		return fmt.Errorf("unknown terminal mode: %s", mode)
	}
}

func (s *Service) echoCommands(worktreePath, sessionInit, afterInit, shellIntegrationFile string) error {
	line := buildCommandLine(worktreePath, sessionInit, afterInit)
	if shellIntegrationFile != "" {
		return os.WriteFile(shellIntegrationFile, []byte(line), 0o644)
	}
	fmt.Println(line)
	return nil
}

func (s *Service) inplaceCommands(worktreePath, sessionInit, afterInit string) error {
	line := buildCommandLine(worktreePath, sessionInit, afterInit)
	if s.terminal != nil {
		if err := s.terminal.RunInActiveSession(line); err == nil {
			return nil
		}
		slog.Warn("Inplace execution failed, falling back to echo")
	}
	fmt.Println(line)
	return nil
}

func (s *Service) tabMode(o SwitchOpts) error {
	if s.terminal == nil {
		slog.Warn("No terminal detected, falling back to echo")
		return s.echoCommands(o.WorktreePath, o.SessionInitScript, o.AfterInit, o.ShellIntegrationFile)
	}

	caps := s.terminal.GetCapabilities()
	if !caps.CanCreateTabs {
		slog.Warn("Terminal does not support tabs, falling back to echo")
		return s.echoCommands(o.WorktreePath, o.SessionInitScript, o.AfterInit, o.ShellIntegrationFile)
	}

	pasteScript := combineScripts(o.SessionInitScript, o.AfterInit)

	// Warn if terminal can't paste scripts.
	if pasteScript != nil && !caps.CanPasteCommands {
		fmt.Fprintf(os.Stderr, "Warning: %s cannot execute paste scripts.\n", s.terminal.DisplayName())
		fmt.Fprintf(os.Stderr, "You will need to run these commands manually:\n  %s\n", *pasteScript)
	}

	// Try to switch to existing session.
	if !o.IgnoreSameSession && caps.CanSwitchToSession {
		if sid := s.terminal.FindSessionByWorkingDirectory(o.WorktreePath, true); sid != nil {
			if s.shouldSwitchToExisting(o.BranchName) {
				if err := s.terminal.SwitchToSession(*sid, pasteScript); err == nil {
					fmt.Fprintf(os.Stderr, "Switched to existing %s session\n", displayName(o.BranchName))
					return nil
				}
			}
		}
	}

	return s.terminal.OpenNewTab(o.WorktreePath, pasteScript)
}

func (s *Service) windowMode(o SwitchOpts) error {
	if s.terminal == nil {
		slog.Warn("No terminal detected, falling back to echo")
		return s.echoCommands(o.WorktreePath, o.SessionInitScript, o.AfterInit, o.ShellIntegrationFile)
	}

	caps := s.terminal.GetCapabilities()
	if !caps.CanCreateWindows {
		slog.Warn("Terminal does not support windows, falling back to echo")
		return s.echoCommands(o.WorktreePath, o.SessionInitScript, o.AfterInit, o.ShellIntegrationFile)
	}

	pasteScript := combineScripts(o.SessionInitScript, o.AfterInit)

	// Warn if terminal can't paste scripts.
	if pasteScript != nil && !caps.CanPasteCommands {
		fmt.Fprintf(os.Stderr, "Warning: %s cannot execute paste scripts.\n", s.terminal.DisplayName())
		fmt.Fprintf(os.Stderr, "You will need to run these commands manually:\n  %s\n", *pasteScript)
	}

	// Try to switch to existing session.
	if !o.IgnoreSameSession && caps.CanSwitchToSession {
		if sid := s.terminal.FindSessionByWorkingDirectory(o.WorktreePath, true); sid != nil {
			if s.shouldSwitchToExisting(o.BranchName) {
				if err := s.terminal.SwitchToSession(*sid, pasteScript); err == nil {
					fmt.Fprintf(os.Stderr, "Switched to existing %s session\n", displayName(o.BranchName))
					return nil
				}
			}
		}
	}

	return s.terminal.OpenNewWindow(o.WorktreePath, pasteScript)
}

func (s *Service) editorMode(cliCmd, editorName, worktreePath, sessionInit, afterInit string) error {
	if _, err := exec.LookPath(cliCmd); err != nil {
		slog.Warn("Editor CLI not found, falling back to echo", "editor", editorName, "command", cliCmd)
		return s.echoCommands(worktreePath, sessionInit, afterInit, "")
	}

	combined := combineScripts(sessionInit, afterInit)
	if combined != nil {
		fmt.Fprintf(os.Stderr, "Warning: %s cannot execute initialization scripts.\n", editorName)
		fmt.Fprintf(os.Stderr, "You will need to run these commands manually:\n  %s\n", *combined)
	}

	cmd := exec.Command(cliCmd, worktreePath)
	return cmd.Run()
}

func (s *Service) shouldSwitchToExisting(branchName string) bool {
	if s.ConfirmSessionSwitch != nil {
		return s.ConfirmSessionSwitch(branchName)
	}
	return true
}

func buildCommandLine(worktreePath, sessionInit, afterInit string) string {
	parts := []string{fmt.Sprintf("cd %s", shellQuote(worktreePath))}
	if s := normalizeScript(sessionInit); s != "" {
		parts = append(parts, s)
	}
	if s := normalizeScript(afterInit); s != "" {
		parts = append(parts, s)
	}
	return strings.Join(parts, "; ")
}

func combineScripts(sessionInit, afterInit string) *string {
	var parts []string
	if sessionInit != "" {
		parts = append(parts, sessionInit)
	}
	if afterInit != "" {
		parts = append(parts, afterInit)
	}
	if len(parts) == 0 {
		return nil
	}
	combined := strings.Join(parts, "; ")
	return &combined
}

func normalizeScript(s string) string {
	s = strings.TrimSpace(s)
	s = strings.ReplaceAll(s, "\n", "; ")
	return strings.TrimSpace(s)
}

func shellQuote(s string) string {
	return "'" + strings.ReplaceAll(s, "'", `'\''`) + "'"
}

func displayName(branchName string) string {
	if branchName != "" {
		return branchName
	}
	return "worktree"
}
