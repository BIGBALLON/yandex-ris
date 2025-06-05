from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="yandex-ris",
    version="0.1.2",
    author="BIGBALLON",
    author_email="fm.bigballon@gmail.com",
    description="A professional reverse image search and crawling tool that uses Yandex's image search engine to find and download similar images.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BIGBALLON/yandex-ris",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Multimedia :: Graphics",
    ],
    python_requires=">=3.8",
    install_requires=[
        "selenium>=4.18.1",
        "webdriver-manager>=4.0.1",
        "beautifulsoup4>=4.12.3",
        "icrawler>=0.6.10",
        "python-dateutil>=2.8.2",
        "colorlog>=6.8.2",
        "tqdm>=4.66.2",
        "requests>=2.31.0",
        "urllib3>=2.0.0",
        "lxml>=5.1.0",
        "pillow>=10.2.0",
    ],
    entry_points={
        "console_scripts": [
            "yandex-ris=yandex_ris.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/BIGBALLON/yandex-ris/issues",
        "Source": "https://github.com/BIGBALLON/yandex_ris",
    },
) 