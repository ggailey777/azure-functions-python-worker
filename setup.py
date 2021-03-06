import distutils.cmd
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from distutils.command import build

from setuptools import setup
from setuptools.command import develop


# TODO: change this to something more stable when available.
WEBHOST_URL = ('http://ci.appveyor.com/api/buildjobs/y6wonxc4o3k529s8'
               '/artifacts/Functions.Binaries.2.0.11549-alpha.zip')


class BuildGRPC:
    """Generate gRPC bindings."""
    def _gen_grpc(self):
        cwd = os.getcwd()

        subprocess.run([
            sys.executable, '-m', 'grpc_tools.protoc',
            '-I', os.sep.join(('azure', 'worker', 'protos')),
            '--python_out', cwd,
            '--grpc_python_out', cwd,
            os.sep.join(('azure', 'worker', 'protos',
                         'azure', 'worker', 'protos',
                         'FunctionRpc.proto')),
        ], check=True, stdout=sys.stdout, stderr=sys.stderr)


class build(build.build, BuildGRPC):
    def run(self, *args, **kwargs):
        self._gen_grpc()
        super().run(*args, **kwargs)


class develop(develop.develop, BuildGRPC):
    def run(self, *args, **kwargs):
        self._gen_grpc()
        super().run(*args, **kwargs)


class webhost(distutils.cmd.Command):
    description = 'Download and setup Azure Functions Web Host.'
    user_options = [
        ('webhost-url', None,
            'A custom URL to download Azure Web Host from.'),
        ('webhost-dir', None,
            'A path to the directory where Azure Web Host will be installed.'),
    ]

    def initialize_options(self):
        self.webhost_url = None
        self.webhost_dir = None

    def finalize_options(self):
        if self.webhost_url is None:
            self.webhost_url = WEBHOST_URL

        if self.webhost_dir is None:
            self.webhost_dir = \
                pathlib.Path(__file__).parent / 'build' / 'webhost'

    def run(self):
        with tempfile.NamedTemporaryFile() as zipf:
            zipf.close()
            try:
                print('Downloading Azure Functions Web Host...')
                urllib.request.urlretrieve(self.webhost_url, zipf.name)
            except Exception as e:
                print(
                    f"could not download Azure Functions Web Host binaries "
                    f"from {self.webhost_url}: {e!r}", file=sys.stderr)
                sys.exit(1)

            if not self.webhost_dir.exists():
                os.makedirs(self.webhost_dir, exist_ok=True)

            with zipfile.ZipFile(zipf.name) as archive:
                print('Extracting Azure Functions Web Host binaries...')

                # We cannot simply use extractall(), as the archive
                # contains Windows-style path names, which are not
                # automatically converted into Unix-style paths, so
                # extractall() will produce a flat directory with
                # backslashes in file names.
                for archive_name in archive.namelist():
                    destination = \
                        self.webhost_dir / archive_name.replace('\\', os.sep)
                    if not destination.parent.exists():
                        os.makedirs(destination.parent, exist_ok=True)
                    with archive.open(archive_name) as src, \
                            open(destination, 'wb') as dst:
                        dst.write(src.read())


setup(
    name='azure',
    version='0.0.1',
    description='Azure Python Functions',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Environment :: Web Environment',
        'Development Status :: 3 - Alpha',
    ],
    license='MIT',
    packages=['azure', 'azure.functions',
              'azure.worker', 'azure.worker.protos'],
    provides=['azure'],
    install_requires=[
        'grpcio',
        'grpcio-tools',
    ],
    extras_require={
        'dev': [
            'pytest',
            'requests',
            'mypy',
            'flake8',
        ]
    },
    include_package_data=True,
    cmdclass={
        'build': build,
        'develop': develop,
        'webhost': webhost,
    },
    test_suite='tests'
)
