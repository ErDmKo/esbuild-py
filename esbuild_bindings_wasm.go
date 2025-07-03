//go:build wasm

package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"github.com/evanw/esbuild/pkg/api"

	"github.com/keller-mark/esbuild-py/internal/shared"
)

// IntermediateRequest is used to unmarshal the JSON from Python. We use this
// intermediate struct because the `Loader` field in `api.TransformOptions`
// is an enum, not a string, and requires manual mapping. This ensures the
// JSON API is consistent between the native and WASM backends.
type IntermediateRequest struct {
	Command string `json:"command"`
	Input   string `json:"input"`
	BuildOptions struct {
		EntryPoints []string
		Outfile string
	}
	TransformOptions struct {
		Loader string `json:"loader"`
	} `json:"options"`
}

// Response defines the structure of the JSON response sent back to Python.
type Response struct {
	Code  string `json:"code"`
	Error string `json:"error,omitempty"`
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
	case "build":
		options := api.BuildOptions{
			Bundle: true,
			Write: true,
			Outfile: req.BuildOptions.Outfile,
			EntryPoints: req.BuildOptions.EntryPoints,
		}
		result := api.Build(options)

		// Use the shared constructor. The code is empty as it's written to a file.
		response := shared.NewApiResponse("", result.Errors, result.Warnings)

		responseBytes, err := json.Marshal(response)
		if err != nil {
			errResponse := shared.NewApiResponse("", []api.Message{{Text: "Failed to marshal build response JSON: " + err.Error()}}, nil)
			responseBytes, err = json.Marshal(errResponse)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error marshaling JSON response: %v\n", err)
				os.Exit(1)
			}
			fmt.Print(string(responseBytes))
		} else {
			fmt.Print(string(responseBytes))
			os.Exit(0)
		}
	case "transform":
		// Manually construct the real esbuild options, mapping the string loader.
		realOptions := api.TransformOptions{
			Loader: shared.MapStringToLoader(req.TransformOptions.Loader),
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
