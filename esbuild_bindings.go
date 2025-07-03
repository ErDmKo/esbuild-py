package main

import (
	"C"
	"encoding/json"

	"github.com/evanw/esbuild/pkg/api"
	"github.com/keller-mark/esbuild-py/internal/shared"
)

// This file provides the Go bindings for the esbuild API that are called from
// Python using ctypes.

// --- Transform-specific Structures ---

// TransformRequest is used to unmarshal the JSON from Python for the transform API.
// We use this intermediate struct because the `Loader` field in `api.TransformOptions`
// is an enum, not a string, and requires manual mapping.
type TransformRequest struct {
	Code    string `json:"code"`
	Options struct {
		Loader string `json:"loader"`
	} `json:"options"`
}

//export transform
func transform(requestJSON *C.char) *C.char {
	goRequestJSON := C.GoString(requestJSON)
	var req TransformRequest
	if err := json.Unmarshal([]byte(goRequestJSON), &req); err != nil {
		// On failure, create a response with the parsing error.
		response := shared.NewApiResponse("", []api.Message{{Text: "Failed to parse request JSON: " + err.Error()}}, nil)
		responseBytes, _ := json.Marshal(response)
		return C.CString(string(responseBytes))
	}

	realOptions := api.TransformOptions{
		Loader: shared.MapStringToLoader(req.Options.Loader),
	}

	result := api.Transform(req.Code, realOptions)

	// Use the shared constructor to create a well-formed response.
	response := shared.NewApiResponse(string(result.Code), result.Errors, result.Warnings)

	responseBytes, err := json.Marshal(response)
	if err != nil {
		// This is an internal error, but we still try to return it as a JSON error.
		errResponse := shared.NewApiResponse("", []api.Message{{Text: "Failed to marshal response JSON: " + err.Error()}}, nil)
		responseBytes, _ = json.Marshal(errResponse)
		return C.CString(string(responseBytes))
	}

	return C.CString(string(responseBytes))
}

//export build
// build is the C-exported function that wraps esbuild's Build API.
func build(requestJSON *C.char) *C.char {
	goRequestJSON := C.GoString(requestJSON)
	var options api.BuildOptions
	if err := json.Unmarshal([]byte(goRequestJSON), &options); err != nil {
		response := shared.NewApiResponse("", []api.Message{{Text: "Failed to parse build request JSON: " + err.Error()}}, nil)
		responseBytes, _ := json.Marshal(response)
		return C.CString(string(responseBytes))
	}

	// For build, esbuild defaults to bundling if an outfile is specified.
	// We will explicitly set it to true to be clear and consistent.
	options.Bundle = true
	options.Write = true

	result := api.Build(options)

	// Use the shared constructor. The code is empty as it's written to a file.
	response := shared.NewApiResponse("", result.Errors, result.Warnings)

	responseBytes, err := json.Marshal(response)
	if err != nil {
		errResponse := shared.NewApiResponse("", []api.Message{{Text: "Failed to marshal build response JSON: " + err.Error()}}, nil)
		responseBytes, _ = json.Marshal(errResponse)
		return C.CString(string(responseBytes))
	}

	return C.CString(string(responseBytes))
}

// main is required for the 'go build' command, but it's not used
// when building a shared library.
func main() {}
