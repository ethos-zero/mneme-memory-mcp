from setuptools import find_packages, setup


setup(
    name="mneme-memory-mcp",
    version="0.1.0",
    description="A local MCP memory bridge for Claude, Codex, Hermes, and other agents.",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=["mcp>=1.8"],
    entry_points={
        "console_scripts": [
            "mneme-memory-mcp=mneme_memory_mcp.server:main",
            "mneme-memory-doctor=mneme_memory_mcp.doctor:main",
        ]
    },
)
