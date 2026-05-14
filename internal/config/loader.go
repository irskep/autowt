package config

import (
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"

	"github.com/BurntSushi/toml"
	"github.com/irskep/autowt/internal/model"
)

// Loader handles loading and merging configuration from multiple sources.
type Loader struct {
	AppDir           string
	GlobalConfigFile string
}

// NewLoader creates a Loader with the default OS-specific config directory.
func NewLoader() *Loader {
	dir := DefaultConfigDir()
	return &Loader{
		AppDir:           dir,
		GlobalConfigFile: filepath.Join(dir, "config.toml"),
	}
}

// Load reads configuration with cascading precedence:
// defaults -> global file -> project file -> env vars -> CLI overrides.
func (l *Loader) Load(projectDir string, cliOverrides map[string]any) (Config, error) {
	cfg := DefaultConfig()

	// Global config.
	if tf, md, err := l.loadTOMLFile(l.GlobalConfigFile); err == nil {
		applyTOMLFile(&cfg, tf, md)
	} else if !os.IsNotExist(err) {
		slog.Warn("Failed to load global config", "path", l.GlobalConfigFile, "error", err)
	}

	// Project config.
	if projectDir != "" {
		for _, name := range []string{"autowt.toml", ".autowt.toml"} {
			path := filepath.Join(projectDir, name)
			if tf, md, err := l.loadTOMLFile(path); err == nil {
				applyTOMLFile(&cfg, tf, md)
				break
			}
		}
	}

	// Environment variables.
	applyEnvVars(&cfg)

	// CLI overrides.
	if cliOverrides != nil {
		applyCLIOverrides(&cfg, cliOverrides)
	}

	return cfg, nil
}

// LoadGlobalOnly loads only the global config (no project, env, or CLI overrides).
func (l *Loader) LoadGlobalOnly() (Config, error) {
	cfg := DefaultConfig()
	if tf, md, err := l.loadTOMLFile(l.GlobalConfigFile); err == nil {
		applyTOMLFile(&cfg, tf, md)
	} else if !os.IsNotExist(err) {
		slog.Warn("Failed to load global config", "path", l.GlobalConfigFile, "error", err)
	}
	return cfg, nil
}

// LoadProjectHookConfig loads only the project hook definitions.
func (l *Loader) LoadProjectHookConfig(projectDir string) HookConfig {
	for _, name := range []string{"autowt.toml", ".autowt.toml"} {
		path := filepath.Join(projectDir, name)
		if tf, _, err := l.loadTOMLFile(path); err == nil {
			return hookConfigFromTOMLFile(tf)
		}
	}
	return HookConfig{}
}

// LoadGlobalHookConfig loads only the global hook definitions.
func (l *Loader) LoadGlobalHookConfig() HookConfig {
	if tf, _, err := l.loadTOMLFile(l.GlobalConfigFile); err == nil {
		return hookConfigFromTOMLFile(tf)
	}
	return HookConfig{}
}

// HasUserConfiguredCleanupMode checks if the user has set a cleanup mode.
func (l *Loader) HasUserConfiguredCleanupMode() bool {
	tf, _, err := l.loadTOMLFile(l.GlobalConfigFile)
	if err != nil {
		return false
	}
	return tf.Cleanup.DefaultMode != ""
}

// SaveCleanupMode updates only the cleanup.default_mode in the global config.
func (l *Loader) SaveCleanupMode(mode model.CleanupMode) error {
	if err := os.MkdirAll(l.AppDir, 0o755); err != nil {
		return err
	}

	existing := make(map[string]any)
	if _, err := toml.DecodeFile(l.GlobalConfigFile, &existing); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("cannot save cleanup mode: failed to parse existing config at %s: %w", l.GlobalConfigFile, err)
	}

	cleanup, ok := existing["cleanup"].(map[string]any)
	if !ok {
		cleanup = make(map[string]any)
		existing["cleanup"] = cleanup
	}
	cleanup["default_mode"] = string(mode)

	return l.writeTOML(l.GlobalConfigFile, existing)
}

