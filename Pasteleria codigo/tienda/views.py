import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import RegistroForm
from adminpanel.models import Producto, Promocion
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.error.transbank_error import TransbankError
from django.core.mail import send_mail
from django.conf import settings
from .forms import EmailAuthenticationForm

# ====== Utilidades carrito ======
def _get_carrito(request):
    return request.session.get('carrito', {})

def _save_carrito(request, carrito):
    request.session['carrito'] = carrito
    request.session.modified = True

def _carrito_cuenta_items(request):
    # Cuenta la cantidad TOTAL de productos (ej: 2 donas + 1 torta = 3 items)
    return sum(item['cantidad'] for item in _get_carrito(request).values())

# ====== Vistas Públicas ======
def home(request):
    # 1. Productos destacados reales desde la BD
    destacados = Producto.objects.filter(destacado=True)[:6]
    
    # 2. Promociones reales y ACTIVAS desde la BD
    promos_bd = Promocion.objects.filter(activa=True)
    
    ctx = {
        'promos': promos_bd,     # Pasamos las promos reales a la plantilla
        'destacados': destacados,
        'carrito_count': _carrito_cuenta_items(request),
    }
    return render(request, 'tienda/home.html', ctx)

def nosotros(request):
    return render(request, 'tienda/nosotros.html', {'carrito_count': _carrito_cuenta_items(request)})

def productos_index(request):
    # Categorías 'quemadas' para la vista principal de categorías
    categorias = {
        'vitrina': 'Repostería de vitrina',
        'postres': 'Postres',
        'tortas': 'Tortas',
    }
    return render(request, 'tienda/productos/index.html', {
        'categorias': categorias,
        'carrito_count': _carrito_cuenta_items(request)
    })

def productos_categoria(request, slug):
    # Filtra productos reales por la categoría seleccionada
    productos = Producto.objects.filter(categoria=slug)
    nombres_cat = {'vitrina': 'Repostería de vitrina', 'tortas': 'Tortas', 'postres': 'Postres'}
    
    ctx = {
        'categoria_slug': slug,
        'categoria_nombre': nombres_cat.get(slug, slug.capitalize()),
        'productos': productos,
        'carrito_count': _carrito_cuenta_items(request),
    }
    return render(request, 'tienda/productos/categoria.html', ctx)

def producto_detalle(request, pk):
    # Busca el producto por su ID (pk). Si no existe, lanza error 404.
    producto = get_object_or_404(Producto, pk=pk)
    
    ctx = {
        'producto': producto,
        'carrito_count': _carrito_cuenta_items(request) # Para seguir mostrando el contador del carrito
    }
    return render(request, 'tienda/producto_detalle.html', ctx)

def buscar(request):
    q = request.GET.get('q', '').strip()
    resultados = []
    if q:
        # Busca por nombre que contenga 'q' (insensible a mayúsculas/minúsculas)
        resultados = Producto.objects.filter(nombre__icontains=q)
    
    ctx = {'query': q, 'resultados': resultados, 'carrito_count': _carrito_cuenta_items(request)}
    return render(request, 'tienda/buscar.html', ctx)

# ====== Carrito (Lógica Corregida) ======
def carrito_ver(request):
    carrito = _get_carrito(request)
    # Aseguramos que precio y cantidad sean números para la suma correcta
    total = sum(int(item['precio']) * int(item['cantidad']) for item in carrito.values())
    
    return render(request, 'tienda/carrito/ver.html', {
        'carrito': carrito, 
        'total': total, 
        'carrito_count': _carrito_cuenta_items(request)
    })

