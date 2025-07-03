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

//export transform
// transform is the C-exported function that wraps esbuild's Transform API.
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
		Loader: mapStringToLoader(req.Options.Loader),
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
