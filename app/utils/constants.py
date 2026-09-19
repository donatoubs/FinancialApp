"""
Constantes globales y catálogos financieros de la aplicación.
Incluye entidades bancarias de Ecuador, tipos de tarjetas y divisas.
"""

from typing import List, Dict

# Lista oficial de entidades financieras y emisores de Ecuador
ECUADOR_BANKS: List[Dict[str, str]] = [
    {"name": "Banco Pichincha", "color": "#ffdd00", "text_color": "#000000", "code": "PICHINCHA"},
    {"name": "Banco Guayaquil", "color": "#e30613", "text_color": "#ffffff", "code": "GUAYAQUIL"},
    {"name": "Banco del Pacífico", "color": "#005691", "text_color": "#ffffff", "code": "PACIFICO"},
    {"name": "Produbanco", "color": "#00833e", "text_color": "#ffffff", "code": "PRODUBANCO"},
    {"name": "Banco Bolivariano", "color": "#007236", "text_color": "#ffffff", "code": "BOLIVARIANO"},
    {"name": "Banco Internacional", "color": "#e05206", "text_color": "#ffffff", "code": "INTERNACIONAL"},
    {"name": "Banco del Austro", "color": "#7c1c2b", "text_color": "#ffffff", "code": "AUSTRO"},
    {"name": "Banco Solidario", "color": "#ef7c00", "text_color": "#ffffff", "code": "SOLIDARIO"},
    {"name": "Banco General Rumiñahui", "color": "#004080", "text_color": "#ffffff", "code": "BGR"},
    {"name": "Banco de Loja", "color": "#ffb600", "text_color": "#000000", "code": "LOJA"},
    {"name": "Diners Club Ecuador", "color": "#003b6f", "text_color": "#ffffff", "code": "DINERS"},
    {"name": "Efectivo / Caja", "color": "#10b981", "text_color": "#ffffff", "code": "CASH"},
    {"name": "Otro Banco / Cooperativa", "color": "#64748b", "text_color": "#ffffff", "code": "OTHER"}
]

# Marcas de tarjetas internacionales
CARD_BRANDS = [
    "Visa",
    "Mastercard",
    "Diners Club",
    "American Express",
    "Discover",
    "Otra"
]
