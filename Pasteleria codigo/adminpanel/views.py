import csv
from django.shortcuts import render, redirect, get_object_or_404
from .models import Producto, Promocion, Pedido, DetallePedido
from .forms import ProductoForm, PromocionForm
from django.contrib import messages
from django.db.models import Sum, Count, F, Q
from django.utils.dateparse import parse_date
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from datetime import datetime

@staff_member_required
def dashboard(request):
    return render(request, 'adminpanel/dashboard.html')

@staff_member_required
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
        if fecha_d:
            ventas_qs = ventas_qs.filter(fecha__date__gte=fecha_d)
            detalles_qs = detalles_qs.filter(pedido__fecha__date__gte=fecha_d)
    if fecha_hasta:
        fecha_h = parse_date(fecha_hasta)
        if fecha_h:
            ventas_qs = ventas_qs.filter(fecha__date__lte=fecha_h)
            detalles_qs = detalles_qs.filter(pedido__fecha__date__lte=fecha_h)

    # Generar datos según el tipo de reporte solicitado
    if tipo_reporte == 'ventas':
        # Reporte de Ventas: Lista de pedidos
        reporte = ventas_qs
    else:
       # Reporte de Productos: Agrupado por producto, sumando cantidad y total recaudado
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
    # Función auxiliar (no necesita @staff_member_required porque solo la llaman otras vistas ya protegidas)
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    ventas_qs = Pedido.objects.all().order_by('-fecha')

    if fecha_desde:
        fecha_d = parse_date(fecha_desde)
        if fecha_d:
            ventas_qs = ventas_qs.filter(fecha__date__gte=fecha_d)
    if fecha_hasta:
        fecha_h = parse_date(fecha_hasta)
        if fecha_h:
             ventas_qs = ventas_qs.filter(fecha__date__lte=fecha_h)
    
    return ventas_qs

@staff_member_required
def descargar_reporte(request):
    ventas = _obtener_datos_filtrados(request)
    
    ctx = {
        'reporte': ventas,
        'tipo_reporte': 'ventas',
        'fecha_desde': request.GET.get('fecha_desde'),
        'fecha_hasta': request.GET.get('fecha_hasta')
    }
    
    template = get_template('adminpanel/reporte_pdf.html')
    html = template.render(ctx)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response

@staff_member_required
def descargar_reporte_excel(request):
    ventas = _obtener_datos_filtrados(request)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="reporte_ventas.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID Pedido', 'Fecha', 'Cliente', 'Total', 'Estado'])
    
    for pedido in ventas:
        writer.writerow([
            pedido.id,
            pedido.fecha.strftime("%Y-%m-%d %H:%M"),
            pedido.usuario.username,
            pedido.total,
            pedido.get_estado_display()
        ])
        
    return response

@staff_member_required
def pedidos_view(request):
    todos_pedidos = Pedido.objects.select_related('usuario').prefetch_related('detalles__producto').all().order_by('-fecha')

    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    if fecha_desde:
        fecha_d = parse_date(fecha_desde)
        if fecha_d:
             todos_pedidos = todos_pedidos.filter(fecha__date__gte=fecha_d)
    if fecha_hasta:
        fecha_h = parse_date(fecha_hasta)
        if fecha_h:
             todos_pedidos = todos_pedidos.filter(fecha__date__lte=fecha_h)

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

@staff_member_required
def clientes(request):
    # Asumiendo que el modelo Pedido tiene related_name='pedidos' hacia User, 
    # si no lo tiene por defecto es 'pedido_set'. Ajusta si es necesario.
    # Para simplificar y evitar errores si no está configurado el related_name:
    clientes_qs = User.objects.filter(is_staff=False).select_related('perfil').annotate(
        total_pedidos=Count('pedido') 
    ).order_by('-date_joined')

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

@staff_member_required
def productos(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto agregado correctamente.')
            return redirect('adminpanel:productos') # <--- PREFIJO AGREGADO
        else:
            messages.error(request, 'Error al agregar el producto. Revisa los datos.')
    else:
        form = ProductoForm()

    productos_bd = Producto.objects.all()
    categorias = ['vitrina', 'tortas', 'postres'] 

    ctx = {
        'productos': productos_bd,
        'categorias': categorias,
        'form': form
    }
    return render(request, 'adminpanel/productos.html', ctx)

@staff_member_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        producto.delete()
        messages.success(request, 'Producto eliminado correctamente.')
        return redirect('adminpanel:productos') # <--- PREFIJO AGREGADO
    
    return redirect('adminpanel:productos') # <--- PREFIJO AGREGADO

@staff_member_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('adminpanel:productos') # <--- PREFIJO AGREGADO
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'adminpanel/producto_editar.html', {'form': form, 'producto': producto})

@staff_member_required
def promociones(request):
    if request.method == 'POST':
        form = PromocionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Promoción creada con éxito!')
            return redirect('adminpanel:promociones') # <--- PREFIJO AGREGADO
        else:
             messages.error(request, 'Error al crear la promoción. Revisa los datos.')
    else:
        form = PromocionForm()

    promociones_bd = Promocion.objects.all()

    ctx = {
        'promociones': promociones_bd,
        'form': form
    }
    return render(request, 'adminpanel/promociones.html', ctx)

@staff_member_required
def editar_promocion(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    if request.method == 'POST':
        form = PromocionForm(request.POST, request.FILES, instance=promocion)
        if form.is_valid():
            form.save()
            messages.success(request, 'Promoción actualizada correctamente.')
            return redirect('adminpanel:promociones') # <--- PREFIJO AGREGADO
    else:
        form = PromocionForm(instance=promocion)
    
    return render(request, 'adminpanel/promocion_editar.html', {'form': form, 'promocion': promocion})

@staff_member_required
def eliminar_promocion(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    if request.method == 'POST':
        promocion.delete()
        messages.success(request, 'Promoción eliminada.')
    return redirect('adminpanel:promociones') # <--- PREFIJO AGREGADO