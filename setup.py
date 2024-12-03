# setup.py
from setuptools import setup, find_packages

setup(
    name="objectif",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'PyQt6',
        'loguru',
        'pydantic',
        'adb-shell[usb]',
        'python-dotenv',
        'pywin32'
    ],
)