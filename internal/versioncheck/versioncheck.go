// Package versioncheck checks GitHub Releases for newer versions of autowt.
package versioncheck

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/BurntSushi/toml"
)

const (
	releaseURL   = "https://api.github.com/repos/irskep/autowt/releases/latest"
	releasesPage = "https://github.com/irskep/autowt/releases"
	checkInterval = 1 * time.Hour
	httpTimeout   = 5 * time.Second
)

// Info holds version check results.
type Info struct {
	Current   string
	Latest    string
	Available bool
}

// Check compares the running version against the latest GitHub release.
// Returns nil if no update is available or the check was skipped (rate limit).
// Errors are swallowed — version checking should never break the CLI.
func Check(currentVersion, stateDir string) *Info {
	if currentVersion == "dev" || currentVersion == "" {
		return nil
	}

	stateFile := filepath.Join(stateDir, "version_check.toml")

	// Rate limit: skip if checked recently.
	if cachedInfo, ok := readCache(stateFile); ok {
		if time.Since(cachedInfo.CheckedAt) < checkInterval {
			if cachedInfo.Latest != "" && compareVersions(currentVersion, cachedInfo.Latest) < 0 {
				return &Info{Current: currentVersion, Latest: cachedInfo.Latest, Available: true}
			}
			return nil
		}
	}

	latest, err := fetchLatestVersion()
	if err != nil {
		return nil
	}

	// Save the check time.
	writeCache(stateFile, latest)

	if compareVersions(currentVersion, latest) < 0 {
		return &Info{Current: currentVersion, Latest: latest, Available: true}
	}
	return nil
}

// Print prints the update notification to stderr if info is non-nil.
func Print(info *Info) {
	if info == nil || !info.Available {
		return
	}
	fmt.Fprintf(os.Stderr, "Update available: autowt %s (you have %s)\n", info.Latest, info.Current)
	fmt.Fprintf(os.Stderr, "   Run: go install github.com/irskep/autowt@v%s\n", info.Latest)
	fmt.Fprintf(os.Stderr, "   Release notes: %s\n", releasesPage)
	fmt.Fprintln(os.Stderr)
}

type releaseResponse struct {
	TagName    string `json:"tag_name"`
	Prerelease bool   `json:"prerelease"`
	Draft      bool   `json:"draft"`
}

func fetchLatestVersion() (string, error) {
	client := &http.Client{Timeout: httpTimeout}
	resp, err := client.Get(releaseURL)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return "", fmt.Errorf("GitHub API returned %d", resp.StatusCode)
	}

	var release releaseResponse
	if err := json.NewDecoder(resp.Body).Decode(&release); err != nil {
		return "", err
	}

	return strings.TrimPrefix(release.TagName, "v"), nil
}

type cacheState struct {
	Latest    string    `toml:"latest"`
	CheckedAt time.Time `toml:"checked_at"`
}

func readCache(path string) (cacheState, bool) {
	var state cacheState
	if _, err := toml.DecodeFile(path, &state); err != nil {
		return state, false
	}
	return state, true
}

func writeCache(path, latest string) {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	state := cacheState{Latest: latest, CheckedAt: time.Now()}
	f, err := os.Create(path)
	if err != nil {
		return
	}
	defer f.Close()
	_ = toml.NewEncoder(f).Encode(state)
}

// compareVersions compares two semver-ish strings (without the "v" prefix).
// Returns -1 if a < b, 0 if equal, 1 if a > b.
func compareVersions(a, b string) int {
	aParts := strings.Split(a, ".")
	bParts := strings.Split(b, ".")

	for i := 0; i < len(aParts) || i < len(bParts); i++ {
		var aNum, bNum int
		if i < len(aParts) {
			aNum = parseVersionPart(aParts[i])
		}
		if i < len(bParts) {
			bNum = parseVersionPart(bParts[i])
		}
		if aNum < bNum {
			return -1
		}
		if aNum > bNum {
			return 1
		}
	}
	return 0
}

func parseVersionPart(s string) int {
	n := 0
	for _, c := range s {
		if c >= '0' && c <= '9' {
			n = n*10 + int(c-'0')
		} else {
			break
		}
	}
	return n
}
