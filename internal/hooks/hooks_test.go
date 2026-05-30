package hooks

import (
	"testing"

	"github.com/irskep/autowt/internal/model"
)

func TestMergeForCustomScriptDoesNotAliasInputs(t *testing.T) {
	global := make([]string, 1, 3)
	global[0] = "global"
	project := []string{"project"}
	cs := &model.CustomScript{
		InheritHooks: true,
		PreCreate:    "custom",
	}

	merged := MergeForCustomScript(global, project, cs, PreCreate)
	merged[0] = "changed"

	if global[0] != "global" {
		t.Fatalf("global input mutated to %q", global[0])
	}
	if project[0] != "project" {
		t.Fatalf("project input mutated to %q", project[0])
	}
}
