package main

import "C"
import (
	"encoding/json"

	"github.com/evanw/esbuild/pkg/api"
)

// This file provides the Go bindings for the esbuild API that are called from
// Python using ctypes.

// IntermediateRequest is used to unmarshal the JSON from Python. We use this
// intermediate struct because the `Loader` field in `api.TransformOptions`
// is an enum, not a string, and requires manual mapping.
type IntermediateRequest struct {
	Code    string `json:"code"`
	Options struct {
		Loader string `json:"loader"`
	} `json:"options"`
}

// Response defines the structure of the JSON response sent back to Python.
type Response struct {
	Code   string        `json:"code"`
	Errors []api.Message `json:"errors"`
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
	// 1. Unmarshal the request from Python into our intermediate struct.
	goRequestJSON := C.GoString(requestJSON)
	var req IntermediateRequest
	if err := json.Unmarshal([]byte(goRequestJSON), &req); err != nil {
		errResponse := Response{
			Errors: []api.Message{{Text: "Failed to parse request JSON: " + err.Error()}},
		}
		responseBytes, _ := json.Marshal(errResponse)
		return C.CString(string(responseBytes))
	}

	// 2. Manually construct the real esbuild options, mapping the string loader.
	realOptions := api.TransformOptions{
		Loader: mapStringToLoader(req.Options.Loader),
	}

	// 3. Call the actual esbuild Transform API.
	result := api.Transform(req.Code, realOptions)

	// 4. Create the response object to send back to Python.
	response := Response{
		Errors: result.Errors,
	}
	if len(result.Errors) == 0 {
		response.Code = string(result.Code)
	}

	// 5. Marshal the response to JSON.
	responseBytes, err := json.Marshal(response)
	if err != nil {
		// This is an internal error, but we still try to return it as a JSON error.
		errResponse := Response{
			Errors: []api.Message{{Text: "Failed to marshal response JSON: " + err.Error()}},
		}
		responseBytes, _ = json.Marshal(errResponse)
		return C.CString(string(responseBytes))
	}

	// 6. Convert Go string back to C string and return.
	// The memory for this string must be freed by the Python caller.
	return C.CString(string(responseBytes))
}

// main is required for the 'go build' command, but it's not used
// when building a shared library.
func main() {}
