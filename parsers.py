"""
Parsers para archivos SAP y otros formatos.
"""
import re
import io
import pandas as pd
from utils import clean_id


def _parse_sap_from_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse SAP data desde un DataFrame."""
    date_re = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")
    num_re = re.compile(r"^\d{6,15}$")

    def parse_row(row):
        s = "\t".join([str(v) for v in row if pd.notna(v)])
        parts = [p.strip() for p in re.split(r"\t+", s) if p.strip() != ""]

        dates = [p for p in parts if date_re.match(p)]
        if len(dates) < 2:
            return None

        nums = [p for p in parts if num_re.match(p)]
        if len(nums) < 2:
            return None

        pernr = nums[0]
        cand = [n for n in nums[1:] if n != pernr]
        if not cand:
            return None
        cedula = max(cand, key=len)

        ini = pd.to_datetime(dates[0], format="%d.%m.%Y", errors="coerce")
        fin = pd.to_datetime(dates[1], format="%d.%m.%Y", errors="coerce")
        if pd.isna(ini) or pd.isna(fin):
            return None

        return {"id": clean_id(cedula), "ini": ini.date(), "fin": fin.date(), "pernr": pernr}

    rows = []
    for i in range(len(raw)):
        pr = parse_row(raw.iloc[i].tolist())
        if pr:
            rows.append(pr)

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["id", "ini", "fin", "pernr"])


def _parse_sap_from_text_lines(lines) -> pd.DataFrame:
    """Parse SAP data desde líneas de texto."""
    date_re = re.compile(r"\b\d{2}\.\d{2}\.\d{4}\b")
    num_re = re.compile(r"\b\d{6,15}\b")

    out = []
    for line in lines:
        dates = date_re.findall(line)
        if len(dates) < 2:
            continue

        nums = num_re.findall(line)
        if len(nums) < 2:
            continue

        pernr = nums[0]
        cand = [n for n in nums[1:] if n != pernr]
        if not cand:
            continue

        cedula = max(cand, key=len)

        ini = pd.to_datetime(dates[0], format="%d.%m.%Y", errors="coerce")
        fin = pd.to_datetime(dates[1], format="%d.%m.%Y", errors="coerce")
        if pd.isna(ini) or pd.isna(fin):
            continue

        out.append({"id": clean_id(cedula), "ini": ini.date(), "fin": fin.date(), "pernr": pernr})

    return pd.DataFrame(out) if out else pd.DataFrame(columns=["id", "ini", "fin", "pernr"])


def parse_sap_report(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Parser robusto para archivos SAP en diferentes formatos.
    Intenta: Excel (.xls, .xlsx), HTML, y texto plano.
    """
    # 1) Excel por extensión
    try:
        if filename.endswith(".xls"):
            raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None, engine="xlrd")
        else:
            raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None, engine="openpyxl")
        return _parse_sap_from_dataframe(raw)
    except Exception:
        pass

    # 2) HTML / texto
    try:
        txt = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        txt = file_bytes.decode("latin-1", errors="ignore")

    if "<table" in txt.lower():
        try:
            tables = pd.read_html(txt)
            if tables:
                raw = tables[0].astype(str).reset_index(drop=True)
                return _parse_sap_from_dataframe(raw)
        except Exception:
            pass

    return _parse_sap_from_text_lines(txt.splitlines())
