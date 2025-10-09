from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .forms import RegistroForm
from django.contrib.auth import logout
from django.shortcuts import redirect

# ====== Catálogo simulado (sin BD) ======
CATEGORIAS = {
    'vitrina': 'Repostería de vitrina',
    'postres': 'Postres',
    'tortas': 'Tortas',
}

CATALOGO = {
    # id: dict(...)
    'vit-1': {'id': 'vit-1', 'nombre': 'Berlines', 'precio': 1500, 'categoria': 'vitrina', 'imagen': 'tienda/img/vitrina1.jpg'},
    'vit-2': {'id': 'vit-2', 'nombre': 'Donas', 'precio': 1200, 'categoria': 'vitrina', 'imagen': 'tienda/img/vitrina2.jpg'},
    'pos-1': {'id': 'pos-1', 'nombre': 'Cheesecake Fresa', 'precio': 4500, 'categoria': 'postres', 'imagen': 'tienda/img/postre1.jpg'},
    'pos-2': {'id': 'pos-2', 'nombre': 'Brownie', 'precio': 2000, 'categoria': 'postres', 'imagen': 'tienda/img/postre2.jpg'},
    'tor-1': {'id': 'tor-1', 'nombre': 'Torta Chocolate', 'precio': 15000, 'categoria': 'tortas', 'imagen': 'tienda/img/torta1.jpg'},
    'tor-2': {'id': 'tor-2', 'nombre': 'Torta Frutilla', 'precio': 16000, 'categoria': 'tortas', 'imagen': 'tienda/img/torta2.jpg'},
}

# ====== Promociones simuladas ======
PROMOS = [
    {
        'titulo': '2x1 en Donas',
        'descripcion': 'Llévate 2 por el precio de 1 todos los lunes.',
        'imagen': 'tienda/img/promo_donas.jpg',
        'slug': 'vitrina',
        'etiqueta': '2x1'
    },
    {
        'titulo': '15% en Tortas',
        'descripcion': 'Descuento en toda la línea de tortas clásicas.',
        'imagen': 'tienda/img/promo_tortas.jpg',
        'slug': 'tortas',
        'etiqueta': '-15%'
    },
    {
        'titulo': 'Postres a $3.000',
        'descripcion': 'Promo de temporada en postres seleccionados.',
        'imagen': 'tienda/img/promo_postres.jpg',
        'slug': 'postres',
        'etiqueta': 'Oferta'
    },
]

def _items_por_categoria(slug):
    return [p for p in CATALOGO.values() if p['categoria'] == slug]

# ====== Utilidades carrito (en sesión) ======
def _get_carrito(request):
    return request.session.get('carrito', {})

def _save_carrito(request, carrito):
    request.session['carrito'] = carrito
    request.session.modified = True

def _carrito_cuenta_items(request):
    c = _get_carrito(request)
    return sum(item['cantidad'] for item in c.values())

# ====== Páginas ======
def home(request):
    ctx = {
        'promos': PROMOS,
        'destacados': list(CATALOGO.values())[:6],
        'carrito_count': _carrito_cuenta_items(request),
    }
    return render(request, 'tienda/home.html', ctx)

def nosotros(request):
    return render(request, 'tienda/nosotros.html', {'carrito_count': _carrito_cuenta_items(request)})

def productos_index(request):
    categorias = {
        'vitrina': 'Repostería de vitrina',
        'postres': 'Postres',
        'tortas': 'Tortas',
    }

    promociones = [
        {'nombre': 'Promo Chocolate', 'descuento': '20%', 'vigencia': 'Hasta 30/09/2025'},
        {'nombre': 'Promo Frutal', 'descuento': '15%', 'vigencia': 'Hasta 31/10/2025'},
        {'nombre': 'Promo Cumpleaños', 'descuento': '25%', 'vigencia': 'Hasta 31/12/2025'},
    ]

    return render(request, 'tienda/productos/index.html', {
        'categorias': categorias,
        'promociones': promociones
    })

