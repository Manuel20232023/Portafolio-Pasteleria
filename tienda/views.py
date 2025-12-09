import random
from decimal import Decimal, ROUND_HALF_UP

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse, reverse_lazy
from django.contrib.auth.views import PasswordResetView
from django.utils import timezone
from django.db.models import Q

from .forms import RegistroForm, EmailAuthenticationForm
from adminpanel.models import Producto, Promocion, Pedido, DetallePedido

# TRANSBANK SDK 6.1.0
from transbank.common.options import WebpayOptions
from transbank.webpay.webpay_plus.transaction import Transaction


# ============================================================
# FUNCIONES DE CARRITO
# ============================================================
def _get_carrito(request):
    return request.session.get('carrito', {})


def _save_carrito(request, carrito):
    request.session['carrito'] = carrito
    request.session.modified = True


def _carrito_cuenta_items(request):
    return sum(int(item['cantidad']) for item in _get_carrito(request).values())


# ------------ PROMOCIONES (ÚNICA LÓGICA VÁLIDA) -------------
def _aplicar_promocion_a_item(item):
    """
    Calcula subtotal con y sin promo para un item del carrito.
    Soporta distintos valores en promo.tipo:
      - 2x1 / two_for_one / 2 x 1
      - porcentaje / percentage / descuento_porcentaje
      - segunda_unidad / second_unit_pct / descuento_segunda_unidad
    """
    producto = Producto.objects.get(pk=item['id'])
    cantidad = int(item['cantidad'])
    precio_unitario = Decimal(str(item['precio']))
    subtotal_base = precio_unitario * cantidad  

    hoy = timezone.now().date()

    promo = (
        Promocion.objects.filter(activa=True, producto=producto)
        .filter(
            Q(activo_desde__lte=hoy) | Q(activo_desde__isnull=True),
            Q(activo_hasta__gte=hoy) | Q(activo_hasta__isnull=True),
        )
        .first()
    )

    subtotal_desc = subtotal_base
    descuento = Decimal('0')

    if promo:
        tipo_norm = (promo.tipo or "").strip().lower()

        # -------- 2x1 --------
        if tipo_norm in ["2x1", "2 x 1", "two_for_one"] and cantidad >= 2:
            pares = cantidad // 2
            resto = cantidad % 2
            pagar_por = pares + resto    
            subtotal_desc = precio_unitario * pagar_por
            descuento = subtotal_base - subtotal_desc

        # -------- % sobre todo --------
        elif tipo_norm in ["porcentaje", "percentage", "descuento_porcentaje"] and promo.porcentaje:
            pct = Decimal(str(promo.porcentaje))
            subtotal_desc = subtotal_base * (Decimal("1") - pct / Decimal("100"))
            descuento = subtotal_base - subtotal_desc

        # -------- % en segunda unidad --------
        elif tipo_norm in [
            "segunda_unidad",
            "second_unit_pct",
            "descuento_segunda_unidad",
            "segunda unidad",
        ] and promo.porcentaje_segunda_unidad and cantidad >= 2:
            pct2 = Decimal(str(promo.porcentaje_segunda_unidad))
            pares = cantidad // 2
            resto = cantidad % 2

            precio_par = precio_unitario + (
                precio_unitario * (Decimal("1") - pct2 / Decimal("100"))
            )

            subtotal_desc = precio_par * pares + precio_unitario * resto
            descuento = subtotal_base - subtotal_desc

    return {
        "promo": promo,
        "subtotal_base": subtotal_base,
        "subtotal_desc": subtotal_desc,
        "descuento": descuento,
    }

