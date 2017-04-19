# PyGrim - another lightweight Python 2 web framework

## Dependencies
- Python 2
- uwsgi with yaml support
- PyYAML

## Example
First, change paths in pygrim.yaml to the ones you are really using.

Second, make sure at least one of your pythonpath in your yaml config points to the directory where PyGrim is sitting, or move PyGrim to a place where Python will find it.

Start the server with

```
uwsgi_python27 --yaml <path-to-yaml-file>
```

## How do I...?
You can either:

- See [Wiki](https://github.com/ondrejkajinek/pyGrim/wiki)

or 

- Use the Source, look.