// SaveConfig writes the full config to the global config file.
func (l *Loader) SaveConfig(cfg Config) error {
	if err := os.MkdirAll(l.AppDir, 0o755); err != nil {
		return err
	}

	// Validate existing file is parseable before overwriting.
	if _, err := os.Stat(l.GlobalConfigFile); err == nil {
		var check map[string]any
		if _, err := toml.DecodeFile(l.GlobalConfigFile, &check); err != nil {
			return fmt.Errorf("cannot save config: existing file at %s has invalid TOML: %w", l.GlobalConfigFile, err)
		}
	}

	data := configToTOML(cfg)
	return l.writeTOML(l.GlobalConfigFile, data)
}

func (l *Loader) loadTOMLFile(path string) (tomlFile, toml.MetaData, error) {
	var tf tomlFile
	md, err := toml.DecodeFile(path, &tf)
	return tf, md, err
}

func (l *Loader) writeTOML(path string, data map[string]any) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()
	return toml.NewEncoder(f).Encode(data)
}

// tomlFile mirrors the TOML file structure for typed decoding.
type tomlFile struct {
	Terminal      tomlTerminal      `toml:"terminal"`
	Worktree      tomlWorktree      `toml:"worktree"`
	Cleanup       tomlCleanup       `toml:"cleanup"`
	Scripts       tomlScripts       `toml:"scripts"`
	Confirmations tomlConfirmations `toml:"confirmations"`
}

type tomlTerminal struct {
	Mode      string `toml:"mode"`
	AlwaysNew *bool  `toml:"always_new"`
	Program   string `toml:"program"`
}

type tomlWorktree struct {
	DirectoryPattern string `toml:"directory_pattern"`
	AutoFetch        *bool  `toml:"auto_fetch"`
	BranchPrefix     string `toml:"branch_prefix"`
}

type tomlCleanup struct {
	DefaultMode string `toml:"default_mode"`
}

type tomlScripts struct {
	Init            string                      `toml:"init"` // deprecated
	SessionInit     string                      `toml:"session_init"`
	PreCreate       string                      `toml:"pre_create"`
	PostCreate      string                      `toml:"post_create"`
	PostCreateAsync string                      `toml:"post_create_async"`
	PreCleanup      string                      `toml:"pre_cleanup"`
	PostCleanup     string                      `toml:"post_cleanup"`
	PreSwitch       string                      `toml:"pre_switch"`
	PostSwitch      string                      `toml:"post_switch"`
	Custom          map[string]toml.Primitive   `toml:"custom"`
}

type tomlCustomScript struct {
	Description     string `toml:"description"`
	BranchName      string `toml:"branch_name"`
	InheritHooks    *bool  `toml:"inherit_hooks"`
	SessionInit     string `toml:"session_init"`
	PreCreate       string `toml:"pre_create"`
	PostCreate      string `toml:"post_create"`
	PostCreateAsync string `toml:"post_create_async"`
	PreCleanup      string `toml:"pre_cleanup"`
	PostCleanup     string `toml:"post_cleanup"`
	PreSwitch       string `toml:"pre_switch"`
	PostSwitch      string `toml:"post_switch"`
}

type tomlConfirmations struct {
	CleanupMultiple *bool `toml:"cleanup_multiple"`
	ForceOperations *bool `toml:"force_operations"`
}

