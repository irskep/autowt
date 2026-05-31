package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/irskep/autowt/internal/cli"
	"github.com/irskep/autowt/internal/docsgen"
)

func main() {
	cliOutDir := flag.String("cli-out", "docs/cli", "directory for generated CLI markdown")
	bundleOutDir := flag.String("bundle-out", "internal/docs/generated", "directory for bundled terminal docs")
	sourceDir := flag.String("source", "docs", "directory containing narrative documentation")
	manifestPath := flag.String("manifest", "docs/builtin.toml", "built-in documentation manifest")
	filterPath := flag.String("filter", "", "optional Pandoc Lua filter")
	flag.Parse()

	if err := cli.GenerateMarkdownDocs(*cliOutDir); err != nil {
		fmt.Fprintf(os.Stderr, "autowt-docs: %v\n", err)
		os.Exit(1)
	}
	if err := docsgen.Generate(docsgen.Options{
		SourceDir:    *sourceDir,
		ManifestPath: *manifestPath,
		OutDir:       *bundleOutDir,
		FilterPath:   *filterPath,
	}); err != nil {
		fmt.Fprintf(os.Stderr, "autowt-docs: %v\n", err)
		os.Exit(1)
	}
}
