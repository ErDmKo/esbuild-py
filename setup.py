import logging
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from subprocess import call, check_output, CalledProcessError
from distutils.errors import CompileError

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- Go Build Logic ---

def is_go_available():
    """Checks if the `go` command is available on the system PATH."""
    try:
        check_output(['go', 'version'])
        return True
    except (CalledProcessError, FileNotFoundError):
        return False

class GoExtension(Extension):
    """A custom setuptools Extension to identify Go extensions."""
    pass

class build_go_ext(build_ext):
    """
    A custom `build_ext` command to compile Go extensions.
    It builds the Go source files into a shared library that can be loaded by ctypes.
    """
    def build_extension(self, ext: Extension):
        if not isinstance(ext, GoExtension):
            return super().build_extension(ext)

        ext_path = self.get_ext_fullpath(ext.name)

        # The WASM build is now pre-compiled, so we only handle the native build.
        cmd = ['go', 'build', '-buildmode=c-shared', '-o', ext_path]
        cmd += ext.sources # Use the sources defined in the Extension object

        log.info(f"Running command: {' '.join(cmd)}")
        out = call(cmd)

        if out != 0:
            raise CompileError('Go build failed. Please check your Go installation.')

setup_args = dict(
    install_requires=[],
    zip_safe=False,
)

GO_AVAILABLE = is_go_available()

if GO_AVAILABLE:
    log.info("Go compiler found. Building native extension for optimal performance.")
    # If Go is available, we define the native extension to be compiled.
    setup_args.update(dict(
        ext_modules=[
            GoExtension(
                # We give the native module a specific name to distinguish it.
                name='esbuild_py._esbuild',
                sources=['esbuild_bindings.go'],
            )
        ],
        cmdclass=dict(build_ext=build_go_ext),
    ))
else:
    log.warning("Go compiler not found. Configuring to use WASM fallback.")
    log.warning("The 'wasmtime' package will be installed as a dependency.")
    # If Go is not available, we add 'wasmtime' as a runtime dependency
    # so that the precompiled WASM module can be executed.
    setup_args['package_data'] = { 'esbuild_py': ['precompiled/esbuild.wasm'] }
    setup_args['install_requires'] = ['wasmtime']

# Finally, run the setup command.
setup(**setup_args)
