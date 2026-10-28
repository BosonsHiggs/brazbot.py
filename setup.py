from pathlib import Path
from setuptools import find_packages, setup

README_PATH = Path(__file__).parent / "README.md"
long_description = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""

setup(
    name="brazbot",
    version="2.0.0",
    description="Biblioteca brasileira nativa e assíncrona para criação de bots na API v10 e Voice Gateway v8 do Discord",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Aril Ogai",
    author_email="iagolirapassos@gmail.com",
    url="https://github.com/BosonsHiggs/brazbot.py",
    project_urls={
        "Bug Tracker": "https://github.com/BosonsHiggs/brazbot.py/issues",
        "Source Code": "https://github.com/BosonsHiggs/brazbot.py",
    },
    license="MIT",
    packages=find_packages(exclude=("tests*", "examples*")),
    install_requires=[
        "aiohttp>=3.9.0",
        "PyNaCl>=1.5.0",
        "cryptography>=38.0.0",
        "yt-dlp>=2024.1.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "latest": [
            "aiohttp>=3.14.5",
            "PyNaCl>=1.6.2",
            "cryptography>=44.0.0",
            "yt-dlp>=2026.10.26",
            "python-dotenv>=1.2.4",
        ],
    },
    entry_points={
        "console_scripts": [
            "brazbot = brazbot.bot:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Topic :: Communications :: Chat",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.10",
)
