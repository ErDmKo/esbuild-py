import ctypes
import json
import logging
import os
import site
from pathlib import Path
from sysconfig import get_config_var

log = logging.getLogger(__name__)


class NativeBackend:
    """
    A wrapper for the native esbuild Go binary.
    This class is responsible for loading the shared library (.so/.dll/.dylib)
    and interacting with it via ctypes, with a focus on safe memory management.
    """

    def __init__(self):
        """Finds and loads the shared library, and sets up function signatures."""
        log.debug("Initializing NativeBackend...")
        so_filepath = self._get_lib_path()
        if so_filepath is None:
            log.debug("Native library not found by _get_lib_path.")
            raise FileNotFoundError("Could not find the native shared library.")

        log.info(f"LOADING NATIVE LIBRARY AT: {so_filepath}")
        log.debug("Attempting to load with ctypes...")
        try:
            self.so = ctypes.cdll.LoadLibrary(so_filepath)
            log.debug("ctypes.cdll.LoadLibrary successful.")
        except OSError as e:
            log.debug(f"ctypes.cdll.LoadLibrary failed: {e}")
            raise

        # --- Set up function signatures for safe FFI ---

        # The Go 'transform' function returns a C string (char*) that we must free.
        # By setting restype to c_void_p, we get back a raw pointer (as an int),
        # giving us full control over memory management.
        self._transform = self.so.transform
        self._transform.argtypes = [ctypes.c_char_p]
        self._transform.restype = ctypes.c_void_p

        # The Go 'free' function takes the pointer we received and frees it.
        self._free = self.so.free
        self._free.argtypes = [ctypes.c_void_p]
        self._free.restype = None  # It returns nothing

        log.debug("NativeBackend initialization complete.")

    def _get_lib_path(self) -> str | None:
        """
        Finds the path to the compiled native shared library using a robust
        search strategy.
        """
        ext_suffix = get_config_var('EXT_SUFFIX')
        # The simple module name, not the full package path.
        # setuptools uses the part after the last dot of the extension name.
        # 'esbuild_py._esbuild' becomes '_esbuild' + suffix.
        so_filename = '_esbuild' + ext_suffix
        log.debug(f"Looking for library file: {so_filename}")

        # For an editable install, setuptools places the compiled .so file
        # inside the source package directory.
        package_dir = str(Path(__file__).absolute().parent)
        
        # 1. Check the primary location first.
        primary_path = os.path.join(package_dir, so_filename)
        log.debug(f"Checking primary path: {primary_path}")
        if os.path.exists(primary_path):
            return primary_path

        # 2. As a fallback, check the standard site-packages locations.
        log.debug("Primary path not found. Checking site-packages...")
        for d in site.getsitepackages():
            site_path = os.path.join(d, "esbuild_py", so_filename)
            log.debug(f"Checking site-packages path: {site_path}")
            if os.path.exists(site_path):
                return site_path

        log.debug("Library not found in any checked paths.")
        return None

    def transform(self, code: str, **kwargs):
        """Proxy for the Go transform function with safe memory management."""
        options = kwargs.copy()
        if 'loader' not in options:
            options['loader'] = 'jsx'

        request = {"code": code, "options": options}
        request_json = json.dumps(request)
        
        result_ptr = None
        try:
            # 1. Call the Go function, which returns a raw pointer.
            result_ptr = self._transform(request_json.encode('utf-8'))

            if not result_ptr:
                raise RuntimeError("esbuild transform function returned a NULL pointer.")

            # 2. Cast the raw pointer to a C string pointer and get its value.
            c_string = ctypes.cast(result_ptr, ctypes.c_char_p).value
            
            # 3. Decode the bytes to a Python string.
            result_json = c_string.decode('utf-8')
            log.info(f"Received raw JSON from native call: {result_json!r}")
            
            # 4. Process the response.
            response = json.loads(result_json)

            if response.get('errors') and len(response['errors']) > 0:
                error_messages = [e.get('text', 'Unknown error') for e in response['errors']]
                raise RuntimeError(f"esbuild transformation failed: {', '.join(error_messages)}")

            return response.get('code', '')

        finally:
            # 5. CRITICAL: Always free the memory allocated by Go.
            # This runs even if errors occur in the `try` block.
            if result_ptr:
                log.debug(f"Freeing memory at address: {result_ptr}")
                self._free(result_ptr)