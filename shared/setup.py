"""Setup configuration for shared package."""

from setuptools import find_packages, setup

setup(
    name="game-scheduler-shared",
    version="0.1.0",
    description="Shared models, schemas, and utilities for game scheduler services",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.11",
    install_requires=[
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "asyncpg>=0.29.0",
        "aio-pika>=9.0.0",
        "redis>=5.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "ruff>=0.1.0",
        ],
    },
)
