from setuptools import setup, find_packages

# Read the README for the long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agentradis",
    version="0.1.0",
    author="Stanley Zheng",
    description="Radis Project: An Agent-based System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "aiofiles~=24.1.0",
        "browser-use~=0.1.40",
        "browsergym~=0.13.3",
        "colorama~=0.4.6",
        "datasets~=3.2.0",
        "googlesearch-python~=1.3.0",
        "gymnasium~=1.0.0",
        "html2text~=2024.2.26",
        "jsonschema~=4.21.1",
        "loguru~=0.7.3",
        "numpy",
        "openai~=1.58.1",
        "pillow~=10.4.0",
        "pydantic_core~=2.27.2",
        "pydantic~=2.10.4",
        "pyyaml~=6.0.2",
        "tenacity~=9.0.0",
        "unidiff~=0.7.5",
        "uvicorn~=0.34.0",
    ],
)
