from setuptools import find_packages, setup

setup(
    name="sphinx-guru-builder",
    version="0.0.0",
    description="",
    zip_safe=False,
    packages=["sphinx_guru_builder"],
    package_data={"sphinx_guru_builder": ["theme/*"]},
    install_requires=["pyaml"],
)
