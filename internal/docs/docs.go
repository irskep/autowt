package docs

import _ "embed"

//go:embed generated/autowt.1
var manPage string

//go:embed generated/autowt.txt
var plainText string

func ManPage() string {
	return manPage
}

func PlainText() string {
	return plainText
}
