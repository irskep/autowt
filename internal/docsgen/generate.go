package docsgen

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/BurntSushi/toml"
)

type Options struct {
	SourceDir    string
	ManifestPath string
	OutDir       string
	FilterPath   string
}

type manifest struct {
	Title       string   `toml:"title"`
	Author      string   `toml:"author"`
	Date        string   `toml:"date"`
	Name        string   `toml:"name"`
	CommandHelp string   `toml:"command_help"`
	Pages       []string `toml:"pages"`
}

func Generate(options Options) error {
	if strings.TrimSpace(options.SourceDir) == "" {
		return fmt.Errorf("source directory is required")
	}
	if strings.TrimSpace(options.OutDir) == "" {
		return fmt.Errorf("output directory is required")
	}
	if strings.TrimSpace(options.ManifestPath) == "" {
		return fmt.Errorf("manifest path is required")
	}

	manifest, err := loadManifest(options.ManifestPath)
	if err != nil {
		return err
	}
	source, err := assembleMarkdown(options.SourceDir, manifest)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(options.OutDir, 0o755); err != nil {
		return err
	}

	tmp, err := os.CreateTemp("", "autowt-docs-*.md")
	if err != nil {
		return err
	}
	tmpPath := tmp.Name()
	defer os.Remove(tmpPath)
	if _, err := tmp.Write(source); err != nil {
		tmp.Close()
		return err
	}
	if err := tmp.Close(); err != nil {
		return err
	}

	if err := runPandoc(tmpPath, options.FilterPath, "man", filepath.Join(options.OutDir, "autowt.1")); err != nil {
		return err
	}
	if err := runPandoc(tmpPath, options.FilterPath, "plain", filepath.Join(options.OutDir, "autowt.txt")); err != nil {
		return err
	}
	return nil
}

func loadManifest(path string) (manifest, error) {
	var manifest manifest
	if _, err := toml.DecodeFile(path, &manifest); err != nil {
		return manifest, err
	}
	var missing []string
	if strings.TrimSpace(manifest.Title) == "" {
		missing = append(missing, "title")
	}
	if strings.TrimSpace(manifest.Author) == "" {
		missing = append(missing, "author")
	}
	if strings.TrimSpace(manifest.Date) == "" {
		missing = append(missing, "date")
	}
	if strings.TrimSpace(manifest.Name) == "" {
		missing = append(missing, "name")
	}
	if strings.TrimSpace(manifest.CommandHelp) == "" {
		missing = append(missing, "command_help")
	}
	if len(manifest.Pages) == 0 {
		missing = append(missing, "pages")
	}
	if len(missing) > 0 {
		return manifest, fmt.Errorf("built-in docs manifest missing required fields: %s", strings.Join(missing, ", "))
	}
	return manifest, nil
}

func runPandoc(inputPath string, filterPath string, format string, outPath string) error {
	args := []string{
		"--from", "markdown+fenced_code_attributes",
		"--to", format,
		"--standalone",
		"--output", outPath,
		inputPath,
	}
	if strings.TrimSpace(filterPath) != "" {
		args = append(args[:4], append([]string{"--lua-filter", filterPath}, args[4:]...)...)
	}
	if format == "plain" {
		args = append([]string{"--columns", "100"}, args...)
	}

	cmd := exec.Command("pandoc", args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		detail := strings.TrimSpace(stderr.String())
		if detail == "" {
			return fmt.Errorf("pandoc %s: %w", format, err)
		}
		return fmt.Errorf("pandoc %s: %w: %s", format, err, detail)
	}
	return nil
}

func assembleMarkdown(sourceDir string, manifest manifest) ([]byte, error) {
	var out bytes.Buffer
	fmt.Fprintf(&out, "%% %s\n", manifest.Title)
	fmt.Fprintf(&out, "%% %s\n", manifest.Author)
	fmt.Fprintf(&out, "%% %s\n\n", manifest.Date)
	out.WriteString("# NAME\n\n")
	fmt.Fprintf(&out, "%s\n\n", manifest.Name)
	out.WriteString("# COMMAND HELP\n\n")
	fmt.Fprintf(&out, "%s\n\n", manifest.CommandHelp)
	for _, name := range manifest.Pages {
		path := filepath.Join(sourceDir, name)
		content, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		out.Write(content)
		out.WriteString("\n\n")
	}
	return out.Bytes(), nil
}