def productos_categoria(request, slug):
    categoria_slug = slug  # normalizamos
    categoria_nombre = CATEGORIAS.get(categoria_slug, categoria_slug.capitalize())
    productos = [p for p in CATALOGO.values() if p['categoria'] == categoria_slug]

    ctx = {
        'categoria_slug': categoria_slug,
        'categoria_nombre': categoria_nombre,
        'productos': productos,
        'carrito_count': _carrito_cuenta_items(request),
    }
    return render(request, 'tienda/productos/categoria.html', ctx)

def buscar(request):
    q = request.GET.get('q', '').strip()
    resultados = []
    if q:
        q_lower = q.lower()
        resultados = [p for p in CATALOGO.values() if q_lower in p['nombre'].lower()]
    ctx = {'query': q, 'resultados': resultados, 'carrito_count': _carrito_cuenta_items(request)}
    return render(request, 'tienda/buscar.html', ctx)

# ====== Cuenta ======
def login_view(request):
    if request.user.is_authenticated:
        return redirect('tienda:home')
    form = AuthenticationForm(request, data=request.POST or None)
    # Agregar clases Bootstrap a los widgets
    form.fields['username'].widget.attrs.update({'class': 'form-control'})
    form.fields['password'].widget.attrs.update({'class': 'form-control'})
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, '¡Bienvenido!')
        next_url = request.GET.get('next') or 'tienda:home'
        return redirect(next_url)
    return render(request, 'tienda/cuenta/login.html', {'form': form, 'carrito_count': _carrito_cuenta_items(request)})

def registro_view(request):
    if request.user.is_authenticated:
        return redirect('tienda:home')
    form = UserCreationForm(request.POST or None)
    # Agregar clases Bootstrap a todos los campos del formulario
    for f in form.fields.values():
        f.widget.attrs.update({'class': 'form-control'})
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Cuenta creada con éxito.')
        return redirect('tienda:home')
    return render(request, 'tienda/cuenta/registro.html', {'form': form, 'carrito_count': _carrito_cuenta_items(request)})

def salir_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada.')
    return redirect('tienda:home')

# ====== Carrito ======
def carrito_ver(request):
    carrito = _get_carrito(request)
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    return render(request, 'tienda/carrito/ver.html', {
        'carrito': carrito, 'total': total, 'carrito_count': _carrito_cuenta_items(request)
    })

def carrito_agregar(request, pid):
    producto = CATALOGO.get(pid)
    if not producto:
        messages.error(request, 'Producto no encontrado.')
        return redirect('tienda:productos')
    carrito = _get_carrito(request)
    if pid in carrito:
        carrito[pid]['cantidad'] += 1
    else:
        carrito[pid] = {
            'id': pid,
            'nombre': producto['nombre'],
            'precio': producto['precio'],
            'imagen': producto['imagen'],
            'cantidad': 1,
        }
    _save_carrito(request, carrito)
    messages.success(request, f"Agregado {producto['nombre']} al carrito.")
    return redirect(request.META.get('HTTP_REFERER', 'tienda:productos'))

def carrito_eliminar(request, pid):
    carrito = _get_carrito(request)
    if pid in carrito:
        del carrito[pid]
        _save_carrito(request, carrito)
        messages.info(request, 'Producto eliminado del carrito.')
    return redirect('tienda:carrito')

def carrito_vaciar(request):
    _save_carrito(request, {})
    messages.info(request, 'Carrito vaciado.')
    return redirect('tienda:carrito')

@login_required
def checkout(request):
    carrito = _get_carrito(request)
    if not carrito:
        messages.info(request, 'Tu carrito está vacío.')
        return redirect('tienda:productos')
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    # Aquí luego conectarás el flujo real de pago
    return render(request, 'tienda/checkout.html', {
        'carrito': carrito, 'total': total, 'carrito_count': _carrito_cuenta_items(request)
    })

def registro_view(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada con éxito. Ahora puedes iniciar sesión.')
            return redirect('tienda:login')
    else:
        form = RegistroForm()
    return render(request, 'tienda/cuenta/registro.html', {'form': form})

def salir_view(request):
    logout(request)
    return redirect('tienda:home')