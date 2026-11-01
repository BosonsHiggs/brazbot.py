from pathlib import Path
from setuptools import find_packages, setup

readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="brazbot",
    version="2.0.0",
    author="BosonsHiggs",
    description="Production-ready native Python library for Discord API v10 and Voice Gateway v8 with zero third-party Discord dependencies.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BosonsHiggs/brazbot.py",
    packages=find_packages(exclude=("tests*", "examples*")),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "aiohttp>=3.14.5",
        "cryptography>=44.0.0",
        "yt-dlp>=2026.03.17",
    ],
    extras_require={
        "speed": [
            "aiodns>=3.2.0",
            "Brotli>=1.1.0",
            "PyNaCl>=1.5.0",
        ],
        "dev": [
            "pytest>=8.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Communications :: Chat",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    keywords="discord api v10 bot voice gateway v8 slash-commands components2 automod moderation music",
)
