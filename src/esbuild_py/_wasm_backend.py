import importlib.resources
import wasmtime
import json
import logging
import os
import tempfile

log = logging.getLogger(__name__)

class WasmBackend:
    """
    A class that encapsulates all the logic for interacting with the
    precompiled esbuild.wasm module using a stdin/stdout communication model,
    facilitated by temporary files for compatibility.
    """
    def __init__(self):
        """
        Initializes the WASM runtime by loading and compiling the module.
        The actual instance is created on-the-fly for each call.
        """
        self.engine = wasmtime.Engine()
        self.module = self._load_wasm_module()
        log.debug("WASM module loaded and compiled successfully.")

    def _load_wasm_module(self):
        """
        Safely accesses the precompiled .wasm file included in the package
        and compiles it into a wasmtime.Module.
        """
        try:
            log.debug("Attempting to load WASM from 'esbuild_py.precompiled'.")
            # Modern approach for Python 3.9+
            wasm_bytes = importlib.resources.files("esbuild_py.precompiled").joinpath("esbuild.wasm").read_bytes()
        except (FileNotFoundError, AttributeError, ModuleNotFoundError):
            # Fallback for older Python versions or different packaging setups
            log.debug("importlib.resources failed, falling back to pkgutil.")
            import pkgutil
            wasm_bytes = pkgutil.get_data("esbuild_py", "precompiled/esbuild.wasm")
            if wasm_bytes is None:
                raise FileNotFoundError("Could not find the precompiled esbuild.wasm file.")

        log.debug(f"Successfully loaded {len(wasm_bytes)} bytes of WASM code.")
        return wasmtime.Module(self.engine, wasm_bytes)

    def transform(self, code: str, **kwargs):
        """
        The main API method for this backend. It transforms the given code
        by running the WASM module as a sandboxed CLI tool, using temporary
        files for I/O.
        """
        # 1. Prepare the JSON request payload.
        options = kwargs.copy()
        if 'loader' not in options:
            options['loader'] = 'jsx'

        request_payload = {
            "command": "transform",
            "input": code,
            "options": options,
        }
        request_json_bytes = json.dumps(request_payload).encode('utf-8')

        # 2. Create temporary files for stdin and stdout.
        # We use NamedTemporaryFile to get a file path that we can pass to wasmtime.
        # We must ensure these files are cleaned up properly.
        stdin_file = tempfile.NamedTemporaryFile(delete=False)
        stdout_file = tempfile.NamedTemporaryFile(delete=False)

        try:
            # Write the request to the stdin file.
            stdin_file.write(request_json_bytes)
            stdin_file.close() # Close it so the WASM process can read it.

            # 3. Configure WASI to use our temporary files.
            wasi_config = wasmtime.WasiConfig()
            wasi_config.stdin_file = stdin_file.name
            wasi_config.stdout_file = stdout_file.name
            wasi_config.stderr_file = stdout_file.name # Redirect stderr to stdout file for easier debugging.

            # 4. Instantiate and run the WASM module.
            store = wasmtime.Store(self.engine)
            store.set_wasi(wasi_config)
            linker = wasmtime.Linker(self.engine)
            linker.define_wasi()
            instance = linker.instantiate(store, self.module)

            start_func = instance.exports(store)["_start"]
            try:
                start_func(store)
            except wasmtime.WasmtimeError as e:
                # A normal exit from a WASI program is raised as an exception.
                # We check the string representation to see if it's a clean exit.
                if "Exited with i32 exit status 0" not in str(e):
                    # If it's not a clean exit, it's a real error.
                    with open(stdout_file.name, 'rb') as f:
                        error_output = f.read().decode('utf-8')
                    # We raise a new error with the captured output.
                    raise RuntimeError(f"esbuild WASM execution failed:\\n{error_output}") from e

            # 5. Read the result from the stdout file.
            with open(stdout_file.name, 'rb') as f:
                output_bytes = f.read()

            if not output_bytes:
                raise RuntimeError("esbuild WASM process returned no data.")

            # 6. Decode and parse the JSON response.
            response = json.loads(output_bytes.decode('utf-8'))

            if error_message := response.get("error"):
                raise RuntimeError(f"esbuild transformation failed: {error_message}")

            return response.get("code", "")

        finally:
            # 7. CRITICAL: Clean up the temporary files.
            os.unlink(stdin_file.name)
            os.unlink(stdout_file.name)
