import csv
from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Promocion
from .forms import ProductoForm, PromocionForm
from django.contrib import messages
from django.db.models import Sum, Count
from .models import Pedido, DetallePedido
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import F

def dashboard(request):
    return render(request, 'adminpanel/dashboard.html')

def reportes(request):
    tipo_reporte = request.GET.get('tipo_reporte', 'ventas')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    # Consultas base
    ventas_qs = Pedido.objects.all().order_by('-fecha')
    detalles_qs = DetallePedido.objects.all()

    # Aplicar filtros de fecha si existen
    if fecha_desde:
        fecha_d = parse_date(fecha_desde)
        ventas_qs = ventas_qs.filter(fecha__date__gte=fecha_d)
        detalles_qs = detalles_qs.filter(pedido__fecha__date__gte=fecha_d)
    if fecha_hasta:
        fecha_h = parse_date(fecha_hasta)
        ventas_qs = ventas_qs.filter(fecha__date__lte=fecha_h)
        detalles_qs = detalles_qs.filter(pedido__fecha__date__lte=fecha_h)

    # Generar datos según el tipo de reporte solicitado
    if tipo_reporte == 'ventas':
        # Reporte de Ventas: Lista de pedidos
        reporte = ventas_qs
    else:
       reporte = detalles_qs.values('producto__nombre').annotate(
            cantidad_total=Sum('cantidad'),
            total_recaudado=Sum(F('cantidad') * F('precio_unitario'))
        ).order_by('-cantidad_total')

    contexto = {
        'tipo_reporte': tipo_reporte,
        'reporte': reporte,
        'fecha_desde': fecha_desde or '',
        'fecha_hasta': fecha_hasta or '',
    }
    return render(request, 'adminpanel/reporte.html', contexto)
       

def _obtener_datos_filtrados(request):
    # Reutilizamos la misma lógica que en la vista de reportes
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    ventas_qs = Pedido.objects.all().order_by('-fecha')

    if fecha_desde:
        ventas_qs = ventas_qs.filter(fecha__date__gte=parse_date(fecha_desde))
    if fecha_hasta:
        ventas_qs = ventas_qs.filter(fecha__date__lte=parse_date(fecha_hasta))
    
    return ventas_qs
# Vistas de descarga “ficticias” para no romper la página
def descargar_reporte(request):
    # 1. Obtener los datos reales filtrados
    ventas = _obtener_datos_filtrados(request)
    
    # 2. Preparar el contexto para el template PDF
    ctx = {
        'reporte': ventas,
        'tipo_reporte': 'ventas',
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta')
    }
    
    # 3. Renderizar el template a HTML
    template = get_template('adminpanel/reporte_pdf.html')
    html = template.render(ctx)
    
    # 4. Crear la respuesta PDF
    response = HttpResponse(content_type='application/pdf')
    # 'attachment' hace que se descargue. Si quieres verlo en el navegador usa 'inline'
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas.pdf"'
    
    # 5. Generar el PDF usando xhtml2pdf
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response

# ====== Vista para descargar Excel (CSV) ======
def descargar_reporte_excel(request):
    # 1. Obtener datos
    ventas = _obtener_datos_filtrados(request)
    
    # 2. Preparar respuesta tipo CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas.csv"'
    
    # 3. Escribir el archivo CSV
    writer = csv.writer(response)
    # Escribir cabecera
    writer.writerow(['ID Pedido', 'Fecha', 'Cliente', 'Total', 'Estado'])
    
    # Escribir filas de datos
    for pedido in ventas:
        writer.writerow([
            pedido.id,
            pedido.fecha.strftime("%Y-%m-%d %H:%M"),
            pedido.usuario.username,
            pedido.total,
            pedido.get_estado_display()
        ])
        
    return response

from django.utils.dateparse import parse_date
# Asegúrate de tener importado Pedido al inicio del archivo

