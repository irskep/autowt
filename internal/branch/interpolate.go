package branch

import (
	"fmt"
	"strings"
)

// InterpolateArgs replaces $1, $2, ... placeholders in a template
// with the corresponding positional arguments. Arguments are not
// shell-quoted; the caller is responsible for safe usage.
func InterpolateArgs(template string, args []string) string {
	result := template
	for i, arg := range args {
		placeholder := fmt.Sprintf("$%d", i+1)
		result = strings.ReplaceAll(result, placeholder, arg)
	}
	return result
}
