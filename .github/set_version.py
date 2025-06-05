import sys
import re

version = sys.argv[1]

version_file = "yandex_ris/version.py"
setup_file = "setup.py"

with open(setup_file, "r") as f:
    setup_content = f.read()

setup_content = re.sub(
    r'version\s*=\s*[\'\"](.*?)[\'\"]',
    f'version="{version}"',
    setup_content
)

with open(setup_file, "w") as f:
    f.write(setup_content)

with open(version_file, "r") as f:
    version_content = f.read()

version_content = re.sub(
    r'__version__\s*=\s*[\'\"](.*?)[\'\"]',
    f'__version__ = "{version}"',
    version_content
)

with open(version_file, "w") as f:
    f.write(version_content)

print(f"✅ Updated setup.py and version.py to version {version}")
