"""
Utilidades para procesamiento de datos.
"""
import re
import unicodedata
import pandas as pd
import numpy as np
from datetime import timedelta


def normalize_text(s: str) -> str:
    """
    Normaliza textos para comparar nombres de columnas:
    - lowercase
    - sin tildes
    - deja solo alfanumérico (elimina ° . / etc.)
    """
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nombres de columnas (quita espacios extra)."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """
    Busca la primera columna que coincida con los candidatos (normalizados).
    """
    norm_map = {normalize_text(c): c for c in df.columns}
    for cand in candidates:
        key = normalize_text(cand)
        if key in norm_map:
            return norm_map[key]
    return None


def clean_id(x):
    """Limpia identificadores (quita .0, espacios, etc.)."""
    if pd.isna(x):
        return None
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    if isinstance(x, float):
        return str(int(x)) if x.is_integer() else str(x).strip()
    s = str(x).strip().replace(" ", "")
    s = re.sub(r"\.0$", "", s)
    return s if s else None


def first_nonnull(series):
    """Retorna el primer valor no nulo de una serie."""
    for v in series:
        if pd.notna(v) and str(v).strip() != "":
            return v
    return np.nan


def effective_date_from_list(lst, end_date):
    """Selecciona la fecha más reciente que no supere end_date."""
    cand = [d for d in (lst or []) if d <= end_date]
    return max(cand) if cand else None


def expand_ranges(df, p_start, p_end, id_col="id", ini_col="ini", fin_col="fin"):
    """
    Convierte rangos (ini-fin) a (id,fecha) diario recortado al periodo.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["id", "fecha"])
    dfp = df[df[id_col].notna() & df[ini_col].notna() & df[fin_col].notna()].copy()
    dfp = dfp[(dfp[fin_col] >= p_start) & (dfp[ini_col] <= p_end)]
    out = []
    for _, r in dfp.iterrows():
        ini = max(r[ini_col], p_start)
        fin = min(r[fin_col], p_end)
        d = ini
        while d <= fin:
            out.append((r[id_col], d))
            d += timedelta(days=1)
    return pd.DataFrame(out, columns=["id", "fecha"]).drop_duplicates() if out else pd.DataFrame(columns=["id", "fecha"])


def ensure_cols(df, cols):
    """Asegura que existan las columnas especificadas."""
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df


def safe_select(df, cols):
    """Selecciona columnas, creándolas si no existen."""
    df = ensure_cols(df, cols)
    return df[cols]
