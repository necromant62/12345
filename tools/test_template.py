#!/usr/bin/env python3
"""Validate generated Zabbix 5.4 XML template."""

from pathlib import Path
from xml.etree.ElementTree import parse

ROOT = Path(__file__).resolve().parents[1]
XML = ROOT / "zabbix" / "zbx_webtel_ii_es_aux_5.4.xml"


def test_xml() -> None:
    tree = parse(XML)
    root = tree.getroot()
    assert root.tag == "zabbix_export"
    assert root.findtext("version") == "5.4"

    tpl = root.find("./templates/template")
    assert tpl is not None
    assert tpl.findtext("template") == "UPS WEBtel II ES AUX SNMP"

    items = tpl.findall("./items/item")
    assert len(items) >= 70

    uuids = [el.text for el in root.findall(".//uuid")]
    assert all(u and len(u) == 32 and all(c in "0123456789abcdef" for c in u) for u in uuids)
    assert len(uuids) == len(set(uuids))

    keys = []
    oids = []
    for item in items:
        assert item.findtext("type") == "SNMP_AGENT"
        key = item.findtext("key")
        oid = item.findtext("snmp_oid")
        assert key
        assert oid and oid.startswith(".1.3.6.1.")
        keys.append(key)
        oids.append(oid)
        assert len(item.findall("value_type")) <= 1
    assert len(keys) == len(set(keys))

    # Core OIDs from manufacturer table 16
    required = {
        ".1.3.6.1.4.1.22138.1.10.1.1.0",
        ".1.3.6.1.4.1.22138.1.10.1.2.0",
        ".1.3.6.1.4.1.22138.1.10.3.3.12.0",
        ".1.3.6.1.4.1.22138.1.10.3.4.4.0",
        ".1.3.6.1.4.1.22138.1.10.3.4.6.0",
    }
    assert required.issubset(set(oids)), required - set(oids)

    keyset = set(keys)
    for graph in tpl.findall("./graphs/graph"):
        for gi in graph.findall("./graph_items/graph_item"):
            assert gi.findtext("./item/key") in keyset

    triggers = root.findall(".//triggers/trigger")
    assert len(triggers) >= 15
    for tr in triggers:
        expr = tr.findtext("expression")
        assert expr and f"/{tpl.findtext('template')}/" in expr
        assert tr.findtext("priority") in {
            "INFO",
            "WARNING",
            "AVERAGE",
            "HIGH",
            "DISASTER",
        }

    print(f"OK {XML.name}: {len(items)} items, {len(triggers)} triggers")


if __name__ == "__main__":
    test_xml()
