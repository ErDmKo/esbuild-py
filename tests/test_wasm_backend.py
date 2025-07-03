import unittest
import importlib
from unittest import mock

# Import the package itself to get a handle on it for reloading
import esbuild_py

class TestWasmBackend(unittest.TestCase):
    """
    Tests the WASM fallback mechanism by mocking the native backend.
    """

    # We patch the NativeBackend class within the module where it's defined.
    # When the __init__.py tries to instantiate it, this patch will intercept
    # the call and raise a FileNotFoundError, triggering the WASM fallback.
    @mock.patch('esbuild_py._native_backend.NativeBackend', side_effect=FileNotFoundError)
    def test_jsx_transformation_via_wasm(self, mock_native_backend):
        """
        Verify that the WASM backend is used when the native backend fails
        and that it correctly transforms code.
        """
        # The esbuild_py package is initialized on its first import. To test the
        # fallback logic, we must force a reload of the module *while* the patch
        # is active. This re-triggers the backend selection logic.
        importlib.reload(esbuild_py)

        # 1. Verify that the WASM backend is now active
        self.assertEqual(esbuild_py.BACKEND, 'wasm', "The WASM backend should be active after the native one fails.")

        # 2. Perform a standard transformation test
        jsx = """
import * as React from 'react'
import * as ReactDOM from 'react-dom'

ReactDOM.render(
    <h1>Hello, world!</h1>,
    document.getElementById('root')
);
        """
        expected_js = """
import * as React from "react";
import * as ReactDOM from "react-dom";
ReactDOM.render(
  /* @__PURE__ */ React.createElement("h1", null, "Hello, world!"),
  document.getElementById("root")
);
        """.strip()

        # Use the main transform function, which should now be routed to the WASM backend
        actual_js = esbuild_py.transform(jsx, loader='jsx').strip()

        self.assertEqual(actual_js, expected_js)

        # The backend will be automatically restored when the mock patch exits
        # context at the end of the test function.
