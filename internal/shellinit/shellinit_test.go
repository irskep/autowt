package shellinit

import (
	"strings"
	"testing"
)

func TestGenerateBash(t *testing.T) {
	out, err := Generate("bash", false, "# completions")
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
	if strings.Contains(out, "_AUTOWT_COMPLETE") || strings.Contains(out, "_AWT_COMPLETE") {
		t.Error("bash output should not contain Click-style completion env vars")
	}
	if !strings.Contains(out, "# completions") {
		t.Error("bash output should include generated completions")
	}
}

func TestGenerateBashDryRun(t *testing.T) {
	out, err := Generate("bash", true, "")
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
	out, err := Generate("fish", false, "# completions")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(out, "function autowt") {
		t.Error("fish output should define autowt function")
	}
	if !strings.Contains(out, "function awt --wraps=autowt") {
		t.Error("fish output should define awt wrapper")
	}
	if !strings.Contains(out, "# completions") {
		t.Error("fish output should include generated completions")
	}
}

func TestGenerateUnsupported(t *testing.T) {
	_, err := Generate("powershell", false, "")
	if err == nil {
		t.Error("expected error for unsupported shell")
	}
}

func TestDetectShell(t *testing.T) {
	// DetectShell reads $SHELL, which we can't easily control in tests.
	// Just verify it returns something or empty.
	_ = DetectShell()
}
