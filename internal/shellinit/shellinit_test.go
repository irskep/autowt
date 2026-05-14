package shellinit

import (
	"strings"
	"testing"
)

func TestGenerateBash(t *testing.T) {
	out, err := Generate("bash", false)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "AUTOWT_SHELL_INTEGRATION_FILE") {
		t.Error("bash output should contain AUTOWT_SHELL_INTEGRATION_FILE")
	}
	if !strings.Contains(out, "alias awt=autowt") {
		t.Error("bash output should contain awt alias")
	}
	if !strings.Contains(out, `eval "$eval_cmd"`) {
		t.Error("bash output should contain eval")
	}
}

func TestGenerateBashDryRun(t *testing.T) {
	out, err := Generate("bash", true)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "dry-run") {
		t.Error("dry-run output should contain 'dry-run'")
	}
	if strings.Contains(out, `eval "$eval_cmd"`) {
		t.Error("dry-run output should NOT contain eval")
	}
}

func TestGenerateFish(t *testing.T) {
	out, err := Generate("fish", false)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "function autowt") {
		t.Error("fish output should define autowt function")
	}
	if !strings.Contains(out, "function awt --wraps=autowt") {
		t.Error("fish output should define awt wrapper")
	}
}

func TestGenerateUnsupported(t *testing.T) {
	_, err := Generate("powershell", false)
	if err == nil {
		t.Error("expected error for unsupported shell")
	}
}

func TestDetectShell(t *testing.T) {
	// DetectShell reads $SHELL, which we can't easily control in tests.
	// Just verify it returns something or empty.
	_ = DetectShell()
}
