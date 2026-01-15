"""
Procesador principal: toda la lógica de cálculos y generación de reportes.
"""
import pandas as pd
import numpy as np
from datetime import timedelta
from io import BytesIO

from utils import (
    clean_id, expand_ranges, effective_date_from_list,
    safe_select, find_col, normalize_cols
)
from parsers import parse_sap_report


class AusenciasProcessor:
    """Procesador de ausencias sin soporte."""

    def __init__(self, period_start, period_end):
        self.period_start = period_start
        self.period_end = period_end
        self.logs = []

    def log(self, msg: str):
        """Agrega un mensaje al log."""
        self.logs.append(msg)

    def process(self, files: dict) -> dict:
        """
        Procesa todos los archivos y genera el reporte.

        Args:
            files: Dict con keys: 'horas', 'ausrep', 'retiros', 'md', 'func', 'aussap'
                   Cada value es un dict con 'bytes' y 'name'

        Returns:
            Dict con keys: 'dfs' (hojas del Excel), 'logs', 'excel_bytes', 'file_name'
        """
        # Leer archivos
        horas = normalize_cols(pd.read_excel(BytesIO(files['horas']['bytes']), sheet_name=0, engine="openpyxl"))
        ausrep = normalize_cols(pd.read_excel(BytesIO(files['ausrep']['bytes']), sheet_name=0, engine="openpyxl"))
        retiros = normalize_cols(pd.read_excel(BytesIO(files['retiros']['bytes']), sheet_name=0, engine="openpyxl"))
        md = normalize_cols(pd.read_excel(BytesIO(files['md']['bytes']), sheet_name=0, engine="openpyxl"))
        func = normalize_cols(pd.read_excel(BytesIO(files['func']['bytes']), sheet_name=0, engine="openpyxl"))

        aussap2 = parse_sap_report(files['aussap']['bytes'], files['aussap']['name'])

        # Validar columnas
        col_map = self._validate_columns(horas, ausrep, retiros, md, func)
        if col_map is None:
            return None

        # Procesar marcaciones TS
        marc = self._process_marcaciones(horas, col_map['h_id'], col_map['h_fecha'])

        # Procesar ausentismos reporte
        ausrep_days = self._process_ausentismos_reporte(ausrep, col_map)

        # Procesar retiros
        ret_list = self._process_retiros(retiros, col_map)

        # Procesar MasterData
        ing_list, authorized_ids, md2 = self._process_masterdata(md, func, col_map)

        # Procesar SAP
        aussap_days = expand_ranges(aussap2, self.period_start, self.period_end)

        # Crear universo y grid
        grid, info_master = self._build_grid(
            marc, ausrep_days, aussap_days, ret_list, ing_list,
            authorized_ids, md2, horas, ausrep, aussap2, retiros
        )

        # Calcular ausencias sin soporte
        aus_sin_out = self._calculate_ausencias_sin_soporte(grid, info_master)

        # Generar resumen
        summary = self._generate_summary(grid, info_master)

        # Hojas adicionales
        retiros_fuera = summary[summary["estado_periodo"] == "Retirado antes del periodo"].copy()
        retiros_fuera["TieneMovEnPeriodo"] = np.where(
            (retiros_fuera["DiasConMarcacion"] > 0) | (retiros_fuera["DiasAusReporte"] > 0) | (retiros_fuera["DiasAusSAP"] > 0),
            "SI", "NO"
        )

        ingresos_post = summary[summary["estado_periodo"] == "Ingreso posterior al periodo"].copy()

        inconsistencias = summary[
            ((summary["estado_periodo"] == "Ingreso posterior al periodo") & (summary["DiasConMarcacion"] > 0)) |
            ((summary["Ingreso"].notna()) & (summary["Retiro"].notna()) & (summary["Retiro"] < summary["Ingreso"]) & (summary["DiasConMarcacion"] > 0))
        ].copy()

        # Parámetros
        params = pd.DataFrame({
            "Parametro": [
                "Periodo_inicio", "Periodo_fin",
                "MD_id_col_usada",
                "Regla_retiro", "Regla_ingreso", "Regla_activos_TS",
                "Cantidad_funciones_autorizadas", "Ausentismos_SAP_parseados"
            ],
            "Valor": [
                str(self.period_start), str(self.period_end),
                str(col_map['md_id']),
                "Fecha retiro = Desde - 1 día",
                "Ingreso = Fecha (Clase de fecha contiene 'alta')",
                "Activos: SOLO IDs en MasterData con función autorizada (TS)",
                str(len(set(func[col_map['f_func']].dropna().astype(str).str.strip().unique()))),
                str(len(aussap2))
            ]
        })

        dfs = {
            "Parametros": params,
            "Ausencias_sin_soporte": aus_sin_out,
            "Resumen_periodo": summary,
            "Retiros_fuera_rango": retiros_fuera,
            "Ingresos_posteriores": ingresos_post,
            "Inconsistencias": inconsistencias,
        }

        excel_bytes = self._build_excel(dfs)
        file_name = f"Ausencias_sin_soporte_{self.period_start}_{self.period_end}.xlsx"

        return {
            'dfs': dfs,
            'logs': self.logs,
            'excel_bytes': excel_bytes,
            'file_name': file_name
        }

    def _validate_columns(self, horas, ausrep, retiros, md, func) -> dict | None:
        """Valida y retorna el mapeo de columnas."""
        col_h_id = find_col(horas, ["IdentificacionEmpleado", "IdentificaciónEmpleado"])
        col_h_fecha = find_col(horas, ["FechaEntrada", "Fecha Entrada"])

        col_ar_id = find_col(ausrep, ["Identificacion", "Identificación"])
        col_ar_ini = find_col(ausrep, ["Fecha_Inicio", "Fecha Inicio"])
        col_ar_fin = find_col(ausrep, ["Fecha_Final", "Fecha Final"])

        col_r_id = find_col(retiros, ["Número ID", "Numero ID", "Nº ID", "No ID"])
        col_r_desde = find_col(retiros, ["Desde"])

        col_md_id = find_col(md, [
            "N° pers.", "Nº pers.", "N°pers.", "Nºpers.", "No pers.", "Nro pers.",
            "Numero pers.", "Número pers.", "Numero de personal", "Numero personal",
            "Número ID", "Numero ID"
        ])
        col_md_func = find_col(md, ["Función", "Funcion"])
        col_md_clase = find_col(md, ["Clase de fecha", "Clase Fecha"])
        col_md_fecha = find_col(md, ["Fecha"])

        col_f_func = find_col(func, ["Función", "Funcion"])

        self.log(f"[TS] ID={col_h_id} | Fecha={col_h_fecha}")
        self.log(f"[Aus Rep] ID={col_ar_id} | Ini={col_ar_ini} | Fin={col_ar_fin}")
        self.log(f"[Retiros] ID={col_r_id} | Desde={col_r_desde}")
        self.log(f"[MD] ID={col_md_id} | Func={col_md_func} | Clase={col_md_clase} | Fecha={col_md_fecha}")
        self.log(f"[Funcs] Func={col_f_func}")

        missing = []
        if not col_h_id or not col_h_fecha:
            missing.append("Rep_Horas_laboradas: IdentificacionEmpleado / FechaEntrada")
        if not col_ar_id or not col_ar_ini or not col_ar_fin:
            missing.append("Rep_aususentismos: Identificacion / Fecha_Inicio / Fecha_Final")
        if not col_r_id or not col_r_desde:
            missing.append("Retiros: Número ID / Desde")
        if not col_md_id or not col_md_func or not col_md_clase or not col_md_fecha:
            missing.append("Md_activos: N° pers. / Función / Clase de fecha / Fecha")
        if not col_f_func:
            missing.append("funciones_marcación: Función")

        if missing:
            self.log(f"[ERROR] Columnas faltantes: {missing}")
            return None

        return {
            'h_id': col_h_id, 'h_fecha': col_h_fecha,
            'ar_id': col_ar_id, 'ar_ini': col_ar_ini, 'ar_fin': col_ar_fin,
            'r_id': col_r_id, 'r_desde': col_r_desde,
            'md_id': col_md_id, 'md_func': col_md_func, 'md_clase': col_md_clase, 'md_fecha': col_md_fecha,
            'f_func': col_f_func
        }

    def _process_marcaciones(self, horas, col_id, col_fecha):
        """Procesa marcaciones de TS."""
        horas2 = horas.copy()
        horas2["id"] = horas2[col_id].apply(clean_id)
        horas2["fecha"] = pd.to_datetime(horas2[col_fecha], errors="coerce").dt.date
        return horas2[horas2["id"].notna() & horas2["fecha"].notna()][["id", "fecha"]].drop_duplicates()

    def _process_ausentismos_reporte(self, ausrep, col_map):
        """Procesa ausentismos del reporte."""
        ausrep2 = ausrep.copy()
        ausrep2["id"] = ausrep2[col_map['ar_id']].apply(clean_id)
        ausrep2["ini"] = pd.to_datetime(ausrep2[col_map['ar_ini']], errors="coerce").dt.date
        ausrep2["fin"] = pd.to_datetime(ausrep2[col_map['ar_fin']], errors="coerce").dt.date
        return expand_ranges(ausrep2, self.period_start, self.period_end)

    def _process_retiros(self, retiros, col_map):
        """Procesa retiros."""
        retiros2 = retiros.copy()
        retiros2["id"] = retiros2[col_map['r_id']].apply(clean_id)
        retiros2["Desde_dt"] = pd.to_datetime(retiros2[col_map['r_desde']], errors="coerce").dt.date
        retiros2["FechaRetiro"] = retiros2["Desde_dt"].apply(
            lambda d: d - timedelta(days=1) if pd.notna(d) else None
        )

        ret_list = (
            retiros2.groupby("id")["FechaRetiro"]
            .apply(lambda s: sorted(set([d for d in s.dropna()])))
            .reset_index()
        )
        ret_list["RetiroEfectivo"] = ret_list["FechaRetiro"].apply(
            lambda lst: effective_date_from_list(lst, self.period_end)
        )
        ret_list["ListaRetiros"] = ret_list["FechaRetiro"].apply(
            lambda lst: ", ".join([d.isoformat() for d in lst]) if isinstance(lst, list) else ""
        )
        return ret_list

    def _process_masterdata(self, md, func, col_map):
        """Procesa MasterData y funciones autorizadas."""
        md2 = md.copy()
        md2["id"] = md2[col_map['md_id']].apply(clean_id)
        md2["funcion"] = md2[col_map['md_func']].astype(str).str.strip()
        md2["clase_fecha"] = md2[col_map['md_clase']].astype(str).str.strip()
        md2["fecha_clase"] = pd.to_datetime(md2[col_map['md_fecha']], errors="coerce").dt.date

        md2["ingreso"] = np.where(
            md2["clase_fecha"].str.lower().str.contains("alta"),
            md2["fecha_clase"],
            pd.NaT
        )
        md2["ingreso"] = pd.to_datetime(md2["ingreso"], errors="coerce").dt.date

        auth_funcs = set(func[col_map['f_func']].dropna().astype(str).str.strip().unique())
        md2["autorizado_TS"] = md2["funcion"].isin(auth_funcs)

        ing_list = (
            md2.groupby("id")["ingreso"]
            .apply(lambda s: sorted(set([d for d in s.dropna()])))
            .reset_index()
        )
        ing_list["IngresoEfectivo"] = ing_list["ingreso"].apply(
            lambda lst: effective_date_from_list(lst, self.period_end)
        )
        ing_list["ListaIngresos"] = ing_list["ingreso"].apply(
            lambda lst: ", ".join([d.isoformat() for d in lst]) if isinstance(lst, list) else ""
        )

        authorized_ids = set(md2.loc[md2["autorizado_TS"] & md2["id"].notna(), "id"].unique())

        return ing_list, authorized_ids, md2

    def _build_grid(self, marc, ausrep_days, aussap_days, ret_list, ing_list,
                    authorized_ids, md2, horas, ausrep, aussap2, retiros):
        """Construye el grid completo con todos los IDs y fechas."""
        horas2_ids = horas.copy()
        horas2_ids["id"] = horas2_ids[horas2_ids.columns[0]].apply(clean_id)

        ausrep2_ids = ausrep.copy()
        ausrep2_ids["id"] = ausrep2_ids[ausrep2_ids.columns[0]].apply(clean_id)

        retiros2_ids = retiros.copy()
        retiros2_ids["id"] = retiros2_ids[retiros2_ids.columns[0]].apply(clean_id)

        ids_union = pd.Index(pd.concat([
            pd.Series(list(authorized_ids)),
            horas2_ids["id"], ausrep2_ids["id"], aussap2["id"], retiros2_ids["id"]
        ]).dropna().unique())

        all_dates = pd.date_range(self.period_start, self.period_end, freq="D").date
        grid = pd.MultiIndex.from_product([ids_union, all_dates], names=["id", "fecha"]).to_frame(index=False)

        # Agregar flags
        grid = grid.merge(marc.assign(tiene_marcacion=True), on=["id", "fecha"], how="left")
        grid["tiene_marcacion"] = grid["tiene_marcacion"].fillna(False)

        grid = grid.merge(ausrep_days.assign(tiene_aus_rep=True), on=["id", "fecha"], how="left")
        grid["tiene_aus_rep"] = grid["tiene_aus_rep"].fillna(False)

        grid = grid.merge(aussap_days.assign(tiene_aus_sap=True), on=["id", "fecha"], how="left")
        grid["tiene_aus_sap"] = grid["tiene_aus_sap"].fillna(False)

        grid = grid.merge(ret_list[["id", "RetiroEfectivo"]], on="id", how="left")
        grid = grid.merge(ing_list[["id", "IngresoEfectivo"]], on="id", how="left")
        grid = grid.merge(md2[["id", "autorizado_TS", "funcion"]].drop_duplicates("id"), on="id", how="left")
        grid["autorizado_TS"] = grid["autorizado_TS"].fillna(False)

        # Estado y vigencia
        grid["estado_periodo"] = [
            self._estado_periodo(r, i)
            for r, i in zip(grid["RetiroEfectivo"], grid["IngresoEfectivo"])
        ]

        grid["vigente_dia"] = [
            self._vigente(d, i, r)
            for d, i, r in zip(grid["fecha"], grid["IngresoEfectivo"], grid["RetiroEfectivo"])
        ]

        grid["sin_soporte"] = (
            grid["vigente_dia"]
            & (~grid["tiene_marcacion"])
            & (~grid["tiene_aus_rep"])
            & (~grid["tiene_aus_sap"])
        )

        grid["considerar_activo_TS"] = (grid["estado_periodo"] == "Activo (MD)") & (grid["autorizado_TS"])
        grid["considerar"] = grid["considerar_activo_TS"] | grid["estado_periodo"].isin([
            "Retirado en el periodo", "Retirado antes del periodo", "Retiro despues del periodo",
            "Sin masterdata (posible retirado)"
        ])

        # Info master
        info_master = pd.DataFrame({"id": ids_union})
        info_master = info_master.merge(md2[["id", "funcion"]].drop_duplicates("id"), on="id", how="left")
        info_master = info_master.merge(ret_list[["id", "ListaRetiros"]], on="id", how="left")
        info_master = info_master.merge(ing_list[["id", "ListaIngresos"]], on="id", how="left")

        return grid, info_master

    def _estado_periodo(self, ret, ing):
        """Determina el estado del empleado en el periodo."""
        if pd.isna(ret):
            if pd.isna(ing):
                return "Sin masterdata (posible retirado)"
            if ing > self.period_end:
                return "Ingreso posterior al periodo"
            return "Activo (MD)"
        if ret < self.period_start:
            return "Retirado antes del periodo"
        if ret <= self.period_end:
            return "Retirado en el periodo"
        return "Retiro despues del periodo"

    def _vigente(self, d, ing, ret):
        """Determina si el empleado está vigente en una fecha."""
        if pd.notna(ing) and d < ing:
            return False
        if pd.notna(ret) and d > ret:
            return False
        return True

    def _calculate_ausencias_sin_soporte(self, grid, info_master):
        """Calcula ausencias sin soporte."""
        aus_sin = grid[grid["considerar"] & grid["sin_soporte"]].merge(info_master, on="id", how="left")
        aus_sin["Observacion"] = aus_sin["estado_periodo"].map(self._obs)

        detail_cols = [
            "id", "funcion", "autorizado_TS", "fecha", "estado_periodo",
            "IngresoEfectivo", "RetiroEfectivo",
            "tiene_marcacion", "tiene_aus_rep", "tiene_aus_sap",
            "sin_soporte", "Observacion", "ListaIngresos", "ListaRetiros"
        ]
        return safe_select(aus_sin, detail_cols).sort_values(["estado_periodo", "id", "fecha"])

    def _obs(self, stt):
        """Genera observación según estado."""
        return {
            "Activo (MD)": "Activo autorizado TS: sin marcación y sin ausentismo (Reporte + SAP)",
            "Retirado en el periodo": "Retirado: sin marcación y sin ausentismo (Reporte + SAP) hasta fecha retiro",
            "Retiro despues del periodo": "Retiro posterior: sin marcación y sin ausentismo (Reporte + SAP) en el periodo",
            "Sin masterdata (posible retirado)": "Sin masterdata: sin marcación y sin ausentismo (Reporte + SAP) en el periodo"
        }.get(stt, "Sin marcación y sin ausentismo (Reporte + SAP)")

    def _generate_summary(self, grid, info_master):
        """Genera resumen por ID."""
        g = grid[grid["considerar"]].merge(info_master, on="id", how="left")

        need_cols = [
            "funcion", "autorizado_TS", "estado_periodo",
            "IngresoEfectivo", "RetiroEfectivo",
            "ListaIngresos", "ListaRetiros",
            "fecha", "vigente_dia",
            "tiene_marcacion", "tiene_aus_rep", "tiene_aus_sap",
            "sin_soporte"
        ]

        for c in need_cols:
            if c not in g.columns:
                if c in ["vigente_dia", "tiene_marcacion", "tiene_aus_rep", "tiene_aus_sap", "sin_soporte", "autorizado_TS"]:
                    g[c] = False
                else:
                    g[c] = np.nan

        for c in ["vigente_dia", "tiene_marcacion", "tiene_aus_rep", "tiene_aus_sap", "sin_soporte", "autorizado_TS"]:
            g[c] = g[c].fillna(False)

        summary = g.groupby("id").agg(
            funcion=("funcion", "first"),
            autorizado_TS=("autorizado_TS", "first"),
            estado_periodo=("estado_periodo", "first"),
            Ingreso=("IngresoEfectivo", "first"),
            Retiro=("RetiroEfectivo", "first"),
            ListaIngresos=("ListaIngresos", "first"),
            ListaRetiros=("ListaRetiros", "first"),
            DiasPeriodo=("fecha", "nunique"),
            DiasVigente=("vigente_dia", "sum"),
            DiasConMarcacion=("tiene_marcacion", "sum"),
            DiasAusReporte=("tiene_aus_rep", "sum"),
            DiasAusSAP=("tiene_aus_sap", "sum"),
            DiasSinSoporte=("sin_soporte", "sum"),
        ).reset_index()

        ultima_marc = g[g["tiene_marcacion"]].groupby("id")["fecha"].max().rename("UltimaMarcacion")
        summary = summary.merge(ultima_marc, on="id", how="left").sort_values(
            ["estado_periodo", "DiasSinSoporte"], ascending=[True, False]
        )

        return summary

    def _build_excel(self, dfs: dict) -> bytes:
        """Construye archivo Excel con múltiples hojas."""
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for sh, df in dfs.items():
                df.to_excel(writer, sheet_name=sh[:31], index=False)
        buffer.seek(0)
        return buffer.read()
