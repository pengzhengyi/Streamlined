from distutils.core import setup

from setuptools import find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setup(
    name="streamlined",
    version="0.4.4",
    author="Zhengyi Peng",
    author_email="pengzhengyipengzhengyi@gmail.com",
    description="Make ML or generic pipeline more streamlined",
    keywords="workflow pipeline",
    install_requires=[
        "ray[default]",
        "treelib",
        "diskcache",
        "networkx[default]",
        "decorator",
        "wrapt",
        "matplotlib",
        "pydot",
        "aiorun",
        "uvloop",
        "aiofile",
        "pqdict",
        "aiofiles",
        "nest_asyncio",
        "rich",
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(include=["streamlined", "streamlined.*"]),
    project_urls={
        "Bug Tracker": "https://github.com/pengzhengyi/Streamlined/issues",
        "Documentation": "https://github.com/pengzhengyi/Streamlined/wiki",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    url="https://github.com/pengzhengyi/Streamlined",
)