// applyTOMLFile merges a decoded TOML file onto an existing config.
func applyTOMLFile(cfg *Config, tf tomlFile, md toml.MetaData) {
	if tf.Terminal.Mode != "" {
		cfg.Terminal.Mode = model.TerminalMode(tf.Terminal.Mode)
	}
	if tf.Terminal.AlwaysNew != nil {
		cfg.Terminal.AlwaysNew = *tf.Terminal.AlwaysNew
	}
	if tf.Terminal.Program != "" {
		cfg.Terminal.Program = tf.Terminal.Program
	}

	if tf.Worktree.DirectoryPattern != "" {
		cfg.Worktree.DirectoryPattern = tf.Worktree.DirectoryPattern
	}
	if tf.Worktree.AutoFetch != nil {
		cfg.Worktree.AutoFetch = *tf.Worktree.AutoFetch
	}
	if tf.Worktree.BranchPrefix != "" {
		cfg.Worktree.BranchPrefix = tf.Worktree.BranchPrefix
	}

	if tf.Cleanup.DefaultMode != "" {
		cfg.Cleanup.DefaultMode = model.CleanupMode(tf.Cleanup.DefaultMode)
	}

	// Handle init -> session_init backward compatibility.
	if tf.Scripts.SessionInit != "" {
		cfg.Scripts.SessionInit = tf.Scripts.SessionInit
	} else if tf.Scripts.Init != "" {
		slog.Warn("The 'init' script key is deprecated; rename to 'session_init'")
		cfg.Scripts.SessionInit = tf.Scripts.Init
	}
	if tf.Scripts.PreCreate != "" {
		cfg.Scripts.PreCreate = tf.Scripts.PreCreate
	}
	if tf.Scripts.PostCreate != "" {
		cfg.Scripts.PostCreate = tf.Scripts.PostCreate
	}
	if tf.Scripts.PostCreateAsync != "" {
		cfg.Scripts.PostCreateAsync = tf.Scripts.PostCreateAsync
	}
	if tf.Scripts.PreCleanup != "" {
		cfg.Scripts.PreCleanup = tf.Scripts.PreCleanup
	}
	if tf.Scripts.PostCleanup != "" {
		cfg.Scripts.PostCleanup = tf.Scripts.PostCleanup
	}
	if tf.Scripts.PreSwitch != "" {
		cfg.Scripts.PreSwitch = tf.Scripts.PreSwitch
	}
	if tf.Scripts.PostSwitch != "" {
		cfg.Scripts.PostSwitch = tf.Scripts.PostSwitch
	}

	for name, prim := range tf.Scripts.Custom {
		// Try as a string first (simple format).
		var s string
		if err := md.PrimitiveDecode(prim, &s); err == nil {
			cfg.Scripts.Custom[name] = model.CustomScript{InheritHooks: true, SessionInit: s}
			continue
		}
		// Full table format.
		var tcs tomlCustomScript
		if err := md.PrimitiveDecode(prim, &tcs); err == nil {
			cs := model.CustomScript{
				InheritHooks:    true,
				Description:     tcs.Description,
				BranchName:      tcs.BranchName,
				SessionInit:     tcs.SessionInit,
				PreCreate:       tcs.PreCreate,
				PostCreate:      tcs.PostCreate,
				PostCreateAsync: tcs.PostCreateAsync,
				PreCleanup:      tcs.PreCleanup,
				PostCleanup:     tcs.PostCleanup,
				PreSwitch:       tcs.PreSwitch,
				PostSwitch:      tcs.PostSwitch,
			}
			if tcs.InheritHooks != nil {
				cs.InheritHooks = *tcs.InheritHooks
			}
			cfg.Scripts.Custom[name] = cs
		}
	}

	if tf.Confirmations.CleanupMultiple != nil {
		cfg.Confirmations.CleanupMultiple = *tf.Confirmations.CleanupMultiple
	}
	if tf.Confirmations.ForceOperations != nil {
		cfg.Confirmations.ForceOperations = *tf.Confirmations.ForceOperations
	}
}

func hookConfigFromTOMLFile(tf tomlFile) HookConfig {
	hc := HookConfig{}
	if tf.Scripts.SessionInit != "" {
		hc.SessionInit = tf.Scripts.SessionInit
	} else if tf.Scripts.Init != "" {
		hc.SessionInit = tf.Scripts.Init
	}
	hc.PreCreate = tf.Scripts.PreCreate
	hc.PostCreate = tf.Scripts.PostCreate
	hc.PostCreateAsync = tf.Scripts.PostCreateAsync
	hc.PreCleanup = tf.Scripts.PreCleanup
	hc.PostCleanup = tf.Scripts.PostCleanup
	hc.PreSwitch = tf.Scripts.PreSwitch
	hc.PostSwitch = tf.Scripts.PostSwitch
	return hc
}

