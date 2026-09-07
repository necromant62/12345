#!/usr/bin/env python3
"""Validate generated Zabbix 5.0 XML template."""

from pathlib import Path
from sys import path as sys_path
from xml.etree.ElementTree import parse

ROOT = Path(__file__).resolve().parents[1]
sys_path.insert(0, str(Path(__file__).resolve().parent))

from generate_webtel_zabbix_template import TPL, to_classic_expr

XML = ROOT / "zabbix" / "zbx_webtel_ii_es_aux_5.0.xml"


def test_classic_expressions() -> None:
    assert to_classic_expr(f"last(/{TPL}/webtel.ups.connected)=0") == (
        f"{{{TPL}:webtel.ups.connected.last()}}=0"
    )
    assert to_classic_expr(f"min(/{TPL}/webtel.output.load,5m)>{{$UPS.LOAD.WARN}}") == (
        f"{{{TPL}:webtel.output.load.min(5m)}}>{{$UPS.LOAD.WARN}}"
    )
    assert to_classic_expr(
        f"length(last(/{TPL}/webtel.ups.warnings))>0 and "
        f"last(/{TPL}/webtel.ups.warnings)<>\"0\""
    ) == (
        f"{{{TPL}:webtel.ups.warnings.strlen()}}>0 and "
        f"{{{TPL}:webtel.ups.warnings.last()}}<>\"0\""
    )


def test_xml() -> None:
    tree = parse(XML)
    root = tree.getroot()
    assert root.tag == "zabbix_export"
    assert root.findtext("version") == "5.0"
    assert not root.findall(".//uuid")
    assert root.find("./value_maps/value_map") is not None

    tpl = root.find("./templates/template")
    assert tpl is not None
    assert tpl.findtext("template") == "UPS WEBtel II ES AUX SNMP"
    assert tpl.find("./applications/application") is not None

    items = tpl.findall("./items/item")
    assert len(items) >= 70

    keys = []
    oids = []
    for item in items:
        assert item.findtext("type") == "SNMP_AGENT"
        key = item.findtext("key")
        oid = item.findtext("snmp_oid")
        assert key
        assert oid and oid.startswith(".1.3.6.1.")
        assert item.find("./applications/application/name") is not None
        keys.append(key)
        oids.append(oid)
        prep = item.find("./preprocessing/step")
        if prep is not None and prep.findtext("type") == "MULTIPLIER":
            assert prep.findtext("params")
            assert prep.find("parameters") is None
    assert len(keys) == len(set(keys))

    required = {
        ".1.3.6.1.4.1.22138.1.10.1.1.0",
        ".1.3.6.1.4.1.22138.1.10.1.2.0",
        ".1.3.6.1.4.1.22138.1.10.3.3.12.0",
        ".1.3.6.1.4.1.22138.1.10.3.4.4.0",
        ".1.3.6.1.4.1.22138.1.10.3.4.6.0",
    }
    assert required.issubset(set(oids)), required - set(oids)

    assert tpl.find("./graphs") is None
    graphs = root.findall("./graphs/graph")
    assert len(graphs) >= 5
    keyset = set(keys)
    for graph in graphs:
        for gi in graph.findall("./graph_items/graph_item"):
            assert gi.findtext("./item/key") in keyset

    triggers = root.findall(".//triggers/trigger")
    assert len(triggers) >= 15
    expressions = []
    for tr in triggers:
        expr = tr.findtext("expression")
        assert expr and expr.startswith("{")
        assert "last(/" not in expr
        assert f"{tpl.findtext('template')}:" in expr
        assert tr.findtext("priority") in {
            "INFO",
            "WARNING",
            "AVERAGE",
            "HIGH",
            "DISASTER",
        }
        expressions.append(expr)
    joined = "\n".join(expressions)
    assert f"{{{tpl.findtext('template')}:webtel.ups.connected.last()}}=0" in joined
    assert ".strlen()" in joined
    assert ".min(5m)" in joined
    assert tpl.find("./valuemaps") is None

    print(f"OK {XML.name}: {len(items)} items, {len(triggers)} triggers, {len(graphs)} graphs")


if __name__ == "__main__":
    test_classic_expressions()
    test_xml()
