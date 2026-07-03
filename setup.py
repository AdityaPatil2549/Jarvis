from setuptools import setup, find_packages

setup(
    name="jarvis-lite",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        # See requirements.txt
    ],
    entry_points={
        "console_scripts": [
            "jarvis=main:main",
        ],
    },
)