def _aplicar_promos_a_carrito(carrito):
    """
    Recalcula subtotales y total del carrito aplicando las promociones activas.

    Soporta:
      - promos por producto (promo.producto)
      - promos por categoría usando categoria_objetivo
      - promos por categoría usando enlace_categoria
      - promos globales (categoria_objetivo = 'all')
    """
    hoy = timezone.localdate()
    total = Decimal('0')

    for key, item in list(carrito.items()):
        producto_id = int(item['id'])
        cantidad = int(item['cantidad'])
        precio_unit = Decimal(str(item['precio'])) 

        try:
            producto = Producto.objects.get(pk=producto_id)
        except Producto.DoesNotExist:
            del carrito[key]
            continue

        categoria = producto.categoria

        subtotal_base = precio_unit * cantidad
        item['subtotal_base'] = float(subtotal_base)

        item['tiene_promo'] = False
        item['etiqueta_promo'] = ''
        item['descuento'] = 0
        subtotal_final = subtotal_base

        # ------ BUSCAR PROMOS CANDIDATAS ------
        candidatos = (
            Promocion.objects.filter(activa=True)
            .filter(
                Q(producto=producto)
                | Q(categoria_objetivo=categoria)
                | Q(enlace_categoria=categoria)
                | Q(categoria_objetivo='all')
            )
            .filter(
                Q(activo_desde__isnull=True) | Q(activo_desde__lte=hoy),
                Q(activo_hasta__isnull=True) | Q(activo_hasta__gte=hoy),
            )
        )

        promo_aplicable = None
        for promo in candidatos:
            if promo.hasta_agotar_stock and promo.producto:
                if promo.producto.stock <= 0:
                    continue

            promo_aplicable = promo
            break

        # ------ APLICAR LA PROMO SI EXISTE ------
        if promo_aplicable:
            tipo = (promo_aplicable.tipo or '').lower()
            descuento = Decimal('0')

            # 2x1
            if tipo == '2x1':
                if cantidad >= 2:
                    pares = cantidad // 2
                    unidades_pagadas = cantidad - pares   
                    subtotal_final = precio_unit * unidades_pagadas
                    descuento = subtotal_base - subtotal_final

            # % a todo
            elif tipo == 'porcentaje' and promo_aplicable.porcentaje:
                porc = Decimal(str(promo_aplicable.porcentaje)) / Decimal('100')
                descuento = subtotal_base * porc
                subtotal_final = subtotal_base - descuento

            # % en la segunda unidad
            elif (
                tipo == 'segunda_unidad'
                and promo_aplicable.porcentaje_segunda_unidad
                and cantidad >= 2
            ):
                pares = cantidad // 2
                resto = cantidad % 2
                porc2 = Decimal(str(promo_aplicable.porcentaje_segunda_unidad)) / Decimal('100')

                descuento_por_par = precio_unit * porc2
                descuento = descuento_por_par * pares
                subtotal_final = subtotal_base - descuento

            if descuento > 0:
                item['tiene_promo'] = True
                item['etiqueta_promo'] = promo_aplicable.etiqueta or promo_aplicable.titulo
                item['descuento'] = float(descuento)

        # Guardar subtotal final
        item['subtotal'] = float(subtotal_final)
        total += subtotal_final

    return float(total)

# ============================================================
# PÁGINAS PRINCIPALES
# ============================================================
def home(request):
    destacados = Producto.objects.filter(destacado=True)[:6]
    promos_bd = Promocion.objects.filter(activa=True)
    return render(request, 'tienda/home.html', {
        'promos': promos_bd,
        'destacados': destacados,
        'carrito_count': _carrito_cuenta_items(request)
    })


def nosotros(request):
    return render(request, 'tienda/nosotros.html', {
        'carrito_count': _carrito_cuenta_items(request)
    })


def productos_index(request):
    categorias = {
        'vitrina': 'Repostería de vitrina',
        'postres': 'Postres',
        'tortas': 'Tortas'
    }

    promociones = Promocion.objects.filter(activa=True)

    return render(request, 'tienda/productos/index.html', {
        'categorias': categorias,
        'promociones': promociones,
        'carrito_count': _carrito_cuenta_items(request),
    })


def productos_categoria(request, slug):
    productos = Producto.objects.filter(categoria=slug)
    nombres_cat = {
        'vitrina': 'Repostería de vitrina',
        'tortas': 'Tortas',
        'postres': 'Postres'
    }
    promociones_cat = Promocion.objects.filter(activa=True, enlace_categoria=slug)

    return render(request, 'tienda/productos/categoria.html', {
        'categoria_slug': slug,
        'categoria_nombre': nombres_cat.get(slug, slug.capitalize()),
        'productos': productos,
        'promociones': promociones_cat,
        'carrito_count': _carrito_cuenta_items(request),
    })


def producto_detalle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return render(request, 'tienda/producto_detalle.html', {
        'producto': producto,
        'carrito_count': _carrito_cuenta_items(request)
    })


