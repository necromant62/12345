#!/usr/bin/env python3
"""Generate Zabbix 5.0 XML template from WEBtel II ES AUX MIB."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

ROOT = Path(__file__).resolve().parents[1]
TPL = "UPS WEBtel II ES AUX SNMP"
GROUP = "Templates/Power"
DATE = "2026-09-07T12:00:00Z"
ZBX_VERSION = "5.0"

APP_BY_COMPONENT = {
    "system": "WEBtel System",
    "status": "WEBtel Status",
    "identity": "WEBtel Identity",
    "ratings": "WEBtel Ratings",
    "input": "WEBtel Input",
    "bypass": "WEBtel Bypass",
    "output": "WEBtel Output",
    "internal": "WEBtel Internal",
    "battery": "WEBtel Battery",
    "sensor": "WEBtel Sensors",
    "discrete": "WEBtel Discrete inputs",
    "relay": "WEBtel Relays",
}


def app_name(tags: dict[str, str] | None) -> str:
    return APP_BY_COMPONENT.get((tags or {}).get("component", "status"), "WEBtel Status")


def to_classic_expr(expr: str) -> str:
    """Convert 5.4 last(/host/key) expressions to 5.0 {host:key.last()} syntax."""
    expr = re.sub(
        r"length\(last\(/([^/]+)/([^)]+)\)\)",
        r"{\1:\2.strlen()}",
        expr,
    )
    expr = re.sub(
        r"(min|avg|last)\(/([^/]+)/([^,)]+)(?:,([^)]+))?\)",
        lambda m: (
            f"{{{m.group(2)}:{m.group(3)}.{m.group(1)}({m.group(4)})}}"
            if m.group(4)
            else f"{{{m.group(2)}:{m.group(3)}.{m.group(1)}()}}"
        ),
        expr,
    )
    return expr


def et_text(parent: Element, tag: str, text: str | None = None) -> Element:
    el = SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def add_tags(parent: Element, tags: dict[str, str]) -> None:
    wrap = SubElement(parent, "tags")
    for k, v in tags.items():
        tag = SubElement(wrap, "tag")
        et_text(tag, "tag", k)
        et_text(tag, "value", v)


def add_preprocessing(parent: Element, steps: list[dict]) -> None:
    wrap = SubElement(parent, "preprocessing")
    for step in steps:
        s = SubElement(wrap, "step")
        et_text(s, "type", step["type"])
        params = step.get("parameters") or []
        et_text(s, "params", "\n".join(params))


def add_valuemap_ref(parent: Element, name: str) -> None:
    vm = SubElement(parent, "valuemap")
    et_text(vm, "name", name)


# ---------------------------------------------------------------------------
# Item catalogue
# ---------------------------------------------------------------------------

# Each item: key, name, oid, extra dict
# extra: delay, value_type, units, description, mul, tags, valuemap, inventory,
#        history, trends, triggers

def items() -> list[dict]:
    d: list[dict] = []

    def add(**kw):
        d.append(kw)

    # Standard MIB-2
    add(
        key="webtel.sys.descr",
        name="Описание устройства (sysDescr)",
        oid=".1.3.6.1.2.1.1.1.0",
        delay="1h",
        value_type="TEXT",
        trends="0",
        history="7d",
        description="SNMP sysDescr адаптера WEBtel II ES AUX.",
        tags={"component": "system"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.sys.uptime",
        name="Время работы SNMP-агента (sysUpTime)",
        oid=".1.3.6.1.2.1.1.3.0",
        delay="1m",
        units="uptime",
        description="sysUpTime.0 — время работы SNMP-агента адаптера.",
        tags={"component": "system"},
    )
    add(
        key="webtel.sys.name",
        name="Имя устройства (sysName)",
        oid=".1.3.6.1.2.1.1.5.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        inventory="NAME",
        description="SNMP sysName.",
        tags={"component": "system"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.sys.location",
        name="Расположение адаптера (sysLocation)",
        oid=".1.3.6.1.2.1.1.6.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        inventory="LOCATION",
        description="Текстовое поле расположения адаптера, до 35 символов. OID .1.3.6.1.2.1.1.6.0",
        tags={"component": "system"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )

    # Status
    add(
        key="webtel.ups.connected",
        name="Статус подключения WEBtel к ИБП",
        oid=".1.3.6.1.4.1.22138.1.10.1.1.0",
        delay="30s",
        valuemap="WEBtel UPS connection",
        description="0 — не подключен, 1 — подключен. OID .1.3.6.1.4.1.22138.1.10.1.1.0",
        tags={"component": "status"},
        triggers=[
            {
                "id": "disconnected",
                "name": "WEBtel {HOST.NAME}: нет связи адаптера с ИБП",
                "expression": f"last(/{TPL}/webtel.ups.connected)=0",
                "priority": "HIGH",
                "description": "Адаптер WEBtel II ES AUX не получает данные от ИБП.",
            }
        ],
    )
    add(
        key="webtel.ups.mode",
        name="Режим работы ИБП",
        oid=".1.3.6.1.4.1.22138.1.10.1.2.0",
        delay="30s",
        valuemap="WEBtel UPS mode",
        description=(
            "upsModeStatus из WEBtel_II_ES_AUX.mib: "
            "powerOn(0), standby(1), bypass(2), onLine(3), battery(4), "
            "batteryTest(5), fault(6), ECO(7), converter(8), shutdown(9)."
        ),
        tags={"component": "status"},
        triggers=[
            {
                "id": "battery",
                "name": "WEBtel {HOST.NAME}: ИБП в автономном режиме (батарея)",
                "expression": f"last(/{TPL}/webtel.ups.mode)=4",
                "priority": "HIGH",
                "description": "ИБП питает нагрузку от батареи.",
            },
            {
                "id": "bypass",
                "name": "WEBtel {HOST.NAME}: ИБП на встроенной обводной цепи",
                "expression": f"last(/{TPL}/webtel.ups.mode)=2",
                "priority": "WARNING",
                "description": "Нагрузка питается по bypass.",
            },
            {
                "id": "alarm",
                "name": "WEBtel {HOST.NAME}: аварийный режим ИБП",
                "expression": f"last(/{TPL}/webtel.ups.mode)=6",
                "priority": "DISASTER",
            },
            {
                "id": "shutdown",
                "name": "WEBtel {HOST.NAME}: ИБП выключен",
                "expression": f"last(/{TPL}/webtel.ups.mode)=9",
                "priority": "DISASTER",
            },
        ],
    )

    # Ratings
    add(
        key="webtel.ups.model",
        name="Модель ИБП",
        oid=".1.3.6.1.4.1.22138.1.10.2.1.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        inventory="MODEL",
        description="Наименование модели ИБП.",
        tags={"component": "identity"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.rated.va",
        name="Номинальная полная мощность",
        oid=".1.3.6.1.4.1.22138.1.10.2.2.0",
        delay="1h",
        units="VA",
        description="Номинальная полная выходная мощность ИБП (ВА).",
        tags={"component": "ratings"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.rated.pf",
        name="Коэффициент мощности",
        oid=".1.3.6.1.4.1.22138.1.10.2.3.0",
        delay="1h",
        units="%",
        description="Коэффициент мощности (%).",
        tags={"component": "ratings"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.rated.vin",
        name="Номинальное входное напряжение",
        oid=".1.3.6.1.4.1.22138.1.10.2.4.0",
        delay="1h",
        units="V",
        description="Номинальное входное напряжение (В).",
        tags={"component": "ratings"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.rated.vout",
        name="Номинальное выходное напряжение",
        oid=".1.3.6.1.4.1.22138.1.10.2.5.0",
        delay="1h",
        units="V",
        description="Номинальное выходное напряжение (В). Допустимые значения записи: 200, 208, 220, 230, 240.",
        tags={"component": "ratings"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.rated.iout",
        name="Номинальный выходной ток",
        oid=".1.3.6.1.4.1.22138.1.10.2.6.0",
        delay="1h",
        units="A",
        description="Номинальный выходной ток ИБП (А).",
        tags={"component": "ratings"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.rated.freq",
        name="Номинальная частота выхода",
        oid=".1.3.6.1.4.1.22138.1.10.2.7.0",
        delay="1h",
        units="Hz",
        mul="0.1",
        description="Номинальная частота выходного напряжения, в MIB умножена на 10.",
        tags={"component": "ratings"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.rated.vbatt",
        name="Номинальное напряжение батареи",
        oid=".1.3.6.1.4.1.22138.1.10.2.8.0",
        delay="1h",
        units="V",
        mul="0.1",
        description="Номинальное напряжение батареи, в MIB умножено на 10.",
        tags={"component": "ratings"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )

    # Input measurements (x10)
    def volt(key, name, oid, extra_tags=None):
        tags = {"component": "input"}
        if extra_tags:
            tags.update(extra_tags)
        add(
            key=key,
            name=name,
            oid=oid,
            delay="30s",
            units="V",
            mul="0.1",
            description=f"{name}. Значение в MIB умножено на 10.",
            tags=tags,
        )

    def freq(key, name, oid, component):
        add(
            key=key,
            name=name,
            oid=oid,
            delay="30s",
            units="Hz",
            mul="0.1",
            description=f"{name}. Значение в MIB умножено на 10.",
            tags={"component": component},
        )

    volt("webtel.input.voltage.l1", "Входное напряжение L1 / однофазное", ".1.3.6.1.4.1.22138.1.10.3.1.1.0")
    volt("webtel.input.voltage.l2", "Входное напряжение L2", ".1.3.6.1.4.1.22138.1.10.3.1.2.0", {"phase": "3"})
    volt("webtel.input.voltage.l3", "Входное напряжение L3", ".1.3.6.1.4.1.22138.1.10.3.1.3.0", {"phase": "3"})
    volt("webtel.input.voltage.l1l2", "Входное линейное напряжение L1-L2", ".1.3.6.1.4.1.22138.1.10.3.1.4.0", {"phase": "3"})
    volt("webtel.input.voltage.l2l3", "Входное линейное напряжение L2-L3", ".1.3.6.1.4.1.22138.1.10.3.1.5.0", {"phase": "3"})
    volt("webtel.input.voltage.l3l1", "Входное линейное напряжение L3-L1", ".1.3.6.1.4.1.22138.1.10.3.1.6.0", {"phase": "3"})
    freq("webtel.input.frequency", "Частота входного напряжения", ".1.3.6.1.4.1.22138.1.10.3.1.7.0", "input")

    # Bypass 3/3
    volt("webtel.bypass.voltage.l1", "Напряжение bypass L1", ".1.3.6.1.4.1.22138.1.10.3.2.1.0", {"component": "bypass", "phase": "3"})
    volt("webtel.bypass.voltage.l2", "Напряжение bypass L2", ".1.3.6.1.4.1.22138.1.10.3.2.2.0", {"component": "bypass", "phase": "3"})
    volt("webtel.bypass.voltage.l3", "Напряжение bypass L3", ".1.3.6.1.4.1.22138.1.10.3.2.3.0", {"component": "bypass", "phase": "3"})
    volt("webtel.bypass.voltage.l1l2", "Линейное напряжение bypass L1-L2", ".1.3.6.1.4.1.22138.1.10.3.2.4.0", {"component": "bypass", "phase": "3"})
    volt("webtel.bypass.voltage.l2l3", "Линейное напряжение bypass L2-L3", ".1.3.6.1.4.1.22138.1.10.3.2.5.0", {"component": "bypass", "phase": "3"})
    volt("webtel.bypass.voltage.l3l1", "Линейное напряжение bypass L3-L1", ".1.3.6.1.4.1.22138.1.10.3.2.6.0", {"component": "bypass", "phase": "3"})
    freq("webtel.bypass.frequency", "Частота напряжения bypass", ".1.3.6.1.4.1.22138.1.10.3.2.7.0", "bypass")

    # Output
    add(
        key="webtel.output.voltage.l1",
        name="Выходное напряжение L1 / однофазное",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.1.0",
        delay="30s",
        units="V",
        mul="0.1",
        description="Для 1ф и 3/1 — выходное напряжение; для 3/3 — фаза L1. В MIB ×10.",
        tags={"component": "output"},
    )
    add(
        key="webtel.output.voltage.l2",
        name="Выходное напряжение L2",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.2.0",
        delay="30s",
        units="V",
        mul="0.1",
        description="Только 3/3. В MIB ×10.",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.voltage.l3",
        name="Выходное напряжение L3",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.3.0",
        delay="30s",
        units="V",
        mul="0.1",
        description="Только 3/3. В MIB ×10.",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.voltage.l1l2",
        name="Выходное линейное напряжение L1-L2",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.4.0",
        delay="30s",
        units="V",
        mul="0.1",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.voltage.l2l3",
        name="Выходное линейное напряжение L2-L3",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.5.0",
        delay="30s",
        units="V",
        mul="0.1",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.voltage.l3l1",
        name="Выходное линейное напряжение L3-L1",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.6.0",
        delay="30s",
        units="V",
        mul="0.1",
        tags={"component": "output", "phase": "3"},
    )
    freq("webtel.output.frequency", "Частота выходного напряжения", ".1.3.6.1.4.1.22138.1.10.3.3.7.0", "output")
    add(
        key="webtel.output.current",
        name="Выходной ток / сумма фаз L1-L3",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.8.0",
        delay="30s",
        units="A",
        mul="0.1",
        description="Для 1ф и 3/1 — выходной ток; для 3/3 — сумма токов фаз. В MIB ×10.",
        tags={"component": "output"},
    )
    add(
        key="webtel.output.current.l1",
        name="Выходной ток L1",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.9.0",
        delay="30s",
        units="A",
        mul="0.1",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.current.l2",
        name="Выходной ток L2",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.10.0",
        delay="30s",
        units="A",
        mul="0.1",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.current.l3",
        name="Выходной ток L3",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.11.0",
        delay="30s",
        units="A",
        mul="0.1",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.load",
        name="Нагрузка выхода / средняя по фазам",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.12.0",
        delay="30s",
        units="%",
        description="Для 1ф и 3/1 — нагрузка; для 3/3 — среднее по фазам L1-L3.",
        tags={"component": "output"},
        triggers=[
            {
                "id": "load.warn",
                "name": "WEBtel {HOST.NAME}: высокая нагрузка ИБП ({ITEM.LASTVALUE1})",
                "expression": f"min(/{TPL}/webtel.output.load,5m)>{{$UPS.LOAD.WARN}}",
                "priority": "WARNING",
            },
            {
                "id": "load.crit",
                "name": "WEBtel {HOST.NAME}: критическая нагрузка ИБП ({ITEM.LASTVALUE1})",
                "expression": f"min(/{TPL}/webtel.output.load,5m)>{{$UPS.LOAD.CRIT}}",
                "priority": "HIGH",
            },
        ],
    )
    add(
        key="webtel.output.load.l1",
        name="Нагрузка фазы L1",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.13.0",
        delay="30s",
        units="%",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.load.l2",
        name="Нагрузка фазы L2",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.14.0",
        delay="30s",
        units="%",
        tags={"component": "output", "phase": "3"},
    )
    add(
        key="webtel.output.load.l3",
        name="Нагрузка фазы L3",
        oid=".1.3.6.1.4.1.22138.1.10.3.3.15.0",
        delay="30s",
        units="%",
        tags={"component": "output", "phase": "3"},
    )

    # Internal
    add(
        key="webtel.ups.temperature",
        name="Температура ИБП",
        oid=".1.3.6.1.4.1.22138.1.10.3.4.1.0",
        delay="1m",
        units="°C",
        mul="0.1",
        description="Внутренняя температура ИБП. В MIB ×10.",
        tags={"component": "internal"},
        triggers=[
            {
                "id": "temp.warn",
                "name": "WEBtel {HOST.NAME}: повышенная температура ИБП ({ITEM.LASTVALUE1})",
                "expression": f"avg(/{TPL}/webtel.ups.temperature,5m)>{{$UPS.TEMP.WARN}}",
                "priority": "WARNING",
            },
            {
                "id": "temp.crit",
                "name": "WEBtel {HOST.NAME}: перегрев ИБП ({ITEM.LASTVALUE1})",
                "expression": f"avg(/{TPL}/webtel.ups.temperature,5m)>{{$UPS.TEMP.CRIT}}",
                "priority": "HIGH",
            },
        ],
    )
    add(
        key="webtel.battery.voltage",
        name="Напряжение батареи",
        oid=".1.3.6.1.4.1.22138.1.10.3.4.2.0",
        delay="30s",
        units="V",
        mul="0.1",
        description="Напряжение батареи. В MIB ×10.",
        tags={"component": "battery"},
    )
    add(
        key="webtel.battery.runtime",
        name="Прогноз времени автономии",
        oid=".1.3.6.1.4.1.22138.1.10.3.4.3.0",
        delay="1m",
        units="m",
        description="Прогнозируемое время работы от батареи (мин.). Для однофазных ИБП 1–3 кВА.",
        tags={"component": "battery"},
        triggers=[
            {
                "id": "runtime.low",
                "name": "WEBtel {HOST.NAME}: малое время автономии ({ITEM.LASTVALUE1})",
                "expression": (
                    f"last(/{TPL}/webtel.ups.mode)=4 and "
                    f"last(/{TPL}/webtel.battery.runtime)<{{$UPS.RUNTIME.MIN}}"
                ),
                "priority": "HIGH",
                "description": "Срабатывает только в автономном режиме.",
            }
        ],
    )
    add(
        key="webtel.battery.charge",
        name="Уровень заряда батареи",
        oid=".1.3.6.1.4.1.22138.1.10.3.4.4.0",
        delay="1m",
        units="%",
        description="Текущий уровень заряда батареи (%).",
        tags={"component": "battery"},
        triggers=[
            {
                "id": "charge.low",
                "name": "WEBtel {HOST.NAME}: низкий заряд батареи ({ITEM.LASTVALUE1})",
                "expression": f"last(/{TPL}/webtel.battery.charge)<{{$UPS.BATTERY.MIN}}",
                "priority": "HIGH",
            }
        ],
    )
    add(
        key="webtel.ups.warnings",
        name="Предупреждения ИБП (upsWanrings)",
        oid=".1.3.6.1.4.1.22138.1.10.3.4.5.0",
        delay="30s",
        value_type="TEXT",
        trends="0",
        history="30d",
        description=(
            "В MIB объект upsWanrings — DisplayString (64 бита предупреждений как строка), "
            "не INTEGER. Расшифровка битов — таблица 17 руководства КСДП.00080-10."
        ),
        tags={"component": "status"},
        triggers=[
            {
                "id": "warnings",
                "name": "WEBtel {HOST.NAME}: есть предупреждения ИБП ({ITEM.LASTVALUE1})",
                "expression": (
                    f"length(last(/{TPL}/webtel.ups.warnings))>0 and "
                    f"last(/{TPL}/webtel.ups.warnings)<>\"0\" and "
                    f"last(/{TPL}/webtel.ups.warnings)<>\"00\""
                ),
                "priority": "WARNING",
            }
        ],
    )
    add(
        key="webtel.ups.fault.code",
        name="Код неисправности (аварии)",
        oid=".1.3.6.1.4.1.22138.1.10.3.4.6.0",
        delay="30s",
        valuemap="WEBtel UPS fault code",
        description="Код текущей аварии. Значения — таблица 18 руководства (HEX в десятичном виде).",
        tags={"component": "status"},
        triggers=[
            {
                "id": "fault",
                "name": "WEBtel {HOST.NAME}: авария ИБП, код {ITEM.LASTVALUE1}",
                "expression": f"last(/{TPL}/webtel.ups.fault.code)<>0",
                "priority": "DISASTER",
            }
        ],
    )

    # Sensors TS-100D / HTS-100D
    add(
        key="webtel.sensor.ts100d.name",
        name="Имя датчика TS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.1.1.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        tags={"component": "sensor"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.sensor.ts100d.temperature",
        name="Температура датчика TS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.1.2.0",
        delay="1m",
        units="°C",
        mul="0.1",
        description="Температура TS-100D. В MIB ×10. Без датчика элемент может стать unsupported.",
        tags={"component": "sensor"},
    )
    add(
        key="webtel.sensor.ts100d.status",
        name="Статус датчика TS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.1.3.0",
        delay="1m",
        valuemap="WEBtel sensor status",
        tags={"component": "sensor"},
        triggers=[
            {
                "id": "ts100d.alarm",
                "name": "WEBtel {HOST.NAME}: авария температуры TS-100D",
                "expression": f"last(/{TPL}/webtel.sensor.ts100d.status)=1 or last(/{TPL}/webtel.sensor.ts100d.status)=2",
                "priority": "WARNING",
            }
        ],
    )
    add(
        key="webtel.sensor.hts100d.name",
        name="Имя датчика влажности HTS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.2.1.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        tags={"component": "sensor"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.sensor.hts100d.humidity",
        name="Влажность датчика HTS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.2.2.0",
        delay="1m",
        units="%",
        mul="0.1",
        description="Относительная влажность HTS-100D. В MIB ×10.",
        tags={"component": "sensor"},
    )
    add(
        key="webtel.sensor.hts100d.humidity.status",
        name="Статус влажности HTS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.2.3.0",
        delay="1m",
        valuemap="WEBtel sensor status",
        tags={"component": "sensor"},
        triggers=[
            {
                "id": "hts.hum.alarm",
                "name": "WEBtel {HOST.NAME}: авария влажности HTS-100D",
                "expression": (
                    f"last(/{TPL}/webtel.sensor.hts100d.humidity.status)=1 or "
                    f"last(/{TPL}/webtel.sensor.hts100d.humidity.status)=2"
                ),
                "priority": "WARNING",
            }
        ],
    )
    add(
        key="webtel.sensor.hts100d.temp.name",
        name="Имя датчика температуры HTS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.2.8.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        tags={"component": "sensor"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.sensor.hts100d.temperature",
        name="Температура датчика HTS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.2.9.0",
        delay="1m",
        units="°C",
        mul="0.1",
        tags={"component": "sensor"},
    )
    add(
        key="webtel.sensor.hts100d.temp.status",
        name="Статус температуры HTS-100D",
        oid=".1.3.6.1.4.1.22138.1.10.4.4.2.10.0",
        delay="1m",
        valuemap="WEBtel sensor status",
        tags={"component": "sensor"},
        triggers=[
            {
                "id": "hts.temp.alarm",
                "name": "WEBtel {HOST.NAME}: авария температуры HTS-100D",
                "expression": (
                    f"last(/{TPL}/webtel.sensor.hts100d.temp.status)=1 or "
                    f"last(/{TPL}/webtel.sensor.hts100d.temp.status)=2"
                ),
                "priority": "WARNING",
            }
        ],
    )

    # Discrete inputs MDS-4
    for i in range(4):
        add(
            key=f"webtel.din{i + 1}.name",
            name=f"Имя дискретного входа {i + 1}",
            oid=f".1.3.6.1.4.1.22138.1.10.4.4.3.1.2.{i}",
            delay="1h",
            value_type="CHAR",
            trends="0",
            history="7d",
            tags={"component": "discrete"},
            preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
        )
        add(
            key=f"webtel.din{i + 1}.status",
            name=f"Статус дискретного входа {i + 1}",
            oid=f".1.3.6.1.4.1.22138.1.10.4.4.3.1.3.{i}",
            delay="30s",
            valuemap="WEBtel discrete input",
            description="0 — норма, 1 — авария, 3 — отключен. Модуль MDS-4.",
            tags={"component": "discrete"},
            triggers=[
                {
                    "id": f"din{i + 1}.alarm",
                    "name": f"WEBtel {{HOST.NAME}}: авария дискретного входа {i + 1}",
                    "expression": f"last(/{TPL}/webtel.din{i + 1}.status)=1",
                    "priority": "HIGH",
                }
            ],
        )

    # Relays MRS-4
    for i in range(4):
        add(
            key=f"webtel.relay{i + 1}.state",
            name=f"Состояние релейного выхода {i + 1}",
            oid=f".1.3.6.1.4.1.22138.1.10.4.4.4.1.3.{i}",
            delay="1m",
            valuemap="WEBtel relay state",
            description="0 — выключен, 1 — включен, 3 — отключен. Модуль MRS-4.",
            tags={"component": "relay"},
        )

    # Adapter identity
    add(
        key="webtel.adapter.date",
        name="Дата адаптера",
        oid=".1.3.6.1.4.1.22138.1.10.5.1.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        description='Текущая дата адаптера в формате "ДД.ММ.ГГ".',
        tags={"component": "system"},
    )
    add(
        key="webtel.adapter.time",
        name="Время адаптера",
        oid=".1.3.6.1.4.1.22138.1.10.5.2.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        description='Текущее время адаптера в формате "ЧЧ.ММ.СС".',
        tags={"component": "system"},
    )
    add(
        key="webtel.trap.text",
        name="Текст SNMP-ловушки",
        oid=".1.3.6.1.4.1.22138.1.10.7.1.0",
        delay="1m",
        value_type="TEXT",
        trends="0",
        history="7d",
        description="Текст последней SNMP-ловушки (если адаптер отдаёт переменную по GET).",
        tags={"component": "status"},
    )
    add(
        key="webtel.trap.severity",
        name="Важность SNMP-ловушки",
        oid=".1.3.6.1.4.1.22138.1.10.7.2.0",
        delay="1m",
        valuemap="WEBtel trap severity",
        description="Уровень важности ловушки.",
        tags={"component": "status"},
    )
    add(
        key="webtel.adapter.firmware",
        name="Имя изделия / версия ПО адаптера",
        oid=".1.3.6.1.4.1.22138.1.10.8.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        inventory="OS_FULL",
        tags={"component": "identity"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.adapter.serial",
        name="Заводской номер адаптера",
        oid=".1.3.6.1.4.1.22138.1.10.9.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        inventory="SERIALNO_A",
        tags={"component": "identity"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )
    add(
        key="webtel.ups.serial",
        name="Заводской номер ИБП",
        oid=".1.3.6.1.4.1.22138.1.10.10.0",
        delay="1h",
        value_type="CHAR",
        trends="0",
        history="7d",
        inventory="SERIALNO_B",
        tags={"component": "identity"},
        preprocess=[{"type": "DISCARD_UNCHANGED_HEARTBEAT", "parameters": ["1d"]}],
    )

    return d


VALUEMAPS = {
    "WEBtel UPS connection": [("0", "Не подключен"), ("1", "Подключен")],
    "WEBtel UPS mode": [
        ("0", "Включен"),
        ("1", "Режим ожидания"),
        ("2", "Работа по встроенной обводной цепи"),
        ("3", "Дежурный режим"),
        ("4", "Автономный режим"),
        ("5", "Тестирование батареи"),
        ("6", "Аварийный режим"),
        ("7", "Режим экономии энергии"),
        ("8", "Режим преобразователя частоты"),
        ("9", "Выключен"),
    ],
    "WEBtel sensor status": [
        ("0", "В норме"),
        ("1", "Низкое значение"),
        ("2", "Высокое значение"),
        ("3", "Датчик отключен"),
    ],
    "WEBtel discrete input": [
        ("0", "Норма"),
        ("1", "Авария"),
        ("3", "Отключен"),
    ],
    "WEBtel relay state": [
        ("0", "Выключен"),
        ("1", "Включен"),
        ("3", "Отключен"),
    ],
    "WEBtel trap severity": [
        ("0", "Извещение"),
        ("1", "Предупреждение"),
        ("2", "Авария"),
    ],
    "WEBtel UPS fault code": [
        ("0", "Нет аварии"),
        ("1", "Ошибка запуска внутренней шины"),
        ("2", "Недопустимое повышение напряжения на внутренней шине"),
        ("3", "Недопустимое понижение напряжения на внутренней шине"),
        ("4", "Нестабильное напряжение на внутренней шине"),
        ("5", "Короткое замыкание на внутренней шине"),
        ("6", "Перегрузка по току в ККМ"),
        ("17", "Программный сбой в инверторе"),
        ("18", "Недопустимое повышение выходного напряжения инвертора"),
        ("19", "Недопустимое понижение выходного напряжения инвертора"),
        ("20", "КЗ фазы L1 инвертора"),
        ("21", "КЗ фазы L2 инвертора"),
        ("22", "КЗ фазы L3 инвертора"),
        ("23", "КЗ L1 на L2 инвертора"),
        ("24", "КЗ L2 на L3 инвертора"),
        ("25", "КЗ L1 на L3 инвертора"),
        ("26", "Возвратная мощность фаза L1"),
        ("27", "Возвратная мощность фаза L2"),
        ("28", "Возвратная мощность фаза L3"),
        ("33", "Неисправность модуля SCR батареи"),
        ("34", "Неисправность модуля SCR входа"),
        ("35", "Реле инвертора не включается"),
        ("36", "Сваривание контактов реле инвертора"),
        ("37", "Неисправность внутренней проводки"),
        ("38", "Неверная полярность батареи"),
        ("39", "Чрезмерно высокое напряжение батареи"),
        ("40", "Чрезмерно низкое напряжение батареи"),
        ("49", "Нарушение связи по CAN"),
        ("50", "Неисправность цепи управления"),
        ("51", "Неисправность цепи синхронизации"),
        ("52", "Неисправность формирователя синхроимпульсов"),
        ("53", "Нарушение связи"),
        ("54", "Неисправна выходная цепь"),
        ("65", "Отключение из-за перегрева"),
        ("66", "Нарушение связи с управляющим контроллером"),
        ("67", "Отключение из-за перегрузки"),
        ("68", "Отключение из-за неисправности вентилятора"),
        ("69", "Отключение из-за неисправности зарядного устройства"),
    ],
}

MACROS = [
    ("{$UPS.BATTERY.MIN}", "20", "Минимальный допустимый заряд батареи, %"),
    ("{$UPS.LOAD.WARN}", "80", "Порог предупреждения по нагрузке, %"),
    ("{$UPS.LOAD.CRIT}", "95", "Порог аварии по нагрузке, %"),
    ("{$UPS.TEMP.WARN}", "40", "Порог предупреждения по температуре ИБП, °C"),
    ("{$UPS.TEMP.CRIT}", "55", "Порог аварии по температуре ИБП, °C"),
    ("{$UPS.RUNTIME.MIN}", "10", "Минимальное время автономии в минутах (только в режиме батареи)"),
]

GRAPHS = [
    {
        "name": "WEBtel: напряжение входа и выхода",
        "items": [
            ("webtel.input.voltage.l1", "1A7C11"),
            ("webtel.output.voltage.l1", "2774A4"),
        ],
    },
    {
        "name": "WEBtel: батарея",
        "items": [
            ("webtel.battery.voltage", "F63100"),
            ("webtel.battery.charge", "2774A4"),
        ],
    },
    {
        "name": "WEBtel: нагрузка и ток",
        "items": [
            ("webtel.output.load", "F63100"),
            ("webtel.output.current", "1A7C11"),
        ],
    },
    {
        "name": "WEBtel: температура",
        "items": [
            ("webtel.ups.temperature", "F63100"),
            ("webtel.sensor.ts100d.temperature", "2774A4"),
            ("webtel.sensor.hts100d.temperature", "1A7C11"),
        ],
    },
    {
        "name": "WEBtel: частоты",
        "items": [
            ("webtel.input.frequency", "1A7C11"),
            ("webtel.output.frequency", "2774A4"),
        ],
    },
]


def build_xml(catalog: list[dict]) -> str:
    root = Element("zabbix_export")
    et_text(root, "version", ZBX_VERSION)
    et_text(root, "date", DATE)

    groups = SubElement(root, "groups")
    group = SubElement(groups, "group")
    et_text(group, "name", GROUP)

    templates = SubElement(root, "templates")
    tpl = SubElement(templates, "template")
    et_text(tpl, "template", TPL)
    et_text(tpl, "name", TPL)
    et_text(
        tpl,
        "description",
        "Шаблон SNMP для WEB/SNMP-адаптера АТС-КОНВЕРС WEBtel II ES AUX "
        "(ИБП EcoPower / OnePower Pro).\n\n"
        "Формат: Zabbix 5.0 XML (подходит для 5.0.8).\n"
        "Протокол адаптера: SNMP v1, enterprise OID 1.3.6.1.4.1.22138.1.10.\n"
        "Источник OID: файл WEBtel_II_ES_AUX.mib.\n\n"
        "На узле создайте SNMP-интерфейс версии SNMPv1 (адаптер не поддерживает v2c/v3) "
        "и community, настроенный на странице SNMP адаптера (по умолчанию обычно public).\n\n"
        "Трёхфазные OID на однофазном ИБП станут unsupported — это нормально.\n"
        "Датчики TS-100D/HTS-100D и модули MDS-4/MRS-4 тоже могут быть unsupported, "
        "если оборудование не подключено.",
    )

    tgroups = SubElement(tpl, "groups")
    tg = SubElement(tgroups, "group")
    et_text(tg, "name", GROUP)

    apps = SubElement(tpl, "applications")
    for name in sorted(set(APP_BY_COMPONENT.values())):
        app = SubElement(apps, "application")
        et_text(app, "name", name)

    items_el = SubElement(tpl, "items")
    for it in catalog:
        item = SubElement(items_el, "item")
        et_text(item, "name", it["name"])
        et_text(item, "type", "SNMP_AGENT")
        et_text(item, "snmp_oid", it["oid"])
        et_text(item, "key", it["key"])
        et_text(item, "delay", it.get("delay", "1m"))
        if "history" in it:
            et_text(item, "history", it["history"])
        if "trends" in it:
            et_text(item, "trends", it["trends"])
        value_type = it.get("value_type")
        if it.get("mul"):
            value_type = "FLOAT"
        if value_type:
            et_text(item, "value_type", value_type)
        if "units" in it:
            et_text(item, "units", it["units"])
        if "inventory" in it:
            et_text(item, "inventory_link", it["inventory"])
        if "description" in it:
            et_text(item, "description", it["description"])

        steps = list(it.get("preprocess", []))
        if it.get("mul"):
            steps.insert(0, {"type": "MULTIPLIER", "parameters": [it["mul"]]})
        if steps:
            add_preprocessing(item, steps)
        if "valuemap" in it:
            add_valuemap_ref(item, it["valuemap"])

        applications = SubElement(item, "applications")
        application = SubElement(applications, "application")
        et_text(application, "name", app_name(it.get("tags")))

        if it.get("triggers"):
            trigs = SubElement(item, "triggers")
            for tr in it["triggers"]:
                t = SubElement(trigs, "trigger")
                et_text(t, "expression", to_classic_expr(tr["expression"]))
                et_text(t, "name", tr["name"])
                if "description" in tr:
                    et_text(t, "description", tr["description"])
                et_text(t, "priority", tr["priority"])
                et_text(t, "manual_close", "YES")

    add_tags(tpl, {"class": "hardware", "target": "ups", "vendor": "ATS-CONVERS"})

    macros_el = SubElement(tpl, "macros")
    for name, value, descr in MACROS:
        m = SubElement(macros_el, "macro")
        et_text(m, "macro", name)
        et_text(m, "value", value)
        et_text(m, "description", descr)

    graphs_el = SubElement(tpl, "graphs")
    for g in GRAPHS:
        ge = SubElement(graphs_el, "graph")
        et_text(ge, "name", g["name"])
        gis = SubElement(ge, "graph_items")
        for idx, (key, color) in enumerate(g["items"]):
            gi = SubElement(gis, "graph_item")
            et_text(gi, "sortorder", str(idx))
            et_text(gi, "color", color)
            if idx == 1 and "батарея" in g["name"]:
                et_text(gi, "yaxisside", "RIGHT")
            if idx == 0 and "нагрузка" in g["name"]:
                et_text(gi, "yaxisside", "LEFT")
            if idx == 1 and "нагрузка" in g["name"]:
                et_text(gi, "yaxisside", "RIGHT")
            itref = SubElement(gi, "item")
            et_text(itref, "host", TPL)
            et_text(itref, "key", key)

    vmaps = SubElement(root, "value_maps")
    for name, mappings in VALUEMAPS.items():
        vm = SubElement(vmaps, "value_map")
        et_text(vm, "name", name)
        maps = SubElement(vm, "mappings")
        for value, newvalue in mappings:
            mp = SubElement(maps, "mapping")
            et_text(mp, "value", value)
            et_text(mp, "newvalue", newvalue)

    xml_bytes = tostring(root, encoding="utf-8")
    parsed = minidom.parseString(xml_bytes)
    pretty = parsed.toprettyxml(indent="    ", encoding="UTF-8").decode("utf-8")
    if pretty.startswith("<?xml"):
        return pretty
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + pretty


MIB = r'''UPS-WEBTEL-II-ES-AUX-MIB DEFINITIONS ::= BEGIN

-- Reconstructed from ATS-CONVERS user manual KSDP.00080-10 table 16
-- for WEB/SNMP adapter WEBtel II ES AUX.
-- Enterprise number 22138 = ATS-KONVERS Ltd. (IANA PEN).
-- This MIB is for snmptranslate / documentation. Zabbix cannot import MIB
-- files as templates; use the XML template in zabbix/.

IMPORTS
    MODULE-IDENTITY, OBJECT-TYPE, enterprises, Integer32, Gauge32
        FROM SNMPv2-SMI
    DisplayString
        FROM SNMPv2-TC;

atsConvers MODULE-IDENTITY
    LAST-UPDATED "202609070000Z"
    ORGANIZATION "ATS-KONVERS Ltd."
    CONTACT-INFO "http://www.atsconvers.ru"
    DESCRIPTION
        "Private MIB for WEBtel II ES AUX SNMP adapter
         (EcoPower / OnePower Pro UPS)."
    ::= { enterprises 22138 }

products OBJECT IDENTIFIER ::= { atsConvers 1 }
webtelIiEsAux OBJECT IDENTIFIER ::= { products 10 }

status OBJECT IDENTIFIER ::= { webtelIiEsAux 1 }
ratings OBJECT IDENTIFIER ::= { webtelIiEsAux 2 }
measurements OBJECT IDENTIFIER ::= { webtelIiEsAux 3 }
configuration OBJECT IDENTIFIER ::= { webtelIiEsAux 4 }
adapterConfig OBJECT IDENTIFIER ::= { webtelIiEsAux 5 }
trapArgs OBJECT IDENTIFIER ::= { webtelIiEsAux 6 }
traps OBJECT IDENTIFIER ::= { webtelIiEsAux 7 }

webtelConnected OBJECT-TYPE
    SYNTAX INTEGER { disconnected(0), connected(1) }
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "WEBtel to UPS connection status."
    ::= { status 1 }

webtelUpsMode OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION
        "UPS operating mode. Manual lists: PowerOn, Standby, Bypass,
         Online, Battery, BatteryTest, Alarm, ECO, Converter, Shutdown."
    ::= { status 2 }

upsModel OBJECT-TYPE
    SYNTAX DisplayString
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "UPS model name."
    ::= { ratings 1 }

upsRatedVA OBJECT-TYPE
    SYNTAX Gauge32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Rated output apparent power, VA."
    ::= { ratings 2 }

upsPowerFactor OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Power factor, percent."
    ::= { ratings 3 }

upsRatedVin OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Rated input voltage, V."
    ::= { ratings 4 }

upsRatedVout OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-write
    STATUS current
    DESCRIPTION "Rated output voltage, V (200/208/220/230/240)."
    ::= { ratings 5 }

upsRatedIout OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Rated output current, A."
    ::= { ratings 6 }

upsRatedFreq OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-write
    STATUS current
    DESCRIPTION "Rated output frequency, 0.1 Hz (500 or 600)."
    ::= { ratings 7 }

upsRatedVbatt OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Rated battery voltage, 0.1 V."
    ::= { ratings 8 }

measInput OBJECT IDENTIFIER ::= { measurements 1 }
measBypass OBJECT IDENTIFIER ::= { measurements 2 }
measOutput OBJECT IDENTIFIER ::= { measurements 3 }
measInternal OBJECT IDENTIFIER ::= { measurements 4 }

inputVoltageL1 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Input voltage L1 or single-phase, 0.1 V."
    ::= { measInput 1 }

inputVoltageL2 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Input voltage L2, 0.1 V (3-phase)."
    ::= { measInput 2 }

inputVoltageL3 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Input voltage L3, 0.1 V (3-phase)."
    ::= { measInput 3 }

inputVoltageL1L2 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Input line voltage L1-L2, 0.1 V."
    ::= { measInput 4 }

inputVoltageL2L3 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Input line voltage L2-L3, 0.1 V."
    ::= { measInput 5 }

inputVoltageL3L1 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Input line voltage L3-L1, 0.1 V."
    ::= { measInput 6 }

inputFrequency OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Input frequency, 0.1 Hz."
    ::= { measInput 7 }

outputVoltageL1 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Output voltage L1 or single-phase, 0.1 V."
    ::= { measOutput 1 }

outputVoltageL2 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Output voltage L2, 0.1 V."
    ::= { measOutput 2 }

outputVoltageL3 OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Output voltage L3, 0.1 V."
    ::= { measOutput 3 }

outputFrequency OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Output frequency, 0.1 Hz."
    ::= { measOutput 7 }

outputCurrent OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Output current or sum of phases, 0.1 A."
    ::= { measOutput 8 }

outputLoad OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Output load percent."
    ::= { measOutput 12 }

upsTemperature OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "UPS temperature, 0.1 C."
    ::= { measInternal 1 }

batteryVoltage OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Battery voltage, 0.1 V."
    ::= { measInternal 2 }

batteryRuntime OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Estimated battery runtime, minutes."
    ::= { measInternal 3 }

batteryCharge OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Battery charge percent."
    ::= { measInternal 4 }

warningRegister OBJECT-TYPE
    SYNTAX Gauge32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "64-bit warning register (see manual table 17)."
    ::= { measInternal 5 }

faultCode OBJECT-TYPE
    SYNTAX Integer32
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "Current fault code (see manual table 18)."
    ::= { measInternal 6 }

webtelFirmware OBJECT-TYPE
    SYNTAX DisplayString
    MAX-ACCESS read-only
    STATUS current
    DESCRIPTION "WEBtel adapter firmware version."
    ::= { webtelIiEsAux 8 }

adapterSerial OBJECT-TYPE
    SYNTAX DisplayString
    MAX-ACCESS read-write
    STATUS current
    DESCRIPTION "WEBtel adapter serial number."
    ::= { webtelIiEsAux 9 }

upsSerial OBJECT-TYPE
    SYNTAX DisplayString
    MAX-ACCESS read-write
    STATUS current
    DESCRIPTION "UPS serial number."
    ::= { webtelIiEsAux 10 }

END
'''


README = r'''# Шаблон Zabbix 5.0 для WEBtel II ES AUX

MIB-файл из архива `WEBtel_II_ES_AUX_mib.zip` **нельзя импортировать в Zabbix**.
Это SNMP MIB (описание OID для `snmptranslate` / HP OpenView / Power Net Agent),
а не шаблон мониторинга. Поэтому «просто загрузить mib» в Zabbix не получится.

В этом репозитории:

| Файл | Назначение |
| --- | --- |
| `zabbix/zbx_webtel_ii_es_aux_5.0.xml` | Шаблон для импорта в **Zabbix 5.0.x** (в т.ч. 5.0.8) |
| `zabbix/zbx_webtel_ii_es_aux_5.0.xml.zip` | XML + оригинальный MIB + README |
| `mibs/WEBtel_II_ES_AUX.mib` | Оригинальный MIB АТС-КОНВЕРС (не импортируется в Zabbix) |
| `docs/oids.md` | Краткая таблица OID для `snmpget` |

XML собран по файлу `WEBtel_II_ES_AUX.mib` (модуль `WEBTEL_II_ES_AUX-MIB`,
enterprise `1.3.6.1.4.1.22138`, продукт `webtel_ii_es_aux` = `.1.10`).

Формат: **Zabbix 5.0**. На 5.0.8 файл с `<version>5.4</version>` даёт ошибку
«неподдерживаемый номер версии».

## Как импортировать в Zabbix 5.0.8

1. **Configuration → Templates → Import**.
2. Выберите `zabbix/zbx_webtel_ii_es_aux_5.0.xml` (если скачали zip — сначала распакуйте, импортируется именно XML, не zip и не `.mib`).
3. Правила импорта оставьте по умолчанию (Create new / Update existing).
4. Нажмите **Import**. Должен появиться шаблон `UPS WEBtel II ES AUX SNMP`
   в группе `Templates/Power`.

## Как повесить на ИБП

1. **Configuration → Hosts → Create host**.
2. Имя узла — любое.
3. Группы — свои.
4. **Interfaces**: добавьте **SNMP**.
   - IP адаптера WEBtel (по умолчанию часто `192.168.1.254`).
   - Порт `161`.
   - **SNMP version: SNMPv1** — адаптер поддерживает только v1.
   - Community — как на странице «Настройка SNMP» адаптера
     (часто `public` на чтение).
5. Вкладка **Templates** → свяжите `UPS WEBtel II ES AUX SNMP`.
6. Сохраните. Через минуту в **Latest data** должны появиться напряжение,
   режим, заряд батареи.

Проверка с сервера Zabbix:

```bash
snmpget -v1 -c public 192.168.1.254 .1.3.6.1.4.1.22138.1.10.1.1.0
snmpget -v1 -c public 192.168.1.254 .1.3.6.1.4.1.22138.1.10.2.1.0
```

Первый OID — связь с ИБП (`0/1`), второй — модель.

## Что мониторит шаблон

- Связь адаптера с ИБП и режим работы.
- Вход/выход: напряжение, ток, частота, нагрузка (1ф и 3ф).
- Батарея: напряжение, заряд, прогноз автономии.
- Температура ИБП, регистр предупреждений, код аварии.
- Датчики TS-100D / HTS-100D и дискретные входы MDS-4, реле MRS-4
  (если модулей нет, элементы будут `Not supported` — это нормально).
- Триггеры: нет связи с ИБП, батарея, bypass, авария, выключение,
  низкий заряд, высокая нагрузка, перегрев.

Макросы на шаблоне/узле:

- `{$UPS.BATTERY.MIN}` — заряд, % (по умолчанию 20)
- `{$UPS.LOAD.WARN}` / `{$UPS.LOAD.CRIT}` — нагрузка 80 / 95 %
- `{$UPS.TEMP.WARN}` / `{$UPS.TEMP.CRIT}` — температура 40 / 55 °C
- `{$UPS.RUNTIME.MIN}` — минуты автономии (10)

## Карта режимов ИБП

Из `upsModeStatus` в `WEBtel_II_ES_AUX.mib` (это уже не догадка):

| Значение | MIB | Смысл |
| --- | --- | --- |
| 0 | powerOnMode | Включен |
| 1 | standbyMode | Ожидание |
| 2 | bypassMode | Обводная цепь |
| 3 | onLineMode | Дежурный режим |
| 4 | batteryMode | Автономный режим |
| 5 | batteryTestMode | Тест батареи |
| 6 | faultMode | Авария |
| 7 | eCOMode | ECO |
| 8 | converterMode | Преобразователь частоты |
| 9 | shutdownMode | Выключен |

## Зачем тогда MIB

MIB нужен net-snmp и другим SNMP-браузерам, чтобы видеть имена вместо цифр:

```bash
sudo cp mibs/UPS-WEBTEL-II-ES-AUX.mib /usr/share/snmp/mibs/
snmptranslate -IR -On UPS-WEBTEL-II-ES-AUX-MIB::webtelConnected
```

На работу XML-шаблона MIB на сервере Zabbix **не обязателен**: в шаблоне
стоят числовые OID.
'''


OIDS_MD = r'''# OID WEBtel II ES AUX

Источник: руководство КСДП.00080-10, таблица 16.
Корень: `.1.3.6.1.4.1.22138.1.10` (`ATS-convers.products.webtel_ii_es_aux`).

Значения с пометкой ×10 в MIB нужно делить на 10 (в шаблоне Zabbix это уже сделано preprocessing).

| OID | Описание | Доступ |
| --- | --- | --- |
| `.1.3.6.1.2.1.1.6.0` | Расположение адаптера | RW |
| `.1.3.6.1.4.1.22138.1.10.1.1.0` | Связь с ИБП (0/1) | RO |
| `.1.3.6.1.4.1.22138.1.10.1.2.0` | Режим работы ИБП | RO |
| `.1.3.6.1.4.1.22138.1.10.2.1.0` | Модель ИБП | RO |
| `.1.3.6.1.4.1.22138.1.10.2.2.0` | Номинальная мощность, ВА | RO |
| `.1.3.6.1.4.1.22138.1.10.2.3.0` | Коэффициент мощности, % | RO |
| `.1.3.6.1.4.1.22138.1.10.2.4.0` | Номинальное Uвх, В | RO |
| `.1.3.6.1.4.1.22138.1.10.2.5.0` | Номинальное Uвых, В | RW |
| `.1.3.6.1.4.1.22138.1.10.2.6.0` | Номинальный Iвых, А | RO |
| `.1.3.6.1.4.1.22138.1.10.2.7.0` | Номинальная частота ×10 | RW |
| `.1.3.6.1.4.1.22138.1.10.2.8.0` | Номинальное U батареи ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.1.1.0` | Uвх L1 / 1ф ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.1.7.0` | Fвх ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.3.1.0` | Uвых L1 / 1ф ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.3.7.0` | Fвых ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.3.8.0` | Iвых ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.3.12.0` | Нагрузка, % | RO |
| `.1.3.6.1.4.1.22138.1.10.3.4.1.0` | Температура ИБП ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.4.2.0` | U батареи ×10 | RO |
| `.1.3.6.1.4.1.22138.1.10.3.4.3.0` | Время автономии, мин | RO |
| `.1.3.6.1.4.1.22138.1.10.3.4.4.0` | Заряд батареи, % | RO |
| `.1.3.6.1.4.1.22138.1.10.3.4.5.0` | Регистр предупреждений | RO |
| `.1.3.6.1.4.1.22138.1.10.3.4.6.0` | Код аварии | RO |
| `.1.3.6.1.4.1.22138.1.10.8.0` | Версия ПО адаптера | RO |
| `.1.3.6.1.4.1.22138.1.10.9.0` | Серийный номер адаптера | RW |
| `.1.3.6.1.4.1.22138.1.10.10.0` | Серийный номер ИБП | RW |
'''


def validate(catalog: list[dict], xml_text: str) -> None:
    from xml.etree.ElementTree import fromstring

    tree = fromstring(xml_text)
    assert tree.findtext("version") == "5.0"
    assert not tree.findall(".//uuid"), "5.0 XML must not contain uuid"
    keys = {it["key"] for it in catalog}
    for it in catalog:
        assert it["oid"].startswith(".")
        assert it["key"]
    for g in GRAPHS:
        for key, _color in g["items"]:
            assert key in keys, key
    expr = tree.findtext(".//triggers/trigger/expression")
    assert expr and expr.startswith("{") and "last(/" not in (tree.findtext(".//triggers/trigger/expression") or "")
    print(f"OK: {len(catalog)} items, version 5.0")


def main() -> None:
    catalog = items()
    xml_text = build_xml(catalog)
    validate(catalog, xml_text)

    xml_path = ROOT / "zabbix" / "zbx_webtel_ii_es_aux_5.0.xml"
    mib_path = ROOT / "mibs" / "UPS-WEBTEL-II-ES-AUX.mib"
    readme_path = ROOT / "README.md"
    oids_path = ROOT / "docs" / "oids.md"

    xml_path.write_text(xml_text, encoding="utf-8")
    mib_path.write_text(MIB.lstrip("\n") + "\n", encoding="utf-8")
    readme_path.write_text(README.lstrip("\n"), encoding="utf-8")
    oids_path.write_text(OIDS_MD.lstrip("\n"), encoding="utf-8")

    import zipfile

    zip_path = ROOT / "zabbix" / "zbx_webtel_ii_es_aux_5.0.xml.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(xml_path, arcname=xml_path.name)
        orig_mib = ROOT / "mibs" / "WEBtel_II_ES_AUX.mib"
        if orig_mib.exists():
            zf.write(orig_mib, arcname=orig_mib.name)
        else:
            zf.write(mib_path, arcname=mib_path.name)
        zf.write(oids_path, arcname="oids.md")
        zf.write(readme_path, arcname="README.md")
    print(f"wrote {xml_path} ({xml_path.stat().st_size} bytes)")
    print(f"wrote {mib_path}")
    print(f"wrote {zip_path}")


if __name__ == "__main__":
    main()
