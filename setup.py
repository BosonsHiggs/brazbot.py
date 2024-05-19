from setuptools import setup, find_packages

setup(
    name="brazbot",
    version="0.1.0",
    description="A simple Discord bot library",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Aril Ogai",
    author_email="iagolirapassos@gmail.com",
    url="https://github.com/BosonsHiggs/brazbot.py",
    packages=find_packages(),
    install_requires=[
        "aiohttp"
    ],
    ,
    entry_points={
        'console_scripts': [
            'brazbot = brazbot.bot:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)
