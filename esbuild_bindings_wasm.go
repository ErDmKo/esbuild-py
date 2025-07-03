//go:build wasm

package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"

	"github.com/evanw/esbuild/pkg/api"
)

// IntermediateRequest is used to unmarshal the JSON from Python. We use this
// intermediate struct because the `Loader` field in `api.TransformOptions`
// is an enum, not a string, and requires manual mapping. This ensures the
// JSON API is consistent between the native and WASM backends.
type IntermediateRequest struct {
	Command string `json:"command"`
	Input   string `json:"input"`
	Options struct {
		Loader string `json:"loader"`
	} `json:"options"`
}

// Response defines the structure of the JSON response sent back to Python.
type Response struct {
	Code  string `json:"code"`
	Error string `json:"error,omitempty"`
}

// mapStringToLoader converts a string from Python into the corresponding
// esbuild api.Loader enum value.
func mapStringToLoader(loaderStr string) api.Loader {
	switch loaderStr {
	case "js":
		return api.LoaderJS
	case "jsx":
		return api.LoaderJSX
	case "ts":
		return api.LoaderTS
	case "tsx":
		return api.LoaderTSX
	case "css":
		return api.LoaderCSS
	case "json":
		return api.LoaderJSON
	case "text":
		return api.LoaderText
	case "base64":
		return api.LoaderBase64
	case "dataurl":
		return api.LoaderDataURL
	case "file":
		return api.LoaderFile
	case "binary":
		return api.LoaderBinary
	default:
		// Fallback to JS if an unknown loader is provided.
		// esbuild will likely error out, which is the desired behavior.
		return api.LoaderJS
	}
}

func main() {
	// Read all input from stdin. This will be the JSON payload.
	inputBytes, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading from stdin: %v\n", err)
		os.Exit(1)
	}

	// Unmarshal the JSON request into our intermediate struct.
	var req IntermediateRequest
	if err := json.Unmarshal(inputBytes, &req); err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing JSON request: %v\n", err)
		os.Exit(1)
	}

	var resp Response

	// Execute the requested command.
	switch req.Command {
	case "transform":
		// Manually construct the real esbuild options, mapping the string loader.
		realOptions := api.TransformOptions{
			Loader: mapStringToLoader(req.Options.Loader),
		}

		result := api.Transform(req.Input, realOptions)

		// Consolidate multiple errors into a single string.
		if len(result.Errors) > 0 {
			errorMsg := ""
			for _, e := range result.Errors {
				errorMsg += e.Text + " "
			}
			resp.Error = errorMsg
		}
		resp.Code = string(result.Code)

	default:
		resp.Error = fmt.Sprintf("Unknown command: '%s'", req.Command)
	}

	// Marshal the response struct into JSON.
	outputBytes, err := json.Marshal(resp)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling JSON response: %v\n", err)
		os.Exit(1)
	}

	// Print the final JSON response to stdout.
	fmt.Print(string(outputBytes))
}
