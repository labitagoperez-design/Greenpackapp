# formulas.py

def calcular_tiempo_stock(visual):
    """
    Identifica los días disponibles para el volcado según el estado Visual.
    """
    tiempos = {
        "VO": "7 - días",
        "V":  "5 - días",
        "VC": "3 - días",
        "P":  "Listo para procesar",
        "A":  "Listo para procesar"
    }
    return tiempos.get(visual, "Sin definir")

def calcular_mayor_auto(leves, menor):
    """Fórmula: mayor = 100 - menor - leves"""
    return max(0.0, 100.0 - menor - leves)

def definir_calidad_auto(mayor):
    """Fórmula: <= 25 es calidad 200, > 25 es calidad 300"""
    return "200" if mayor <= 25 else "300"
def proyectar_pallets(cantidad_bins):
    """
    Fórmula: (bins * 400kg * 0.85) / 1220
    Asumimos un promedio de 400kg por bin de fruta.
    """
    kilos_estimados = (cantidad_bins * 400) * 0.85
    return round(kilos_estimados / 1220, 1)
def calcular_eficiencia_proceso(bins_volcados, bins_obtenidos):
    """
    Calcula kg, rinde y eficiencia.
    """
    kg_volcados = bins_volcados * 400
    kg_obtenidos = bins_obtenidos * 370
    
    # Evitar división por cero
    if kg_volcados > 0:
        rendimiento = (kg_obtenidos / kg_volcados) * 100
    else:
        rendimiento = 0.0
        
    return kg_volcados, kg_obtenidos, round(rendimiento, 2)

def calcular_produccion_kilos(c18, c15):
    kg_producido = (c18 * 18) + (c15 * 15)
    kg_empaque = (c18 * 19) + (c15 * 15.5)
    return kg_producido, kg_empaque

def calcular_rendimientos(kg_empaque, kg_producido, kg_volcado):
    if kg_volcado > 0:
        rinde_empaque = (kg_empaque / kg_volcado) * 100
        rinde_comercial = (kg_producido / kg_volcado) * 100
    else:
        rinde_empaque = rinde_comercial = 0.0
    return round(rinde_empaque, 2), round(rinde_comercial, 2)