    install_requires=[
        "click>=8.0.0",
        "rich>=10.0.0",
        "aiofiles~=24.1.0",
        "uvicorn~=0.34.0",
    ],
    entry_points={
        "console_scripts": [
            "radis-diagnose=app.cli.diagnose:cli",
        ],
    },
)
