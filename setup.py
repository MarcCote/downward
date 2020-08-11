import os
import sys
import shutil
import subprocess
from os.path import join as pjoin

from setuptools import setup, find_packages


BASEPATH = os.path.dirname(os.path.abspath(__file__))
subprocess.check_call(['python', 'build.py', '--library'], cwd=BASEPATH)

libdownward = 'builds/library/search/libdownward.so'
if not os.path.isfile(libdownward):
    print('ERROR: Unable to find required library %s.'%(libdownward))
    sys.exit(1)

shutil.copy(libdownward, "src/fast_downward/libdownward.so")

if os.path.exists("src/fast_downward/translate"):
    os.unlink("src/fast_downward/translate")
os.symlink("../translate", "src/fast_downward/translate", target_is_directory=True)

if os.path.exists("src/fast_downward/driver"):
    os.unlink("src/fast_downward/driver")
os.symlink("../../driver", "src/fast_downward/driver", target_is_directory=True)

setup(
    name='fast_downward',
    version=open(pjoin("driver", "version.py")).readlines()[-1].split("=")[-1].strip('+" \n'),
    author='',
    package_dir={"": "src"},
    packages=find_packages("src", exclude=["driver", "translate.*"]),
    package_data={'fast_downward': ['libdownward.so']},
    include_package_data=True,
    license=open('LICENSE.md'),
    zip_safe=False,
    description="Fast-Downward - Python API",
    install_requires=open('requirements.txt').readlines(),
)
