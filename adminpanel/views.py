import csv
import json
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
from openpyxl import Workbook
from django.utils import timezone
from datetime import timedelta
import json
from datetime import timedelta


@staff_member_required
def panel_home(request):
    """Inicio del panel: solo las tarjetas de Reportes, Pedidos, Productos, Clientes."""
    return render(request, 'adminpanel/panel_home.html')

@staff_member_required
def dashboard(request):
    hoy = timezone.now().date()
    hace_7 = hoy - timedelta(days=6)
    hace_30 = hoy - timedelta(days=30)

    # Métricas rápidas
    total_pedidos = Pedido.objects.count()
    pedidos_hoy = Pedido.objects.filter(fecha__date=hoy).count()
    ventas_hoy = Pedido.objects.filter(fecha__date=hoy).aggregate(
        total=Sum('total')
    )['total'] or 0
    pedidos_pendientes = Pedido.objects.filter(estado='PENDIENTE').count()

    # Ventas últimos 7 días (para el gráfico)
    ventas_qs = (
        Pedido.objects
        .filter(fecha__date__range=[hace_7, hoy])
        .values('fecha__date')
        .annotate(total_dia=Sum('total'))
        .order_by('fecha__date')
    )

    ventas_labels = [item['fecha__date'].strftime("%d-%m") for item in ventas_qs]
    ventas_data = [float(item['total_dia']) for item in ventas_qs]

    # Top productos últimos 30 días
    top_productos_qs = (
        DetallePedido.objects
        .filter(pedido__fecha__date__gte=hace_30)
        .values('producto__nombre')
        .annotate(
            cantidad_total=Sum('cantidad'),
            total_recaudado=Sum(F('cantidad') * F('precio_unitario'))
        )
        .order_by('-cantidad_total')[:10]
    )

    context = {
        'total_pedidos': total_pedidos,
        'pedidos_hoy': pedidos_hoy,
        'ventas_hoy': ventas_hoy,
        'pedidos_pendientes': pedidos_pendientes,
        'ventas_labels': json.dumps(ventas_labels),
        'ventas_data': json.dumps(ventas_data),
        'top_productos': top_productos_qs,
    }

    return render(request, 'adminpanel/dashboard.html', context)

@staff_member_required
def reportes(request):
    tipo_reporte = request.GET.get('tipo_reporte', 'ventas')
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')

    ventas_qs = Pedido.objects.all().order_by('-fecha')
    detalles_qs = DetallePedido.objects.all()

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

    if tipo_reporte == 'ventas':
        reporte = ventas_qs
        orden = None
    else:
        orden = request.GET.get('orden', 'cantidad_total')

        reporte = detalles_qs.values('producto__nombre').annotate(
            cantidad_total=Sum('cantidad'),
            total_recaudado=Sum(F('cantidad') * F('precio_unitario'))
        ).order_by('-cantidad_total')

    contexto = {
        'tipo_reporte': tipo_reporte,
        'reporte': reporte,
        'fecha_desde': fecha_desde or '',
        'fecha_hasta': fecha_hasta or '',
        'orden': orden,
    }
    return render(request, 'adminpanel/reporte.html', contexto)
    
def _obtener_datos_filtrados(request, tipo='ventas'):
    """
    Devuelve los datos filtrados por fecha según el tipo:
    - 'ventas'    -> queryset de Pedido
    - 'productos' -> queryset agregado por producto
    """

    fecha_desde = request.GET.get('fecha_desde') or request.GET.get('desde')
    fecha_hasta = request.GET.get('fecha_hasta') or request.GET.get('hasta')

    if tipo == 'ventas':
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

    # --------- productos ---------
    detalles_qs = DetallePedido.objects.all()

    if fecha_desde:
        fecha_d = parse_date(fecha_desde)
        if fecha_d:
            detalles_qs = detalles_qs.filter(pedido__fecha__date__gte=fecha_d)

    if fecha_hasta:
        fecha_h = parse_date(fecha_hasta)
        if fecha_h:
            detalles_qs = detalles_qs.filter(pedido__fecha__date__lte=fecha_h)

    reporte_productos = detalles_qs.values('producto__nombre').annotate(
        cantidad_total=Sum('cantidad'),
        total_recaudado=Sum(F('cantidad') * F('precio_unitario'))
    ).order_by('-cantidad_total')

    return reporte_productos

@staff_member_required
def descargar_reporte(request):
    tipo = request.GET.get('tipo', 'ventas')  

    fecha_desde = request.GET.get('fecha_desde') or request.GET.get('desde')
    fecha_hasta = request.GET.get('fecha_hasta') or request.GET.get('hasta')

    if tipo == 'productos':
        reporte = _obtener_datos_filtrados(request, tipo='productos')
        tipo_reporte = 'productos'
    else:
        reporte = _obtener_datos_filtrados(request, tipo='ventas')
        tipo_reporte = 'ventas'

    ctx = {
        'reporte': reporte,
        'tipo_reporte': tipo_reporte,
        'fecha_desde': fecha_desde,
        'fecha_hasta': fecha_hasta,
    }

    template = get_template('adminpanel/reporte_pdf.html')
    html = template.render(ctx)

    response = HttpResponse(content_type='application/pdf')
    filename = f"reporte_{tipo_reporte}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse('Error al generar PDF', status=500)
    return response

@staff_member_required
def descargar_reporte_excel(request):
    tipo = request.GET.get('tipo', 'ventas')

    if tipo == 'productos':
        reporte = _obtener_datos_filtrados(request, tipo='productos')

        wb = Workbook()
        ws = wb.active
        ws.title = "Productos"

        ws.append(["Producto", "Cantidad vendida", "Total recaudado"])

        for item in reporte:
            ws.append([
                item['producto__nombre'],
                item['cantidad_total'],
                item['total_recaudado'],
            ])

        filename = "reporte_productos.xlsx"

    else:
        ventas = _obtener_datos_filtrados(request, tipo='ventas')

        wb = Workbook()
        ws = wb.active
        ws.title = "Ventas"

        ws.append(["ID Pedido", "Fecha", "Cliente", "Total", "Estado"])

        for pedido in ventas:
            ws.append([
                pedido.id,
                pedido.fecha.strftime("%Y-%m-%d %H:%M"),
                pedido.usuario.username,
                pedido.total,
                pedido.get_estado_display(),
            ])

        filename = "reporte_ventas.xlsx"

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    wb.save(response)
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
            return redirect('adminpanel:productos') 
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
        return redirect('adminpanel:productos') 
    
    return redirect('adminpanel:productos') 

@staff_member_required
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('adminpanel:productos') 
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
            return redirect('adminpanel:promociones') 
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
            return redirect('adminpanel:promociones') 
    else:
        form = PromocionForm(instance=promocion)
    
    return render(request, 'adminpanel/promocion_editar.html', {'form': form, 'promocion': promocion})

@staff_member_required
def eliminar_promocion(request, pk):
    promocion = get_object_or_404(Promocion, pk=pk)
    if request.method == 'POST':
        promocion.delete()
        messages.success(request, 'Promoción eliminada.')
    return redirect('adminpanel:promociones') 