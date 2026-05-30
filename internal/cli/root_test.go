package cli

import (
	"errors"
	"os"
	"testing"
)

func TestIsUnknownCommandErrorDoesNotMatchUnknownFlags(t *testing.T) {
	oldArgs := os.Args
	t.Cleanup(func() { os.Args = oldArgs })
	os.Args = []string{"autowt", "ls", "--badopt"}

	if isUnknownCommandError(errors.New("unknown flag: --badopt")) {
		t.Fatal("unknown flag should not be treated as dynamic branch")
	}
}

func TestIsUnknownCommandErrorMatchesUnknownCommands(t *testing.T) {
	oldArgs := os.Args
	t.Cleanup(func() { os.Args = oldArgs })
	os.Args = []string{"autowt", "feature-branch"}

	if !isUnknownCommandError(errors.New("unknown command \"feature-branch\" for \"autowt\"")) {
		t.Fatal("unknown command should be treated as dynamic branch")
	}
}
