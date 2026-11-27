# grafana-alloy

Build [Grafana Alloy](https://grafana.com/docs/alloy/) configuration files in Python and
serialize them to Alloy syntax. One-way (Python -> Alloy) by design; handy with Pulumi.

```python
from grafana_alloy import AlloyConfig, Block, sys_env

cfg = AlloyConfig()

remote = cfg.add(
    Block(
        "prometheus.remote_write",
        "default",
        blocks=[
            Block(
                "endpoint",
                url="https://mimir.example.com/api/v1/push",
                blocks=[Block("basic_auth", username="svc", password=sys_env("MIMIR_PASSWORD"))],
            )
        ],
    )
)

cfg.add(
    Block(
        "prometheus.scrape",
        "app",
        targets=[{"__address__": "localhost:9090"}],
        scrape_interval="15s",
        forward_to=[remote.ref("receiver")],  # prometheus.remote_write.default.receiver
    )
)

print(cfg)  # or cfg.write("config.alloy")
```

## Concepts

- `AlloyConfig`: one Alloy file. `add()` returns the block; `render()`, `str()` and `write()` serialize.
- `Block(name, label=None, *, blocks=(), **attributes)`: a component or config block. Attributes
  are kwargs; nested blocks go in `blocks=[...]` or `.add(...)`. `block.ref("export")` builds a reference.
- Values: `str`, `int`, `float`, `bool`, `None`, `list`/`tuple`, `dict`, plus `Ref`, `Call`
  (`sys_env`, `concat`, ...) and `Raw("verbatim alloy")` as an escape hatch.

## Pulumi

If any attribute value is a `pulumi.Output`, `cfg.render()` returns a `pulumi.Output[str]`
(secrets stay secret). Install the extra with `pip install grafana-alloy[pulumi]`.

## Development

```sh
uv sync
uv run pytest
uv run ruff check . && uv run mypy src
```
