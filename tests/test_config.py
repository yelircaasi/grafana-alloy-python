import pulumi
import pytest

from grafana_alloy import AlloyConfig, Block, Raw, concat, sys_env


class _Mocks(pulumi.runtime.Mocks):
    def new_resource(self, args):  # type: ignore[no-untyped-def]
        return [args.name + "_id", args.inputs]

    def call(self, args):  # type: ignore[no-untyped-def]
        return {}


pulumi.runtime.set_mocks(_Mocks(), project="p", stack="s", preview=False)


def test_full_example() -> None:
    cfg = AlloyConfig()
    remote = cfg.add(
        Block(
            "prometheus.remote_write",
            "default",
            blocks=[
                Block(
                    "endpoint",
                    url="https://mimir.example.com/api/v1/push",
                    blocks=[Block("basic_auth", username="svc", password=sys_env("PW"))],
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
            forward_to=[remote.ref("receiver")],
        )
    )
    assert str(cfg) == (
        'prometheus.remote_write "default" {\n'
        "  endpoint {\n"
        '    url = "https://mimir.example.com/api/v1/push"\n'
        "\n"
        "    basic_auth {\n"
        '      username = "svc"\n'
        '      password = sys.env("PW")\n'
        "    }\n"
        "  }\n"
        "}\n"
        "\n"
        'prometheus.scrape "app" {\n'
        '  targets         = [{__address__ = "localhost:9090"}]\n'
        '  scrape_interval = "15s"\n'
        "  forward_to      = [prometheus.remote_write.default.receiver]\n"
        "}\n"
    )


def test_scalars_and_escaping() -> None:
    cfg = AlloyConfig([Block("x", "y", a=None, b=True, c=1, d=1.5, e='q"\\\n\t\x01')])
    assert str(cfg) == (
        'x "y" {\n  a = null\n  b = true\n  c = 1\n  d = 1.5\n  e = "q\\"\\\\\\n\\t\\u0001"\n}\n'
    )


def test_multiline_collections() -> None:
    cfg = AlloyConfig([Block("x", "y", t=[{"a": 1}, {"b": 2}], u=[1, 2], k={"a-b": 1})])
    assert str(cfg) == (
        'x "y" {\n  t = [\n    {a = 1},\n    {b = 2},\n  ]\n  u = [1, 2]\n  k = {"a-b" = 1}\n}\n'
    )


def test_ref_call_raw_and_empty_block() -> None:
    cfg = AlloyConfig([Block("x", "y", a=concat([1], [2]), b=Raw("1 + 2"), blocks=[Block("e")])])
    assert str(cfg) == 'x "y" {\n  a = array.concat([1], [2])\n  b = 1 + 2\n\n  e {}\n}\n'


def test_comments_and_separation() -> None:
    cfg = AlloyConfig()
    cfg.comment("hello\nworld")
    cfg.add(Block("logging", level="info"))
    assert str(cfg) == '// hello\n// world\nlogging {\n  level = "info"\n}\n'


def test_duplicate_and_unlabelled_ref() -> None:
    cfg = AlloyConfig([Block("a.b", "c")])
    with pytest.raises(ValueError):
        cfg.add(Block("a.b", "c"))
    with pytest.raises(ValueError):
        Block("logging").ref()


def test_invalid_values() -> None:
    with pytest.raises(TypeError):
        str(AlloyConfig([Block("x", "y", a=object())]))
    with pytest.raises(ValueError):
        Block("x", "y", **{"bad-key": 1})


@pulumi.runtime.test
def test_pulumi_output() -> pulumi.Output[None]:
    secret = pulumi.Output.secret("p@ss")
    cfg = AlloyConfig([Block("x", "y", url=pulumi.Output.from_input("http://h"), pw=secret)])
    rendered = cfg.render()
    assert isinstance(rendered, pulumi.Output)

    def check(text: str) -> None:
        assert text == 'x "y" {\n  url = "http://h"\n  pw  = "p@ss"\n}\n'

    return rendered.apply(check)  # type: ignore[no-any-return]
