"""ResourceShift AI - Data Generation & Ingestion Package."""
from .generate_data import generate_electricity_data
from .generate_water_data import generate_water_data
from .generate_fuel_data import generate_fuel_data

__all__ = [
    "generate_electricity_data",
    "generate_water_data",
    "generate_fuel_data",
]
