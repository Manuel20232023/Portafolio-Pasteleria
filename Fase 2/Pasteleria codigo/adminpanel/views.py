from django.shortcuts import render
from datetime import date
from datetime import datetime

def dashboard(request):
    return render(request, 'adminpanel/dashboard.html')

def reportes(request):
    # Tipo de reporte seleccionado (Ventas o Productos)
    tipo_reporte = request.GET.get('tipo_reporte', 'ventas')

    # Fechas de filtro
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    # Datos de ejemplo para Ventas
    ventas = [
        {'fecha': '2025-09-13', 'cliente': 'Juan', 'producto': 'Torta', 'cantidad': 2, 'total': 5000},
        {'fecha': '2025-09-14', 'cliente': 'Maria', 'producto': 'Pan', 'cantidad': 5, 'total': 2500},
        {'fecha': '2025-09-15', 'cliente': 'Felipe', 'producto': 'Postre', 'cantidad': 1, 'total': 3000},
    ]

    # Datos de ejemplo para Productos con fechas de venta
    productos = [
        {'fecha': '2025-09-13', 'producto__nombre': 'Torta', 'cantidad': 5, 'total': 12500},
        {'fecha': '2025-09-14', 'producto__nombre': 'Pan', 'cantidad': 10, 'total': 5000},
        {'fecha': '2025-09-15', 'producto__nombre': 'Postre', 'cantidad': 2, 'total': 6000},
    ]

    # Filtrado por fecha en Ventas
    if fecha_desde:
        ventas = [v for v in ventas if v['fecha'] >= fecha_desde]
        productos = [p for p in productos if p['fecha'] >= fecha_desde]  # también filtramos productos
    if fecha_hasta:
        ventas = [v for v in ventas if v['fecha'] <= fecha_hasta]
        productos = [p for p in productos if p['fecha'] <= fecha_hasta]

    # Decidir qué lista enviar según tipo de reporte
    reporte = ventas if tipo_reporte == 'ventas' else productos

    contexto = {
        'tipo_reporte': tipo_reporte,
        'reporte': reporte,
        'fecha_desde': fecha_desde or '',
        'fecha_hasta': fecha_hasta or '',
        'orden': 'mas_vendido',  # solo de ejemplo
    }

    return render(request, 'adminpanel/reporte.html', contexto)

# Vistas de descarga “ficticias” para no romper la página
def descargar_reporte(request):
    return render(request, 'adminpanel/reporte.html')

def descargar_reporte_excel(request):
    return render(request, 'adminpanel/reporte.html')

def pedidos_view(request):
    # Simulación de pedidos
    pedidos_retiro = [
        {'fecha': '2025-09-20', 'cliente': 'Juan', 'productos': 'Torta Chocolate', 'total': 15000, 'hora_retiro': '15:00'},
        {'fecha': '2025-09-18', 'cliente': 'Maria', 'productos': 'Pan Dulce', 'total': 3000, 'hora_retiro': '12:00'},
    ]

    pedidos_despacho = [
        {'fecha': '2025-09-19', 'cliente': 'Felipe', 'direccion': 'Calle Falsa 123', 'productos': 'Postre Fresa', 'total': 5000},
        {'fecha': '2025-09-17', 'cliente': 'Ana', 'direccion': 'Av. Siempre Viva 742', 'productos': 'Torta Chocolate', 'total': 15000},
    ]

    # Captura de fechas del filtro
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    active_tab = request.GET.get('tab', 'retiro')

    # Función para convertir string a datetime.date
    def str_a_fecha(fecha_str):
        try:
            return datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except:
            return None

    fd = str_a_fecha(fecha_desde)
    fh = str_a_fecha(fecha_hasta)

    # Filtrar pedidos retiro
    if fd:
        pedidos_retiro = [p for p in pedidos_retiro if datetime.strptime(p['fecha'], '%Y-%m-%d').date() >= fd]
    if fh:
        pedidos_retiro = [p for p in pedidos_retiro if datetime.strptime(p['fecha'], '%Y-%m-%d').date() <= fh]

    # Filtrar pedidos despacho
    if fd:
        pedidos_despacho = [p for p in pedidos_despacho if datetime.strptime(p['fecha'], '%Y-%m-%d').date() >= fd]
    if fh:
        pedidos_despacho = [p for p in pedidos_despacho if datetime.strptime(p['fecha'], '%Y-%m-%d').date() <= fh]

    context = {
        "pedidos_retiro": pedidos_retiro,
        "pedidos_despacho": pedidos_despacho,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "active_tab": active_tab,
    }

    return render(request, "adminpanel/pedidos.html", context)


def clientes(request):
    # Aquí puedes simular datos de clientes
    clientes = [
        {
            "nombre": "Mariela Osorio",
            "correo": "mariela@email.com",
            "telefono": "+56912345678",
            "direccion": "Calle Falsa 123, Santiago",
            "fecha_registro": "2025-01-15",
            "pedidos": 5
        },
        {
            "nombre": "Juan Pérez",
            "correo": "juanp@email.com",
            "telefono": "+56987654321",
            "direccion": "Av. Siempre Viva 742, Santiago",
            "fecha_registro": "2025-03-22",
            "pedidos": 2
        },
         {
            "nombre": "Felipe Carcamo",
            "correo": "felipe@email.com",
            "telefono": "+56968423614",
            "direccion": "Psje Rojo 888, Santiago",
            "fecha_registro": "2025-05-07",
            "pedidos": 8
        },
        # Agrega más clientes de prueba si quieres
    ]

    # También capturamos la búsqueda por nombre o correo
    query = request.GET.get('q', '')
    if query:
        clientes = [c for c in clientes if query.lower() in c['nombre'].lower() or query.lower() in c['correo'].lower()]

    return render(request, 'adminpanel/clientes.html', {
        'clientes': clientes,
        'query': query
    })

def productos(request):
    productos = [
        {'nombre': 'Torta Chocolate', 'precio': 15000, 'stock': 10, 'categoria': 'Tortas'},
        {'nombre': 'Postre Fresa', 'precio': 5000, 'stock': 20, 'categoria': 'Postres'},
        {'nombre': 'Pan Dulce', 'precio': 3000, 'stock': 50, 'categoria': 'Vitrina'},
    ]
    categorias = ['Vitrina', 'Tortas', 'Postres']  # solo nombres de categorías
    return render(request, 'adminpanel/productos.html', {'productos': productos, 'categorias': categorias})

def promociones(request):
    # Lista de promociones de prueba
    promociones = [
        {'nombre': 'Promo Chocolate', 'descuento': '20%', 'vigencia': 'Hasta 30/09/2025'},
        {'nombre': 'Promo Frutal', 'descuento': '15%', 'vigencia': 'Hasta 30/09/2025'},
        {'nombre': 'Promo Cumpleaños', 'descuento': '25%', 'vigencia': 'Hasta 31/12/2025'},
    ]
    return render(request, 'adminpanel/promociones.html', {'promociones': promociones})