def carrito_agregar(request, pid):
    # Buscamos el producto real en la BD
    producto = get_object_or_404(Producto, pk=pid)
    carrito = _get_carrito(request)
    str_id = str(pid) # Usamos string para la clave del diccionario de sesión

    if str_id in carrito:
        carrito[str_id]['cantidad'] += 1
    else:
        # Guardamos los datos básicos en sesión
        img_url = producto.imagen.url if producto.imagen else ''
        carrito[str_id] = {
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': producto.precio,
            'imagen': img_url,
            'cantidad': 1,
        }
    _save_carrito(request, carrito)
    messages.success(request, f"Agregado {producto.nombre} al carrito.")
    # Redirige a la misma página donde estaba el usuario
    return redirect(request.META.get('HTTP_REFERER', 'tienda:productos'))

def carrito_eliminar(request, pid):
    carrito = _get_carrito(request)
    str_id = str(pid)
    if str_id in carrito:
        del carrito[str_id]
        _save_carrito(request, carrito)
        messages.warning(request, 'Producto eliminado.')
    return redirect('tienda:carrito')

def carrito_vaciar(request):
    _save_carrito(request, {})
    messages.info(request, 'Carrito vaciado.')
    return redirect('tienda:carrito')

@login_required
def checkout(request):
    carrito = _get_carrito(request)
    if not carrito:
        messages.info(request, "El carrito está vacío.")
        return redirect('tienda:productos')

    total = sum(int(item['precio']) * int(item['cantidad']) for item in carrito.values())

    # Si la petición es POST, significa que el usuario presionó "Confirmar Pago"
    if request.method == 'POST':
        # 1. Crear la cabecera del pedido
        pedido = Pedido.objects.create(
            usuario=request.user,
            total=total,
            estado='pagado' # Asumimos pagado para este prototipo
        )

        # 2. Crear los detalles y descontar stock
        for item_id, item_data in carrito.items():
            producto = Producto.objects.get(id=int(item_data['id']))
            
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=item_data['cantidad'],
                precio_unitario=int(item_data['precio'])
            )
            
            # Opcional: Descontar stock
            producto.stock -= item_data['cantidad']
            producto.save()

        # 3. Vaciar carrito y notificar
        _save_carrito(request, {})
        messages.success(request, f"¡Pedido #{pedido.id} realizado con éxito!")
        return redirect('tienda:home')

    return render(request, 'tienda/checkout.html', {
        'carrito': carrito, 
        'total': total, 
        'carrito_count': _carrito_cuenta_items(request)
    })

# ====== Cuentas ======
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('adminpanel:dashboard')
        return redirect('tienda:home')

    # USAMOS EL NUEVO FORMULARIO AQUÍ:
    form = EmailAuthenticationForm(request, data=request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'¡Bienvenido {user.first_name or user.username}!') # Usamos first_name si existe, es más amigable
        
        if user.is_staff:
             return redirect('adminpanel:dashboard')
        
        next_url = request.GET.get('next')
        return redirect(next_url or 'tienda:home')

    return render(request, 'tienda/cuenta/login.html', {'form': form})

def registro_view(request):
    if request.user.is_authenticated:
        return redirect('tienda:home')

    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)

        # === NUEVO: ENVIAR CORREO DE BIENVENIDA ===
        try:
            send_mail(
                subject='¡Bienvenido a Sweet Blessing! 🎂',
                message=f'Hola {user.first_name},\n\nGracias por registrarte en nuestra pastelería. Esperamos que disfrutes nuestros productos.\n\nAtte,\nEl equipo de Sweet Blessing.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True, # Para que no falle el registro si el correo falla
            )
        except Exception as e:
            # Opcional: registrar el error en consola si lo necesitas
            print(f"Error enviando correo: {e}")
        # ==========================================

        messages.success(request, 'Cuenta creada con éxito.')
        return redirect('tienda:home')

    return render(request, 'tienda/cuenta/registro.html', {'form': form})
def salir_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada.')
    return redirect('tienda:home')

@login_required
def checkout(request):
    """ Muestra el resumen antes de ir a Webpay """
    carrito = _get_carrito(request)
    if not carrito:
        messages.info(request, "El carrito está vacío.")
        return redirect('tienda:productos')

    total = sum(int(item['precio']) * int(item['cantidad']) for item in carrito.values())
    
    return render(request, 'tienda/checkout.html', {
        'carrito': carrito, 
        'total': total, 
        'carrito_count': _carrito_cuenta_items(request)
    })

