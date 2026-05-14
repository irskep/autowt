package config

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
		GlobalConfigFile: dir + "/config.toml",
	}
}

// Load reads configuration with cascading precedence:
// defaults -> global file -> project file -> env vars -> CLI overrides.
func (l *Loader) Load(projectDir string, cliOverrides map[string]any) (Config, error) {
	// TODO: implement cascading load
	return DefaultConfig(), nil
}
