package versioncheck

import "testing"

func TestCompareVersions(t *testing.T) {
	tests := []struct {
		a, b string
		want int
	}{
		{"0.5.11", "0.5.11", 0},
		{"0.5.10", "0.5.11", -1},
		{"0.5.11", "0.5.10", 1},
		{"0.6.0", "0.5.11", 1},
		{"1.0.0", "0.9.99", 1},
		{"0.5.11", "0.6.0", -1},
		{"1.0", "1.0.0", 0},
		{"1.0.0", "1.0", 0},
	}

	for _, tt := range tests {
		t.Run(tt.a+"_vs_"+tt.b, func(t *testing.T) {
			got := compareVersions(tt.a, tt.b)
			if got != tt.want {
				t.Errorf("compareVersions(%q, %q) = %d, want %d", tt.a, tt.b, got, tt.want)
			}
		})
	}
}

func TestCheckDevVersion(t *testing.T) {
	// "dev" version should return nil (skip check).
	info := Check("dev", t.TempDir())
	if info != nil {
		t.Errorf("expected nil for dev version, got %+v", info)
	}
}
