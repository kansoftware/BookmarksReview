from setuptools import setup, find_packages

setup(
    name="bookmark_summarizer",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "httpx>=0.25.0",
        "beautifulsoup4>=4.12.0",
        "openai>=1.3.0",
        "python-dotenv>=1.0.0",
        "aiofiles>=23.2.0",
        "pydantic>=2.0.0",
        "mermaid-py>=0.4.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="Утилита для экспорта и описания закладок браузера",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/bookmark_summarizer",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "bookmark_summarizer=src.main:main",
        ],
    },
)