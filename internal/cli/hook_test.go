package cli

import (
	"bytes"
	"strings"
	"testing"

	"github.com/irskep/autowt/internal/hooks"
)

func TestHookHelpListsAllHooks(t *testing.T) {
	cmd := newHookCmd()
	var out bytes.Buffer
	cmd.SetOut(&out)

	if err := cmd.Help(); err != nil {
		t.Fatalf("Help() error: %v", err)
	}

	help := out.String()
	for _, hookType := range hooks.AllTypes {
		if !strings.Contains(help, hookType) {
			t.Errorf("help does not list hook %q:\n%s", hookType, help)
		}
	}
}

func TestHookCommandRejectsUnknownHook(t *testing.T) {
	cmd := newHookCmd()

	err := cmd.RunE(cmd, []string{"not_a_hook"})
	if err == nil {
		t.Fatal("RunE() error = nil, want unknown hook error")
	}
	if !strings.Contains(err.Error(), "unknown hook") {
		t.Fatalf("RunE() error = %q, want unknown hook error", err)
	}
}