def pedidos_view(request):
    # 1. Obtener todos los pedidos ordenados por fecha reciente
    # Usamos 'select_related' para traer datos del usuario rápidamente
    # y 'prefetch_related' para los detalles de productos.
    todos_pedidos = Pedido.objects.select_related('usuario').prefetch_related('detalles__producto').all().order_by('-fecha')

    # 2. Filtrado por fechas si aplica
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if fecha_desde:
        todos_pedidos = todos_pedidos.filter(fecha__date__gte=parse_date(fecha_desde))
    if fecha_hasta:
        todos_pedidos = todos_pedidos.filter(fecha__date__lte=parse_date(fecha_hasta))

    # 3. Separar en las dos listas para las pestañas
    pedidos_retiro = todos_pedidos.filter(tipo_entrega='retiro')
    pedidos_despacho = todos_pedidos.filter(tipo_entrega='despacho')

    context = {
        "pedidos_retiro": pedidos_retiro,
        "pedidos_despacho": pedidos_despacho,
        "fecha_desde": fecha_desde or '',
        "fecha_hasta": fecha_hasta or '',
        "active_tab": request.GET.get('tab', 'retiro'),
    }

    return render(request, "adminpanel/pedidos.html", context)
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
    # Obtener todos los usuarios que no sean superadministradores (staff)
    # y contar sus pedidos (si ya implementaste el modelo Pedido)
    clientes_qs = User.objects.filter(is_staff=False).select_related('perfil').annotate(
        total_pedidos=Count('pedido') # Esto funcionará cuando tengas el modelo Pedido conectado a User
    ).order_by('-date_joined')

    # Búsqueda real por nombre, apellido o correo
    query = request.GET.get('q', '').strip()
    if query:
        clientes_qs = clientes_qs.filter(
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query) | 
            Q(email__icontains=query) |
            Q(username__icontains=query)
        )

    return render(request, 'adminpanel/clientes.html', {
        'clientes': clientes_qs,
        'query': query
    })

def productos(request):
    # 1. Procesar el formulario si se envió datos (POST)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES) # request.FILES es vital para las imágenes
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto agregado correctamente.')
            return redirect('productos') # Recarga la página
        else:
            messages.error(request, 'Error al agregar el producto. Revisa los datos.')
    else:
        form = ProductoForm()

    # 2. Obtener productos REALES de la base de datos
    productos_bd = Producto.objects.all()
    
    # Categorías fijas para las pestañas (deben coincidir con tu modelo)
    categorias = ['vitrina', 'tortas', 'postres'] 

    ctx = {
        'productos': productos_bd,
        'categorias': categorias,
        'form': form # Enviamos el formulario al template
    }
    return render(request, 'adminpanel/productos.html', ctx)

def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado correctamente.')
        return redirect('productos')
    
    # Si intentan entrar por GET, los devolvemos a la lista
    return redirect('productos')

def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        # 'instance=producto' es la CLAVE: le dice a Django que estamos ACTUALIZANDO, no creando.
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('productos')
    else:
        # Pre-llenamos el formulario con los datos actuales
        form = ProductoForm(instance=producto)

    return render(request, 'adminpanel/producto_editar.html', {'form': form, 'producto': producto})

def promociones(request):
    if request.method == 'POST':
        # Si vienen datos, los cargamos en el formulario
        form = PromocionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Promoción creada con éxito!')
            return redirect('adminpanel:promociones') # Recarga la página
        else:
             messages.error(request, 'Error al crear la promoción. Revisa los datos.')
    else:
        # Si es solo una visita (GET), formulario vacío
        form = PromocionForm()

    # Obtenemos las promociones reales de la BD
    promociones_bd = Promocion.objects.all()

    ctx = {
        'promociones': promociones_bd,
        'form': form # Enviamos el formulario al HTML
    }
    return render(request, 'adminpanel/promociones.html', ctx)

def editar_promocion(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    if request.method == 'POST':
        form = PromocionForm(request.POST, request.FILES, instance=promocion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promoción actualizada correctamente.')
            return redirect('adminpanel:promociones')
    else:
        form = PromocionForm(instance=promocion)
    
    return render(request, 'adminpanel/promocion_editar.html', {'form': form, 'promocion': promocion})

def eliminar_promocion(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    if request.method == 'POST':
        promocion.delete()
        messages.success(request, 'Promoción eliminada.')
    return redirect('adminpanel:promociones')