def buscar(request):
    q = request.GET.get('q', '').strip()
    resultados = Producto.objects.filter(nombre__icontains=q) if q else []
    return render(request, 'tienda/buscar.html', {
        'query': q,
        'resultados': resultados,
        'carrito_count': _carrito_cuenta_items(request)
    })


# ============================================================
# CARRITO
# ============================================================
def carrito_ver(request):
    carrito = _get_carrito(request)

    if not carrito:
        return render(request, 'tienda/carrito/ver.html', {
            'carrito': carrito,
            'total': 0,
            'carrito_count': _carrito_cuenta_items(request)
        })

    total = _aplicar_promos_a_carrito(carrito)
    _save_carrito(request, carrito)

    return render(request, 'tienda/carrito/ver.html', {
        'carrito': carrito,
        'total': total,
        'carrito_count': _carrito_cuenta_items(request)
    })


def carrito_agregar(request, pid):
    producto = get_object_or_404(Producto, pk=pid)
    carrito = _get_carrito(request)
    str_id = str(pid)

    if producto.stock <= 0:
        messages.error(request, f"'{producto.nombre}' está agotado.")
        return redirect(request.META.get('HTTP_REFERER', 'tienda:productos'))

    cantidad_actual = carrito.get(str_id, {}).get('cantidad', 0)

    if cantidad_actual >= producto.stock:
        messages.warning(
            request,
            f"Ya agregaste el máximo disponible de '{producto.nombre}' (stock: {producto.stock})."
        )
        return redirect(request.META.get('HTTP_REFERER', 'tienda:productos'))

    if str_id in carrito:
        carrito[str_id]['cantidad'] += 1
    else:
        img_url = producto.imagen.url if producto.imagen else ''
        carrito[str_id] = {
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': float(producto.precio), 
            'imagen': img_url,
            'cantidad': 1,
        }

    _save_carrito(request, carrito)
    messages.success(request, f"{producto.nombre} agregado al carrito.")
    return redirect(request.META.get('HTTP_REFERER', 'tienda:productos'))


def carrito_eliminar(request, pid):
    carrito = _get_carrito(request)
    str_id = str(pid)

    if str_id in carrito:
        del carrito[str_id]
        _save_carrito(request, carrito)
        messages.warning(request, "Producto eliminado del carrito.")

    return redirect('tienda:carrito')


def carrito_vaciar(request):
    _save_carrito(request, {})
    messages.info(request, "Carrito vaciado.")
    return redirect('tienda:carrito')


# ============================================================
# CHECKOUT
# ============================================================
@login_required
def checkout(request):
    carrito = _get_carrito(request)

    if not carrito:
        messages.info(request, "El carrito está vacío.")
        return redirect('tienda:productos')

    # Validación de stock antes del pago
    for item in carrito.values():
        producto = Producto.objects.get(id=int(item['id']))
        cantidad = int(item['cantidad'])

        if producto.stock < cantidad:
            messages.error(
                request,
                f"No hay suficiente stock para '{producto.nombre}'. "
                f"Stock disponible: {producto.stock}, solicitado: {cantidad}."
            )
            return redirect('tienda:carrito')

    # Recalcular con promociones 
    total = _aplicar_promos_a_carrito(carrito)
    _save_carrito(request, carrito)

    return render(request, 'tienda/checkout.html', {
        'carrito': carrito,
        'total': total,
        'carrito_count': _carrito_cuenta_items(request)
    })


# ============================================================
# LOGIN Y REGISTRO
# ============================================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect('adminpanel:panel_home') if request.user.is_staff else redirect('tienda:home')

    form = EmailAuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"¡Bienvenido {user.first_name or user.username}!")

        next_url = request.GET.get('next')
        if user.is_staff:
            return redirect('adminpanel:panel_home')
        if next_url:
            return redirect(next_url)

        return redirect('tienda:home')

    return render(request, 'tienda/cuenta/login.html', {'form': form})


