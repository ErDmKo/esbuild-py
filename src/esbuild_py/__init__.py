import logging

# Public API
__all__ = ["transform", "BACKEND", "__version__"]

# The version of the esbuild-py package.
__version__ = "0.2.0"

# The backend implementation to use.
# - "native": The native binary extension.
# - "wasm": The WebAssembly fallback.
# - "none": No backend available.
BACKEND = "none"
_backend_instance = None

log = logging.getLogger(__name__)

# --- Backend Initialization ---
# This section determines which backend (native or WASM) to use.

# 1. Try to import the native C-extension backend first.
try:
    from ._native_backend import NativeBackend
    _backend_instance = NativeBackend()
    BACKEND = "native"

except (ImportError, FileNotFoundError):
    # 2. If the native backend fails, fall back to the WASM implementation.
    log.warning("esbuild-py: Native backend failed to load, attempting WASM fallback.")
    try:
        from ._wasm_backend import WasmBackend
        _backend_instance = WasmBackend()
        BACKEND = "wasm"

    except (ImportError, FileNotFoundError) as e:
        # This catches errors if 'wasmtime' is not installed or if 'esbuild.wasm' is missing.
        log.error(f"esbuild-py: Failed to initialize WASM fallback: {e}")
        _backend_instance = None
        BACKEND = "none"


def transform(code: str, **kwargs):
    """
    Transforms the given source code using esbuild.

    This function acts as a proxy, delegating the call to the active
    backend (either native or WASM).

    Args:
        code: The source code to transform (e.g., TypeScript, JSX).
        **kwargs: Options to pass to esbuild, e.g., loader='tsx', minify=True.

    Returns:
        The transformed code as a string.

    Raises:
        RuntimeError: If no backend could be initialized.
    """
    if _backend_instance is None:
        raise RuntimeError(
            "Neither the native nor the WASM esbuild backend could be initialized. "
            "This is likely due to a failed installation or a missing dependency. \n"
            "Please try reinstalling the package. If the problem persists, please open an issue at: \n"
            "https://github.com/esbuild-kit/esbuild-py/issues"
        )

    # Delegate the call to the active backend's transform method.
    return _backend_instance.transform(code, **kwargs)


def build(**kwargs) -> dict:
    """
    Builds, bundles, and optionally minifies one or more entry points using
    the active esbuild backend.

    This is the primary public API for bundling files. It automatically
    selects the best available backend (native or WASM) and delegates the
    call to it.

    Args:
        **kwargs: esbuild build options, such as `entry_points`, `outfile`,
                  `bundle`, `minify`, etc.

    Returns:
        A dictionary containing 'errors' and 'warnings' lists.

    Raises:
        RuntimeError: If the build fails or if no backend is available.
    """
    if _backend_instance is None:
        raise RuntimeError(
            "No esbuild backend is available. The native library may be missing "
            "or the WASM fallback failed."
        )
    return _backend_instance.build(**kwargs)
