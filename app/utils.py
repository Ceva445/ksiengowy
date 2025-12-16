import re


OCR_QTY_MAP = {
    "I": "1",
    "l": "1",
    "!": "1",
    "§": "5",
    "s": "5",
    "S": "5",
    "O": "0",
}

def normalize_qty(val: str) -> str:
    if not val:
        return ""

    val = val.strip()
    for k, v in OCR_QTY_MAP.items():
        val = val.replace(k, v)

    val = re.sub(r"\D", "", val)
    return val

def normalize_code(code: str) -> str:
    return code.replace(" ", "")


def find(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not m:
        return ""
    return (m.group(1) if m.lastindex else m.group(0)).strip()


def extract_table_rows(text: str) -> list[dict]:
    rows = []

    row_re = re.compile(
        r"""
        ^\s*
        (?P<line>\d{1,4})\s+
        (?P<code>\d{2}\.\d{3}\.?\s*\d{3})\s+
        (?P<qty_ordered>\S+)
        (?:\s+(?P<qty_delivered>\S+))?
        """,
        re.VERBOSE
    )

    stop_re = re.compile(
        r"do\s+dostawy\s+w\s+najbliższym\s+okresie",
        re.IGNORECASE
    )

    ignore_items = False

    for line in text.splitlines():
        if stop_re.search(line):
            ignore_items = True
            continue
        if ignore_items:
            continue

        m = row_re.match(line)
        if not m:
            continue

        raw_ordered = m.group("qty_ordered")
        raw_delivered = m.group("qty_delivered")

        qty_ordered = normalize_qty(raw_ordered)

        if raw_delivered and (
            raw_delivered.isdigit() or len(raw_delivered) == 1
        ):
            qty_delivered = normalize_qty(raw_delivered)
        else:
            qty_delivered = qty_ordered

        if not qty_ordered:
            continue

        rows.append({
            "code": normalize_code(m.group("code")),
            "quantity_ordered": qty_ordered,
            "quantity_delivered": qty_delivered,
        })

    return rows


def extract_fv_invoice_data(text: str) -> dict:
    """Parses invoice text into JSON structure."""

    def find(pattern, text):
        """Finds first match for regex pattern."""
        m = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if not m:
            return ""
        return (m.group(1) if m.lastindex else m.group(0)).strip()

    # === Main JSON structure ===
    data = {
        "seller": {
            "name": find(r"^LYRECO POLSKA S\.A\.", text),
            "address": find(r"ul\.\s+([^\n]+Komorów)", text),
            "nip": "",
            "bank": find(r"BNP\s+Paribas\s+Bank\s+Polska\s+SA", text),
            "account_number": find(r"(\d{26})", text),
            "bdo": find(r"BDO[:\s]+(\d+)", text)
        },
        "buyer": {
            "name": find(r"CEVA\s+LOGISTICS\s+POLAND\s+SP\s+Z\.?O\.?O\.?", text),
            "address": find(r"UL\.?\s+DWORKOWA\s+[^\n]+", text),
            "nip": ""
        },
        "recipient": {
            "name": find(r"Odbiorca\s+([A-Z0-9\s\.\-]+)", text),
            "address": find(r"Odbiorca[^\n]*\n([A-Z0-9\s\.\-]+)", text)
        },
        "invoice": {
            "number": find(r"Potwierdzenie\s+zamówienia\s+(\d+)", text),
            "issue_date": find(r"Data\s+wystawienia\s+([\d/]+)", text),
            "sale_date": find(r"Data\s+sprzedaży\s*[:\-]?\s*([\d/]+)", text),
            "payment_method": find(r"Sposób\s+płatności\s*[:\-]?\s*([^\n]+)", text),
            "order_number": find(r"Zamówienie\s+Nr\s+(\d+)", text)
        },
        "items": [],
        "total_items": 0,
        "uncleaned_text": text
    }

    # === NIP numbers ===
    # Seller (LYRECO)
    seller_nip_pattern = re.compile(
        r"NIP\s*[:\-]?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3})",
        re.IGNORECASE
    )
    seller_nip_match = seller_nip_pattern.search(text)
    if seller_nip_match:
        data["seller"]["nip"] = seller_nip_match.group(1)

    # Buyer (CEVA)
    buyer_nip_pattern = re.compile(
        r"(?:Nr\s*klienta.*?NIP\s*[:\-]?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3}))|"
        r"(?:Nabywca.*?NIP\s*[:\-]?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3}))",
        re.IGNORECASE | re.DOTALL
    )
    buyer_nip_match = buyer_nip_pattern.search(text)
    if buyer_nip_match:
        nip_val = buyer_nip_match.group(1) or buyer_nip_match.group(2)
        data["buyer"]["nip"] = nip_val

    # === Products table ===
    item_pattern = re.compile(
        r"""
        (?:^|\|\s*)?                               # optional prefix like "h |"
        (?P<code>\d{2}\.\d{3}\.\d{3})               # product code
        \s+
        (?P<desc>.+?)                              # description
        \s+(?P<qty>\d+)\s*\|\s*                    # quantity
        (?P<unit>[A-ZŁ]+)\s+                       # unit
        (?P<price_net>[\d\.,]+)\s+                 # unit price
        (?P<value_net>[\d\.,]+)\s*\|\s*            # net value
        (?P<vat_rate>[\d\.,]+%)\s+                 # VAT rate
        (?P<vat_value>[\d\.,]+)\s+                 # VAT value
        (?P<gross_value>[\d\.,]+)                  # gross value
        """,
        re.VERBOSE | re.MULTILINE
    )

    for m in item_pattern.finditer(text):
        data["items"].append({
            "code": m.group("code"),
            "name": m.group("desc").strip(),
            "quantity": m.group("qty"),
            "unit": m.group("unit"),
            "unit_price": m.group("price_net"),
            "value_net": m.group("value_net"),
            "vat_rate": m.group("vat_rate"),
            "vat_value": m.group("vat_value"),
            "gross_value": m.group("gross_value")
        })
    data["total_items"] = len(data["items"])
    return data

def extract_wz_data(text: str) -> dict:
    rows = extract_table_rows(text)

    data = {
        "document_type": "DOKUMENT DOSTAWY",
        "document_number": find(r"DOKUMENT\s+DOSTAWY\s+(\d+)", text),
        "order_number": find(r"Nr\s+Zam[oó]wienia\s*[:\-]?\s*(\d+)", text),
        "client_number": find(r"Nr\s+Klient[a-z]*\s+(\d+)", text),
        "seller": {
            "name": find(r"LYRECO\s+POLSKA\s+S\.A\.", text),
            "address": find(r"ul\.\s+[^\n]+Komor[oó]w", text),
            "nip": find(r"NIP\s*[:\-]?\s*(\d{3}[-\s]\d{2}[-\s]\d{2}[-\s]\d{3})", text),
            "bank": find(r"BNP\s+Paribas\s+Bank\s+Polska\s+SA", text),
            "account_number": find(r"\b(\d{26})\b", text),
        },
        "dates": {
            "delivery_date": find(r"Data\s+Dostawy\s+(\d{2}\.\d{2}\.\d{4})", text),
            "order_date": find(r"Data\s+Zam[oó]wienia\s+(\d{2}\.\d{2}\.\d{4})", text),
        },
        "items": rows,
        "remarks": find(r"UWAGA:.*", text),
        "uncleaned_text": text,
    }

    return data