// applyEnvVars reads AUTOWT_* environment variables and applies them.
func applyEnvVars(cfg *Config) {
	envMap := map[string]func(string){
		"AUTOWT_TERMINAL_MODE":                    func(v string) { cfg.Terminal.Mode = model.TerminalMode(v) },
		"AUTOWT_TERMINAL_ALWAYS_NEW":              func(v string) { cfg.Terminal.AlwaysNew = parseBool(v) },
		"AUTOWT_TERMINAL_PROGRAM":                 func(v string) { cfg.Terminal.Program = v },
		"AUTOWT_WORKTREE_DIRECTORY_PATTERN":       func(v string) { cfg.Worktree.DirectoryPattern = v },
		"AUTOWT_WORKTREE_AUTO_FETCH":              func(v string) { cfg.Worktree.AutoFetch = parseBool(v) },
		"AUTOWT_WORKTREE_BRANCH_PREFIX":           func(v string) { cfg.Worktree.BranchPrefix = v },
		"AUTOWT_CLEANUP_DEFAULT_MODE":             func(v string) { cfg.Cleanup.DefaultMode = model.CleanupMode(v) },
		"AUTOWT_SCRIPTS_SESSION_INIT":             func(v string) { cfg.Scripts.SessionInit = v },
		"AUTOWT_SCRIPTS_PRE_CREATE":               func(v string) { cfg.Scripts.PreCreate = v },
		"AUTOWT_SCRIPTS_POST_CREATE":              func(v string) { cfg.Scripts.PostCreate = v },
		"AUTOWT_SCRIPTS_POST_CREATE_ASYNC":        func(v string) { cfg.Scripts.PostCreateAsync = v },
		"AUTOWT_SCRIPTS_PRE_CLEANUP":              func(v string) { cfg.Scripts.PreCleanup = v },
		"AUTOWT_SCRIPTS_POST_CLEANUP":             func(v string) { cfg.Scripts.PostCleanup = v },
		"AUTOWT_SCRIPTS_PRE_SWITCH":               func(v string) { cfg.Scripts.PreSwitch = v },
		"AUTOWT_SCRIPTS_POST_SWITCH":              func(v string) { cfg.Scripts.PostSwitch = v },
		"AUTOWT_CONFIRMATIONS_CLEANUP_MULTIPLE":   func(v string) { cfg.Confirmations.CleanupMultiple = parseBool(v) },
		"AUTOWT_CONFIRMATIONS_FORCE_OPERATIONS":   func(v string) { cfg.Confirmations.ForceOperations = parseBool(v) },
	}

	for key, apply := range envMap {
		if val := os.Getenv(key); val != "" {
			apply(val)
		}
	}
}

func parseBool(s string) bool {
	switch strings.ToLower(s) {
	case "true", "yes", "1", "on":
		return true
	default:
		return false
	}
}

func applyCLIOverrides(cfg *Config, overrides map[string]any) {
	if v, ok := overrides["terminal_mode"].(string); ok && v != "" {
		cfg.Terminal.Mode = model.TerminalMode(v)
	}
	if v, ok := overrides["cleanup_mode"].(string); ok && v != "" {
		cfg.Cleanup.DefaultMode = model.CleanupMode(v)
	}
	if v, ok := overrides["after_init"].(string); ok && v != "" {
		cfg.Scripts.SessionInit = v
	}
}

func configToTOML(cfg Config) map[string]any {
	data := map[string]any{
		"terminal": map[string]any{
			"mode":       string(cfg.Terminal.Mode),
			"always_new": cfg.Terminal.AlwaysNew,
		},
		"worktree": map[string]any{
			"directory_pattern": cfg.Worktree.DirectoryPattern,
			"auto_fetch":       cfg.Worktree.AutoFetch,
		},
		"cleanup": map[string]any{
			"default_mode": string(cfg.Cleanup.DefaultMode),
		},
	}

	if cfg.Terminal.Program != "" {
		data["terminal"].(map[string]any)["program"] = cfg.Terminal.Program
	}
	if cfg.Worktree.BranchPrefix != "" {
		data["worktree"].(map[string]any)["branch_prefix"] = cfg.Worktree.BranchPrefix
	}

	return data
}
