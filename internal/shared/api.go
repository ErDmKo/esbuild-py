package shared

import "github.com/evanw/esbuild/pkg/api"

// ApiResponse defines the universal response structure for all API calls.
// It's designed to be safely serialized to JSON, ensuring that slices are
// never null.
type ApiResponse struct {
	Code     string        `json:"code,omitempty"`
	Errors   []api.Message `json:"errors"`
	Warnings []api.Message `json:"warnings"`
}

// NewApiResponse is a factory function that creates a well-formed ApiResponse
// from the results of an esbuild API call.
// It guarantees that the Errors and Warnings slices are never nil, which
// prevents them from being serialized to `null` in JSON.
func NewApiResponse(code string, errors []api.Message, warnings []api.Message) *ApiResponse {
	resp := &ApiResponse{
		Code:     code,
		Errors:   errors,
		Warnings: warnings,
	}

	// Ensure we always return an empty slice `[]` instead of `null` for JSON.
	if resp.Errors == nil {
		resp.Errors = make([]api.Message, 0)
	}
	if resp.Warnings == nil {
		resp.Warnings = make([]api.Message, 0)
	}

	return resp
}

func MapStringToLoader(loaderStr string) api.Loader {
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
