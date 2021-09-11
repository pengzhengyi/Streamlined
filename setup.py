from distutils.core import setup

from setuptools import find_packages

setup(
    name="Streamlined",
    version="0.1.0",
    description="Make ML or generic pipeline more streamlined",
    author="Zhengyi Peng",
    author_email="pengzhengyipengzhengyi@gmail.com",
    packages=find_packages(include=["streamlined", "streamlined.*"]),
)
