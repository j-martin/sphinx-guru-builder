# sphinx-guru-builder

## Installation

```
$ pip install sphinx-guru-builder
```

## Usage

1. Add the extension to your `conf.py`.

```py
extensions = [
    "sphinx_guru_builder",
]
```

2. Optionally, add `html_published_location` to create a link on each page to
   the original docs.

```py
html_published_location = "https://example.com/docs"`
```

3. Build your docs.

```
$ sphinx-build -b guru source_dir build_dir
```

4. Upload the generated `guru.zip` file in the parent directory of the
   `build_dir`.

See [Guru API docs](https://developer.getguru.com/docs/guru-sync-manual-api) for instruction on how to upload the archive.
