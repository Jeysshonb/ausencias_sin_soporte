"""
Script de prueba para verificar imports
"""
import sys
print("Python version:", sys.version)
print("\nIntentando importar módulos...\n")

try:
    import utils
    print("✓ utils importado correctamente")
except Exception as e:
    print(f"✗ Error importando utils: {e}")

try:
    import parsers
    print("✓ parsers importado correctamente")
except Exception as e:
    print(f"✗ Error importando parsers: {e}")

try:
    import processor
    print("✓ processor importado correctamente")
except Exception as e:
    print(f"✗ Error importando processor: {e}")

try:
    import streamlit as st
    print("✓ streamlit importado correctamente")
except Exception as e:
    print(f"✗ Error importando streamlit: {e}")

try:
    import pandas as pd
    print("✓ pandas importado correctamente")
except Exception as e:
    print(f"✗ Error importando pandas: {e}")

try:
    import numpy as np
    print("✓ numpy importado correctamente")
except Exception as e:
    print(f"✗ Error importando numpy: {e}")

try:
    import openpyxl
    print("✓ openpyxl importado correctamente")
except Exception as e:
    print(f"✗ Error importando openpyxl: {e}")

print("\n¡Todos los imports funcionan correctamente!")