def registro_view(request):
    if request.user.is_authenticated:
        return redirect('tienda:home')

    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()

        username = user.get_username()
        password = form.cleaned_data.get('password1')

        user_auth = authenticate(request, username=username, password=password)

        if user_auth is not None:
            login(request, user_auth)
        else:
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        # Enviar correo de bienvenida
        try:
            send_mail(
                subject='¡Bienvenido a Sweet Blessing!',
                message=f'Hola {user.first_name}, gracias por registrarte en Sweet Blessing.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            print("Error enviando correo:", e)

        messages.success(request, 'Cuenta creada con éxito.')
        return redirect('tienda:home')

    return render(request, 'tienda/cuenta/registro.html', {'form': form})


def salir_view(request):
    logout(request)
    messages.info(request, "Sesión cerrada.")
    return redirect('tienda:home')


# ============================================================
#  WEBPAY — SDK 6.1.0
# ============================================================
@login_required
def webpay_iniciar(request):
    carrito = _get_carrito(request)

    if not carrito:
        messages.info(request, "El carrito está vacío.")
        return redirect('tienda:productos')

    # Aplicar promociones antes de calcular el total
    total = _aplicar_promos_a_carrito(carrito)
    _save_carrito(request, carrito)

    if total <= 0:
        messages.error(request, "Total inválido.")
        return redirect('tienda:carrito')

    pedido = Pedido.objects.create(
        usuario=request.user,
        total=Decimal(str(total)),
        estado='pendiente'
    )

    request.session['pedido_webpay_id'] = pedido.id

    if not request.session.session_key:
        request.session.create()

    session_id = request.session.session_key
    buy_order = str(pedido.id)
    return_url = request.build_absolute_uri(reverse('tienda:webpay_retorno'))

    try:
        options = WebpayOptions(
            commerce_code=settings.WEBPAY_PLUS_COMMERCE_CODE,
            api_key=settings.WEBPAY_PLUS_API_KEY,
            integration_type="INTEGRATION"
        )
        tx = Transaction(options)
        amount_int = int(round(total))

        response = tx.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=amount_int,
            return_url=return_url
        )

        return render(request, "tienda/webpay/redireccion.html", {
            'url': response["url"],
            'token': response["token"]
        })

    except Exception as e:
        print("ERROR WEBPAY:", e)
        messages.error(request, f"Error al iniciar Webpay: {e}")
        return redirect('tienda:checkout')