@login_required
def webpay_iniciar(request):
    """ Crea el pedido 'pendiente' e inicia la transacción en Transbank """
    carrito = _get_carrito(request)
    if not carrito:
        return redirect('tienda:productos')

    total = sum(int(item['precio']) * int(item['cantidad']) for item in carrito.values())

    # 1. Crear el pedido como PENDIENTE antes de ir a Webpay
    pedido = Pedido.objects.create(
        usuario=request.user,
        total=total,
        estado='pendiente' # Importante: empieza pendiente
    )
    
    # Guardamos el ID del pedido en la sesión para recordarlo al volver
    request.session['pedido_webpay_id'] = pedido.id

    # 2. Iniciar transacción con Transbank (Entorno de PRUEBAS por defecto)
    buy_order = str(pedido.id)
    session_id = request.session.session_key or str(random.randint(1000, 9999))
    amount = total
    return_url = request.build_absolute_uri('/webpay/retorno/') # URL completa de retorno

    try:
        tx = Transaction()
        response = tx.create(buy_order, session_id, amount, return_url)
        
        # 3. Redirigir al usuario al formulario de pago de Webpay
        return render(request, 'tienda/webpay/redireccion.html', {
            'url': response['url'], 
            'token': response['token']
        })
    except TransbankError as e:
        messages.error(request, f"Error al conectar con Webpay: {e.message}")
        return redirect('tienda:checkout')

# No usamos @login_required aquí porque a veces la sesión se pierde brevemente en el retorno
def webpay_retorno(request):
    """ Recibe la respuesta de Transbank, valida y confirma el pedido """
    # Webpay retorna el token por GET (o POST a veces, pero standard es GET en SDK moderno)
    token = request.GET.get('token_ws') or request.POST.get('token_ws')
    pedido_id = request.session.get('pedido_webpay_id')

    if not token or not pedido_id:
        # Caso: el usuario anuló la compra en el formulario Webpay
        if pedido_id:
             pedido = Pedido.objects.get(id=pedido_id)
             pedido.estado = 'anulado'
             pedido.save()
        messages.error(request, "La transacción fue anulada.")
        return redirect('tienda:carrito')

    try:
        # 1. Confirmar la transacción con Transbank
        tx = Transaction()
        response = tx.commit(token) # Aquí Transbank nos dice si pasó o no
        
        status = response.get('status')
        pedido = Pedido.objects.get(id=pedido_id)

        if status == 'AUTHORIZED' and response.get('response_code') == 0:
            # --- PAGO EXITOSO ---
            pedido.estado = 'pagado'
            pedido.save()

            # Movemos los items del carrito a la tabla DetallePedido
            carrito = _get_carrito(request)
            for item_data in carrito.values():
                producto = Producto.objects.get(id=int(item_data['id']))
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=item_data['cantidad'],
                    precio_unitario=int(item_data['precio'])
                )
                # Descontar stock
                if producto.stock >= item_data['cantidad']:
                     producto.stock -= item_data['cantidad']
                     producto.save()

            # Vaciar carrito
            _save_carrito(request, {})
            del request.session['pedido_webpay_id']
            
            messages.success(request, f"¡Pago exitoso! Pedido #{pedido.id} confirmado.")
            return render(request, 'tienda/webpay/exito.html', {'pedido': pedido, 'response': response})
        else:
            # --- PAGO RECHAZADO ---
            pedido.estado = 'rechazado'
            pedido.save()
            messages.error(request, "El pago fue rechazado por el banco.")
            return redirect('tienda:checkout')

    except TransbankError as e:
        messages.error(request, "Ocurrió un error al validar la transacción.")
        return redirect('tienda:checkout')