from os.path import join as pjoin

from setuptools import setup, find_packages


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
