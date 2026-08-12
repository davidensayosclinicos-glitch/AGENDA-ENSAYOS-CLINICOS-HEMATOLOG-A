import unittest
from datetime import date

import pandas as pd

from agenda_medica_2026 import _agrupar_items_por_categoria, _aplicar_ocultacion_visitas_medicas


class AgendaMedicaVisibilityTests(unittest.TestCase):
    def test_excluye_visitas_del_dia_seleccionado_en_interfaz_medica(self):
        df = pd.DataFrame(
            [
                {"id": 1, "fecha": "2026-08-11", "codigo": "A001", "nombre": "Ana", "ensayo": "ENSAYO 1"},
                {"id": 2, "fecha": "2026-08-12", "codigo": "A002", "nombre": "Luis", "ensayo": "ENSAYO 2"},
                {"id": 3, "fecha": "2026-08-11", "codigo": "A003", "nombre": "Marta", "ensayo": "ENSAYO 3"},
            ]
        )

        resultado = _aplicar_ocultacion_visitas_medicas(df, date(2026, 8, 11))

        self.assertEqual(list(resultado["id"]), [2])

    def test_sintomas_y_aes_comparten_la_misma_estructura(self):
        items = [
            {"nombre": "Dolor abdominal", "categoria": "Sintoma"},
            {"nombre": "Náuseas", "categoria": "Efecto adverso"},
            {"nombre": "Aspirina", "categoria": "Medicación"},
        ]

        agrupado = _agrupar_items_por_categoria(items)

        self.assertEqual([i["nombre"] for i in agrupado["Sintoma"]], ["Dolor abdominal", "Náuseas"])
        self.assertEqual([i["nombre"] for i in agrupado["Medicación"]], ["Aspirina"])
        self.assertNotIn("Efecto adverso", agrupado)


if __name__ == "__main__":
    unittest.main()
