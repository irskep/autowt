package cli

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/irskep/autowt/internal/docs"
	"github.com/mattn/go-isatty"
	"github.com/spf13/cobra"
)

type docsFlags struct {
	Plain bool
	Roff  bool
}

func newDocsCmd() *cobra.Command {
	flags := docsFlags{}
	cmd := &cobra.Command{
		Use:   "docs",
		Short: "Read the built-in documentation",
		Long:  "Read the built-in autowt documentation in your terminal.",
		Args:  cobra.NoArgs,
		RunE: func(cmd *cobra.Command, args []string) error {
			return runDocs(flags)
		},
	}
	cmd.Flags().BoolVar(&flags.Plain, "plain", false, "print plain text instead of opening a pager")
	cmd.Flags().BoolVar(&flags.Roff, "roff", false, "print roff man page source")
	return cmd
}

func runDocs(flags docsFlags) error {
	if flags.Roff {
		_, err := fmt.Print(docs.ManPage())
		return err
	}
	if flags.Plain || !stdoutIsTerminal() {
		_, err := fmt.Print(docs.PlainText())
		return err
	}

	path, cleanup, err := writeTempManPage(docs.ManPage())
	if err != nil {
		return err
	}
	defer cleanup()

	if err := renderManPage(path); err != nil {
		_, printErr := fmt.Print(docs.PlainText())
		return printErr
	}
	return nil
}

func stdoutIsTerminal() bool {
	return isatty.IsTerminal(os.Stdout.Fd())
}

func writeTempManPage(content string) (string, func(), error) {
	file, err := os.CreateTemp("", "autowt-docs-*.1")
	if err != nil {
		return "", func() {}, err
	}
	path := file.Name()
	if _, err := file.WriteString(content); err != nil {
		file.Close()
		os.Remove(path)
		return "", func() {}, err
	}
	if err := file.Close(); err != nil {
		os.Remove(path)
		return "", func() {}, err
	}
	return path, func() { os.Remove(path) }, nil
}

func renderManPage(path string) error {
	cmd := exec.Command("man", path)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
