from grafana_alloy import AlloyConfig, Block, sys_env


def make_basic_config() -> str:

    cfg = AlloyConfig()

    cfg.comment("Basic observability pipeline for a Kubernetes node")

    cfg.add(Block("logging", level="info", format="logfmt"))

    # Prometheus metrics
    mimir = cfg.add(
        Block(
            "prometheus.remote_write",
            "mimir",
            blocks=[
                Block(
                    "endpoint",
                    url="https://mimir.example.com/api/v1/push",
                    blocks=[
                        Block(
                            "basic_auth",
                            username="metrics",
                            password=sys_env("MIMIR_PASSWORD"),
                        )
                    ],
                )
            ],
        )
    )

    cfg.add(
        Block(
            "prometheus.scrape",
            "node",
            targets=[{"__address__": "localhost:9100"}],
            scrape_interval="15s",
            forward_to=[mimir.ref("receiver")],
        )
    )

    pods = cfg.add(Block("discovery.kubernetes", "pods", role="pod"))

    cfg.add(
        Block(
            "prometheus.scrape",
            "app",
            targets=pods.ref("targets"),
            scrape_interval="30s",
            job_name="kubernetes-pods",
            forward_to=[mimir.ref("receiver")],
            blocks=[Block("clustering", enabled=True)],
        )
    )

    # Loki logs
    loki = cfg.add(
        Block(
            "loki.write",
            "loki",
            blocks=[
                Block(
                    "endpoint",
                    url="https://loki.example.com/loki/api/v1/push",
                    blocks=[
                        Block(
                            "basic_auth",
                            username="logs",
                            password=sys_env("LOKI_PASSWORD"),
                        )
                    ],
                )
            ],
        )
    )

    cfg.add(
        Block(
            "loki.source.file",
            "varlogs",
            targets=[{"__path__": "/var/log/*.log"}],
            forward_to=[loki.ref("receiver")],
        )
    )

    # Simple OTel pipeline
    _batch = cfg.add(
        Block(
            "otelcol.processor.batch",
            "default",
            blocks=[
                Block(
                    "output",
                    metrics=[
                        Block("otelcol.exporter.otlp", "default").ref("input")
                    ],  # will be fixed below
                    # better to create the exporter first or use forward refs carefully
                )
            ],
        )
    )

    # Cleaner ordering for the OTel section:
    otel_exporter = cfg.add(
        Block(
            "otelcol.exporter.otlp",
            "other",
            blocks=[
                Block(
                    "client",
                    endpoint="otel-collector.example.com:4317",
                    blocks=[Block("tls", insecure=False)],
                )
            ],
        )
    )

    otel_batch = cfg.add(
        Block(
            "otelcol.processor.batch",
            "other",
            blocks=[
                Block(
                    "output",
                    metrics=[otel_exporter.ref("input")],
                    logs=[otel_exporter.ref("input")],
                    traces=[otel_exporter.ref("input")],
                )
            ],
        )
    )

    cfg.add(
        Block(
            "otelcol.receiver.otlp",
            "complex",
            blocks=[
                Block("grpc", endpoint="0.0.0.0:4317"),
                Block("http", endpoint="0.0.0.0:4318"),
                Block(
                    "output",
                    metrics=[otel_batch.ref("input")],
                    logs=[otel_batch.ref("input")],
                    traces=[otel_batch.ref("input")],
                ),
            ],
        )
    )

    return str(cfg)  # or cfg.render() if you need a Pulumi Output


if __name__ == "__main__":
    print(make_basic_config())
