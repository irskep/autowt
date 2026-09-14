package terminal

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/irskep/autowt/internal/model"
)

// captureStdout runs fn with stdout redirected and returns what it printed.
func captureStdout(t *testing.T, fn func()) string {
	t.Helper()

	r, w, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	orig := os.Stdout
	os.Stdout = w
	defer func() { os.Stdout = orig }()

	fn()

	w.Close()
	out, err := io.ReadAll(r)
	if err != nil {
		t.Fatal(err)
	}
	return string(out)
}

// newTestService returns a Service with no terminal backend, standing in for a
// terminal autowt cannot automate.
func newTestService(t *testing.T) *Service {
	t.Helper()
	t.Setenv("AUTOWT_TEST_FORCE_ECHO", "")
	return &Service{}
}

func TestInplaceWritesToShellIntegrationFile(t *testing.T) {
	s := newTestService(t)
	file := filepath.Join(t.TempDir(), "integration")

	out := captureStdout(t, func() {
		err := s.SwitchToWorktree(SwitchOpts{
			WorktreePath:         "/tmp/wt",
			Mode:                 model.TerminalModeInplace,
			ShellIntegrationFile: file,
		})
		if err != nil {
			t.Errorf("SwitchToWorktree() error: %v", err)
		}
	})

	contents, err := os.ReadFile(file)
	if err != nil {
		t.Fatalf("shell integration file not written: %v", err)
	}
	if string(contents) != "cd '/tmp/wt'" {
		t.Errorf("shell integration file = %q, want %q", contents, "cd '/tmp/wt'")
	}
	if out != "" {
		t.Errorf("stdout = %q, want nothing", out)
	}
}

func TestInplaceWithoutShellIntegrationPrints(t *testing.T) {
	s := newTestService(t)

	out := captureStdout(t, func() {
		if err := s.SwitchToWorktree(SwitchOpts{
			WorktreePath: "/tmp/wt",
			Mode:         model.TerminalModeInplace,
		}); err != nil {
			t.Errorf("SwitchToWorktree() error: %v", err)
		}
	})

	if strings.TrimSpace(out) != "cd '/tmp/wt'" {
		t.Errorf("stdout = %q, want %q", out, "cd '/tmp/wt'")
	}
}

func TestEchoIgnoresShellIntegrationFile(t *testing.T) {
	s := newTestService(t)
	file := filepath.Join(t.TempDir(), "integration")

	out := captureStdout(t, func() {
		if err := s.SwitchToWorktree(SwitchOpts{
			WorktreePath:         "/tmp/wt",
			Mode:                 model.TerminalModeEcho,
			ShellIntegrationFile: file,
		}); err != nil {
			t.Errorf("SwitchToWorktree() error: %v", err)
		}
	})

	if strings.TrimSpace(out) != "cd '/tmp/wt'" {
		t.Errorf("stdout = %q, want %q", out, "cd '/tmp/wt'")
	}
	if _, err := os.Stat(file); !os.IsNotExist(err) {
		t.Error("echo mode should not write the shell integration file")
	}
}

func TestUnsupportedTerminalFallsBackToShellIntegration(t *testing.T) {
	s := newTestService(t)

	for _, mode := range []model.TerminalMode{model.TerminalModeTab, model.TerminalModeWindow} {
		file := filepath.Join(t.TempDir(), "integration")

		captureStdout(t, func() {
			if err := s.SwitchToWorktree(SwitchOpts{
				WorktreePath:         "/tmp/wt",
				Mode:                 mode,
				ShellIntegrationFile: file,
			}); err != nil {
				t.Errorf("SwitchToWorktree(%s) error: %v", mode, err)
			}
		})

		contents, err := os.ReadFile(file)
		if err != nil {
			t.Fatalf("%s: shell integration file not written: %v", mode, err)
		}
		if string(contents) != "cd '/tmp/wt'" {
			t.Errorf("%s: shell integration file = %q, want %q", mode, contents, "cd '/tmp/wt'")
		}
	}
}

func TestUnknownModeIsAnError(t *testing.T) {
	s := newTestService(t)

	if err := s.SwitchToWorktree(SwitchOpts{
		WorktreePath: "/tmp/wt",
		Mode:         model.TerminalMode("nonsense"),
	}); err == nil {
		t.Error("expected an error for an unknown terminal mode")
	}
}
