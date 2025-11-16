import re

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
            "payment_method": find(r"Sposób\s+płatności\s*[:\-]?\s*([^\n]+)", text)
        },
        "items": [],
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
        (?P<code>\d{2}\.\d{3}\.\d{3})          # product code (e.g. 20.483.639)
        [^\S\n]*                               # whitespace excluding \n
        (?P<desc>.+?)                          # product description (non-greedy capture)
        \s+(?P<qty>\d+)\s*\|?\s*               # quantity
        (?P<unit>[A-ZŁ]+)\s+                   # unit (SZT)
        (?P<price_net>[\d,]+)\s+               # unit price
        (?P<value_net>[\d,]+)\s*\|\s*          # net value
        (?P<vat_rate>[\d,]+%)\s+               # VAT rate
        (?P<vat_value>[\d,]+)\s+               # VAT amount
        (?P<gross_value>[\d,]+)                # gross value
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

    return data


def extract_wz_data(text: str) -> dict:
    """Parses 'Dokument Dostawy' (WZ) text into structured JSON."""

    def find(pattern, text):
        """Convenient wrapper for re.search - returns first group or ''. """
        m = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if not m:
            return ""
        return (m.group(1) if m.lastindex else m.group(0)).strip()

    # --- Main structure ---
    data = {
        "document_type": "DOKUMENT DOSTAWY",
        "document_number": find(r"DOKUMENT\s+DOSTAWY\s*_?\s*(\d+)", text),
        "order_number": "",  # will be filled below (improved search)
        "client_number": find(r"Nr\s+Klienta\s+(\d+)", text),
        "seller": {
            "name": find(r"LYRECO\s+POLSKA\s+S\.A\.", text),
            "address": find(r"ul\.\s+[^\n]+Komor[oó]w", text),
            "nip": find(r"NIP\s*[:\-]?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3})", text),
            "bank": find(r"BNP\s+Paribas\s+Bank\s+Polska\s+SA", text),
            "account_number": find(r"\b(\d{26})\b", text)
        },
        "buyer": {
            "name": find(r"CEVA\s+LOGISTICS\s+POLAND\s+SP\s+Z\.?O\.?O\.?", text),
            "address": find(r"UL\.?\s+DWORKOWA\s+[^\n]+", text),
            "nip": find(r"NIP\s*[:\-]?\s*(\d{3}[-\s]?\d{2}[-\s]?\d{2}[-\s]?\d{3})", text)
        },
        "delivery": {
            "address": find(r"UL\.?\s+ŁOWICKA\s+[^\n]+", text),
            "contact_person": find(r"Pani\s+([A-ZŁŚĆŻŹa-ząćęłńóśźż\s]+)", text),
            "phone": find(r"\+48\d{9,}", text)
        },
        "dates": {
            "order_date": find(r"Data\s+Zam[oó]wienia\s+([\d]{4}[-/.]\d{2}[-/.]\d{2})", text),
            "delivery_date": find(r"Data\s+Dostawy\s+([\d]{4}[-/.]\d{2}[-/.]\d{2})", text)
        },
        "representatives": {
            "gop": {
                "id": find(r"Przedstawiciel\s+GOP\s+(\d+)", text),
                "name": find(r"Przedstawiciel\s+GOP\s+\d+\s+([A-ZŁŚĆŻŹa-ząćęłńóśźż\s\.]+)", text)
            },
            "nbs": {
                "id": find(r"Przedstawiciel\s+NBS\s+(\d+)", text),
                "name": find(r"Przedstawiciel\s+NBS\s+\d+\s+([A-ZŁŚĆŻŹa-ząćęłńóśźż\s\.]+)", text)
            }
        },
        "reference_number": find(r"Nr\s+referencyjny\s+zam[oó]wienia\s+([A-Z0-9]+)", text),
        "items": [],
        "remarks": find(r"UWAGA:.*", text),
        "uncleaned_text": text
    }

    # --- Improved order number detection ---
    # Sometimes there are two mentions: short (9089956) and full (29089956)
    order_match = re.search(r"Nr\s+Zam[oó]wienia\s*[:\-]?\s*(\d{7,10})", text, re.IGNORECASE)
    if order_match:
        data["order_number"] = order_match.group(1)
    else:
        # fallback - look for the last 8+ digit number in the text
        long_nums = re.findall(r"\b\d{8,}\b", text)
        if long_nums:
            data["order_number"] = long_nums[-1]

    # --- Items parsing ---
    pattern = re.compile(
        r"""
        (?P<line>\d{1,3})            # line number (10, 20, 30)
        [\s\)\|]*                    # spaces, parentheses or |
        (?P<code>\d{2}\.\d{3}\.\d{3})# product code (20.483.639)
        [^\S\n]+
        (?P<qty_ordered>\d+)         # ordered quantity
        [^\S\n]+
        (?P<qty_delivered>\d+)       # delivered quantity
        [^\S\n]+
        (?P<desc>                    # description
            (?:[^\n]*?)
            (?=(?:\n\d{1,3}\s+\d{2}\.\d{3}\.\d{3})|$)
        )
        """,
        re.VERBOSE | re.MULTILINE
    )

    items = []
    for m in pattern.finditer(text):
        desc = re.sub(r"[\|\$]+", "", m.group("desc"))
        desc = re.sub(r"\s+", " ", desc).strip()
        items.append({
            "line_no": m.group("line"),
            "code": m.group("code"),
            "quantity_ordered": m.group("qty_ordered"),
            "quantity_delivered": m.group("qty_delivered"),
            "name": desc
        })
    data["items"] = items

    return data