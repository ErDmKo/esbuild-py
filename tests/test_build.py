import unittest
import importlib
import tempfile
import os
import shutil
import pytest
import esbuild_py
from unittest import mock

go_installed = shutil.which("go")

@pytest.mark.skipif(not go_installed, reason="Go is not installed")
class TestBuildAPI(unittest.TestCase):
    """
    Tests for the `esbuild.build()` API.
    """

    def setUp(self):
        """
        Create a temporary directory to store source and output files for tests.
        """
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """
        Clean up the temporary directory.
        """
        self.temp_dir.cleanup()

    def create_files(self):
        # --- 1. Create source files ---

        # An imported utility file
        lib_path = os.path.join(self.temp_dir.name, 'lib.js')
        with open(lib_path, 'w') as f:
            f.write("export const getMessage = () => 'Hello from lib';")

        # The main entry point
        entry_path = os.path.join(self.temp_dir.name, 'app.js')
        with open(entry_path, 'w') as f:
            f.write("import { getMessage } from './lib.js'; console.log(getMessage());")

        # The destination for the bundled output
        outfile_path = os.path.join(self.temp_dir.name, 'bundle.js')

        return {
            'outfile_path': outfile_path,
            'lib_path': lib_path,
            'entry_path': entry_path
        }

    @mock.patch('esbuild_py._native_backend.NativeBackend', side_effect=FileNotFoundError)
    def test_wasm_backend_build(self, mock_native_backend):
        importlib.reload(esbuild_py)

        files = self.create_files()
        self.assertEqual(esbuild_py.BACKEND, 'wasm', "The WASM backend should be active after the native one fails.")

        result = esbuild_py.build(
            entry_points=[files['entry_path']],
            outfile=files['outfile_path'],
        )

        self.assertEqual(len(result['errors']), 0, "Build should complete without errors.")
        self.assertEqual(len(result['warnings']), 0, "Build should complete without warnings.")

        # The content of the file should be a bundled application
        with open(files['outfile_path'], 'r') as f:
            content = f.read()

        # Check that code from both files is present in the bundle
        self.assertIn("Hello from lib", content, "Content from the imported file should be in the bundle.")
        self.assertIn("console.log", content, "Content from the entry point should be in the bundle.")
        # Check that esbuild added its comments indicating the source files
        self.assertIn("lib.js", content)
        self.assertIn("app.js", content)

    def test_native_build_simple_bundle(self):
        """
        Tests the native build functionality with a single entry point that
        imports another file, verifying that they are bundled correctly.
        """
        # This test is specifically for the native backend.
        if esbuild_py.BACKEND != 'native':
            # In a more complex setup, one might use pytest markers to skip.
            # For now, we'll just raise an error if the wrong backend is active.
            self.fail("This test requires the 'native' backend to be active.")

        files = self.create_files()

        result = esbuild_py.build(
            entry_points=[files['entry_path']],
            outfile=files['outfile_path'],
        )

        # The build result should not contain errors
        self.assertEqual(len(result['errors']), 0, "Build should complete without errors.")
        self.assertEqual(len(result['warnings']), 0, "Build should complete without warnings.")

        # The output file should exist
        self.assertTrue(os.path.exists(files['outfile_path']), "The bundled output file should be created.")

        # The content of the file should be a bundled application
        with open(files['outfile_path'], 'r') as f:
            content = f.read()

        # Check that code from both files is present in the bundle
        self.assertIn("Hello from lib", content, "Content from the imported file should be in the bundle.")
        self.assertIn("console.log", content, "Content from the entry point should be in the bundle.")
        # Check that esbuild added its comments indicating the source files
        self.assertIn("lib.js", content)
        self.assertIn("app.js", content)

if __name__ == '__main__':
    unittest.main()
