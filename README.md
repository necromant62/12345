# Шаблон Zabbix 5.4 для WEBtel II ES AUX

MIB-файл из архива `WEBtel_II_ES_AUX_mib.zip` **нельзя импортировать в Zabbix**.
Это SNMP MIB (описание OID для `snmptranslate` / HP OpenView / Power Net Agent),
а не шаблон мониторинга. Поэтому на Zabbix 5.4 «просто загрузить mib» не получится.

В этом репозитории:

| Файл | Назначение |
| --- | --- |
| `zabbix/zbx_webtel_ii_es_aux_5.4.xml` | Шаблон для импорта в **Zabbix 5.4** (XML) |
| `zabbix/zbx_webtel_ii_es_aux_5.4.xml.zip` | Тот же шаблон + MIB + README одним архивом |
| `mibs/UPS-WEBTEL-II-ES-AUX.mib` | Восстановленный MIB по руководству КСДП.00080-10 |
| `docs/oids.md` | Таблица OID для проверки `snmpget` |

OID взяты из официального руководства АТС-КОНВЕРС
[WEBtel II ES AUX](https://www.atsconvers.ru/media/dir/pdf/webteliiesaux.pdf),
таблица 16. Enterprise: `1.3.6.1.4.1.22138` (ATS-KONVERS Ltd.).

## Как импортировать в Zabbix 5.4

1. **Configuration → Templates → Import**.
2. Выберите `zabbix/zbx_webtel_ii_es_aux_5.4.xml` (если скачали zip — сначала распакуйте, импортируется именно XML, не zip).
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

В руководстве режимы перечислены без чисел. В шаблоне принята нумерация
0..9 в том же порядке, что и в веб-интерфейсе адаптера
(как у соседнего адаптера WEBtel II RS, где режимы явно пронумерованы).

Если подписи в Latest data не совпадают с экраном ИБП, сделайте
`snmpget` OID `.1.3.6.1.4.1.22138.1.10.1.2.0` в каждом режиме и поправьте
**Value mapping** `WEBtel UPS mode`.

## Зачем тогда MIB

MIB нужен net-snmp и другим SNMP-браузерам, чтобы видеть имена вместо цифр:

```bash
sudo cp mibs/UPS-WEBTEL-II-ES-AUX.mib /usr/share/snmp/mibs/
snmptranslate -IR -On UPS-WEBTEL-II-ES-AUX-MIB::webtelConnected
```

На работу XML-шаблона MIB на сервере Zabbix **не обязателен**: в шаблоне
стоят числовые OID.
