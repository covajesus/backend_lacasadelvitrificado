# Prueba de la función format_number
class TestTemplateClass:
    def format_number(self, value):
        """Formatea números para mostrar enteros sin decimales y decimales cuando es necesario"""
        if value == int(value):
            return str(int(value))
        else:
            return f"{value:.2f}"

# Crear instancia de prueba
test = TestTemplateClass()

# Casos de prueba
test_cases = [
    123.00,   # Debería mostrar: 123
    123.50,   # Debería mostrar: 123.50
    0.00,     # Debería mostrar: 0
    5.25,     # Debería mostrar: 5.25
    100.0,    # Debería mostrar: 100
    1.234,    # Debería mostrar: 1.23 (redondeado)
]

print("Pruebas de formato de números:")
print("=" * 40)
for value in test_cases:
    formatted = test.format_number(value)
    print(f"Input: {value:6} -> Output: {formatted}")
