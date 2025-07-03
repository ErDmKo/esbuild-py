#!/bin/bash

# This script compiles the Go entrypoint into a WebAssembly (WASM) module
# that communicates over stdin/stdout. It uses the standard Go compiler.
#
# It's designed to be run from the root of the project.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# The source file is the Go program with the main function that handles stdin/stdout.
SOURCE_FILE="esbuild_bindings_wasm.go"
OUTPUT_PATH="src/esbuild_py/precompiled/esbuild.wasm"

# --- Build Process ---
echo "Building esbuild WASM CLI with standard Go compiler..."
echo "Source: $SOURCE_FILE"
echo "Destination: $OUTPUT_PATH"

# 1. Create the destination directory if it doesn't exist.
mkdir -p "$(dirname "$OUTPUT_PATH")"

# 2. Compile the Go code to WASM.
# GOOS=wasip1 and GOARCH=wasm are required for WASI compliance,
# which allows the WASM module to access system resources like stdin/stdout.
# The output is a single .wasm file that can be executed by a WASM runtime.
GOOS=wasip1 GOARCH=wasm go build -o "$OUTPUT_PATH" "$SOURCE_FILE"

# 3. Print a success message.
echo "✅ WASM module built successfully."
