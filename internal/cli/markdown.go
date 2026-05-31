package cli

import (
	"bufio"
	"bytes"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra/doc"
)

func GenerateMarkdownDocs(outDir string) error {
	if strings.TrimSpace(outDir) == "" {
		return fmt.Errorf("output directory is required")
	}
	if err := os.RemoveAll(outDir); err != nil {
		return err
	}
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}

	root := newRootCmdWithOptions(rootCmdOptions{IncludeCustomScripts: false})
	root.SetOut(io.Discard)
	root.SetErr(io.Discard)
	root.DisableAutoGenTag = true

	if err := doc.GenMarkdownTreeCustom(root, outDir, func(filename string) string {
		if filepath.Base(filename) == "autowt.md" {
			return "# Command Reference\n\n"
		}
		return ""
	}, func(link string) string {
		return link
	}); err != nil {
		return err
	}
	return fenceIndentedCodeBlocks(outDir)
}

func fenceIndentedCodeBlocks(root string) error {
	return filepath.WalkDir(root, func(path string, entry os.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() || filepath.Ext(path) != ".md" {
			return nil
		}
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		rewritten := rewriteIndentedCodeBlocks(content)
		if bytes.Equal(content, rewritten) {
			return nil
		}
		return os.WriteFile(path, rewritten, 0o644)
	})
}

func rewriteIndentedCodeBlocks(markdown []byte) []byte {
	var out bytes.Buffer
	scanner := bufio.NewScanner(bytes.NewReader(markdown))
	inIndentedBlock := false
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "\t") {
			if !inIndentedBlock {
				out.WriteString("```sh\n")
				inIndentedBlock = true
			}
			out.WriteString(strings.TrimPrefix(line, "\t"))
			out.WriteByte('\n')
			continue
		}
		if inIndentedBlock {
			out.WriteString("```\n")
			inIndentedBlock = false
		}
		out.WriteString(line)
		out.WriteByte('\n')
	}
	if inIndentedBlock {
		out.WriteString("```\n")
	}
	return out.Bytes()
}