def webpay_retorno(request):
    token = request.POST.get("token_ws") or request.GET.get("token_ws")
    pedido_id = request.session.get('pedido_webpay_id')

    # Caso: falta token o id de pedido
    if not token or not pedido_id:
        motivo = "La transacción fue anulada o faltan datos (token/pedido)."
        return render(request, "tienda/webpay/error_pago.html", {
            "motivo": motivo,
            "carrito_count": _carrito_cuenta_items(request),
        })

    try:
        options = WebpayOptions(
            commerce_code=settings.WEBPAY_PLUS_COMMERCE_CODE,
            api_key=settings.WEBPAY_PLUS_API_KEY,
            integration_type="INTEGRATION"
        )
        tx = Transaction(options)
        response = tx.commit(token)

        pedido = Pedido.objects.get(id=pedido_id)

        status = response.get("status")
        response_code = response.get("response_code") or response.get("responseCode") or 1

        # Pago autorizado
        if status == "AUTHORIZED" or str(response_code) == "0":
            pedido.estado = "pagado"
            pedido.save()
            carrito = request.session.get('carrito', {})

            detalles_cliente_lines = []
            detalles_empresa_lines = []

            # Guarda el detalle del pedido y arma líneas de correo usando DESCUENTOS
            for item in carrito.values():
                producto = Producto.objects.get(id=int(item['id']))
                cantidad = int(item['cantidad'])

                # Datos base
                precio_base = Decimal(str(item['precio']))  
                subtotal_base = precio_base * cantidad

                # Datos calculados por _aplicar_promos_a_carrito
                subtotal_final = Decimal(str(item.get('subtotal', subtotal_base)))
                descuento_total = Decimal(str(item.get('descuento', 0)))
                etiqueta = item.get('etiqueta_promo') or ''

                # Precio unitario final que se guardará en DetallePedido
                if cantidad > 0:
                    precio_unit_final = (subtotal_final / cantidad).quantize(
                        Decimal('1.'), rounding=ROUND_HALF_UP
                    )
                else:
                    precio_unit_final = precio_base

                # Crear detalle de pedido con PRECIO FINAL
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_unit_final
                )

                # Actualizar stock
                producto.stock = max(0, producto.stock - cantidad)
                producto.save()

                # ----- texto para correo cliente -----
                if descuento_total > 0:
                    linea_cliente = (
                        f"- {producto.nombre} (x{cantidad}) → "
                        f"${subtotal_final:.0f} "
                        f"(antes: ${subtotal_base:.0f}, ahorro: ${descuento_total:.0f}"
                        f"{' - ' + etiqueta if etiqueta else ''})"
                    )
                else:
                    linea_cliente = f"- {producto.nombre} (x{cantidad}) → ${subtotal_final:.0f}"

                detalles_cliente_lines.append(linea_cliente)

                # ----- texto para correo empresa -----
                linea_empresa = (
                    f"- {producto.nombre} | Cant: {cantidad} | "
                    f"P. base: ${precio_base:.0f} | Subtotal base: ${subtotal_base:.0f} | "
                    f"Descuento: ${descuento_total:.0f} | Subtotal final: ${subtotal_final:.0f}"
                    f"{' | Promo: ' + etiqueta if etiqueta else ''}"
                )
                detalles_empresa_lines.append(linea_empresa)

            # Limpia sesión (carrito + id de pedido)
            request.session['carrito'] = {}
            if 'pedido_webpay_id' in request.session:
                del request.session['pedido_webpay_id']

            # ============================================================
            # ENVÍO DE CORREOS DIFERENTES A CLIENTE Y EMPRESA
            # ============================================================
            EMAIL_EMPRESA = "sweetblessingchile@gmail.com"

            detalles_cliente = "\n".join(detalles_cliente_lines)
            detalles_empresa = "\n".join(detalles_empresa_lines)

            total = pedido.total
            nombre_cliente = pedido.usuario.first_name or pedido.usuario.username

            # 1. CORREO PARA EL CLIENTE
            email_cliente_subject = "Comprobante de tu compra en Sweet Blessing 🎂"
            email_cliente_body = (
                f"¡Hola {nombre_cliente}!\n\n"
                f"Tu pago del pedido #{pedido.id} ha sido recibido exitosamente 🎉\n\n"
                f"🧁 Detalle de tu compra:\n{detalles_cliente}\n\n"
                f"💵 Total pagado: ${total}\n\n"
                "Tu pedido está siendo preparado con cariño ❤️\n\n"
                "Sweet Blessing"
            )

            send_mail(
                email_cliente_subject,
                email_cliente_body,
                settings.DEFAULT_FROM_EMAIL,
                [pedido.usuario.email],
                fail_silently=False,
            )

            # 2. CORREO PARA LA EMPRESA
            email_empresa_subject = f"Nuevo pedido pagado #{pedido.id}"
            email_empresa_body = (
                f"El cliente {nombre_cliente} ha realizado la siguiente compra:\n\n"
                f"{detalles_empresa}\n\n"
                f"Total cobrado: ${total}\n\n"
                "Revisar sistema para gestionar el pedido."
            )

            send_mail(
                email_empresa_subject,
                email_empresa_body,
                settings.DEFAULT_FROM_EMAIL,
                [EMAIL_EMPRESA],
                fail_silently=False,
            )

            return render(request, "tienda/webpay/exito.html", {
                "pedido": pedido,
                "response": response,
                "carrito_count": _carrito_cuenta_items(request),  
            })

        # Pago rechazado por Webpay
        else:
            pedido.estado = "rechazado"
            pedido.save()
            motivo = "El pago fue rechazado por Webpay. Por favor verifica los datos de tu tarjeta o intenta nuevamente."
            return render(request, "tienda/webpay/rechazado.html", {
                "motivo": motivo,
                "carrito_count": _carrito_cuenta_items(request),
            })

    except Exception as e:
        print("ERROR WEBPAY RETORNO:", str(e))
        motivo = "Ocurrió un error inesperado al procesar el pago. Si el problema continúa, contáctanos."
        return render(request, "tienda/webpay/error_pago.html", {
            "motivo": motivo,
            "carrito_count": _carrito_cuenta_items(request),
        })

# ============================================================
# Cuentas  (restablecer contraseña)
# ============================================================
class CustomPasswordResetView(PasswordResetView):
    template_name = 'cuenta/restablecer.html'
    email_template_name = 'cuenta/password_reset_email.html'
    subject_template_name = 'cuenta/password_reset_subject.txt'
    success_url = reverse_lazy('cuenta:password_reset_done')
