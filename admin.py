from flask import Flask, render_template_string, request, session, redirect, url_for
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('ADMIN_SECRET_KEY', 'cambia-esto-en-produccion-xK9#mP2!')

# --- CONFIGURACIÓN PRINCIPAL ---
RUTA_RESULTADOS = 'resultados.txt'
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'mundial2026')

# --- DATOS DEL TORNEO ---
GRUPOS = {
    'A': [('mx', 'México'), ('za', 'Sudáfrica'), ('kr', 'Corea del Sur'), ('cz', 'Chequia')],
    'B': [('ca', 'Canadá'), ('ba', 'Bosnia y Herzegovina'), ('qa', 'Qatar'), ('ch', 'Suiza')],
    'C': [('br', 'Brasil'), ('ma', 'Marruecos'), ('ht', 'Haití'), ('gb-sct', 'Escocia')],
    'D': [('us', 'Estados Unidos'), ('py', 'Paraguay'), ('au', 'Australia'), ('tr', 'Turquía')],
    'E': [('de', 'Alemania'), ('cw', 'Curazao'), ('ci', 'Costa de Marfil'), ('ec', 'Ecuador')],
    'F': [('nl', 'Países Bajos'), ('jp', 'Japón'), ('se', 'Suecia'), ('tn', 'Túnez')],
    'G': [('be', 'Bélgica'), ('eg', 'Egipto'), ('ir', 'Irán'), ('nz', 'Nueva Zelanda')],
    'H': [('es', 'España'), ('cv', 'Cabo Verde'), ('sa', 'Arabia Saudita'), ('uy', 'Uruguay')],
    'I': [('fr', 'Francia'), ('sn', 'Senegal'), ('iq', 'Irak'), ('no', 'Noruega')],
    'J': [('ar', 'Argentina'), ('dz', 'Argelia'), ('at', 'Austria'), ('jo', 'Jordania')],
    'K': [('pt', 'Portugal'), ('cd', 'RD Congo'), ('uz', 'Uzbekistán'), ('co', 'Colombia')],
    'L': [('gb-eng', 'Inglaterra'), ('hr', 'Croacia'), ('gh', 'Ghana'), ('pa', 'Panamá')]
}

# ==========================================
# PLANTILLA HTML DE LOGIN
# ==========================================
HTML_LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acceso Admin · Porra Mundial</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Poppins', sans-serif; background-color: #f2f9f5; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
        .login-card { background: white; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); padding: 2.5rem; width: 100%; max-width: 400px; }
        .header-banner { background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; padding: 1.2rem; border-radius: 12px; text-align: center; margin-bottom: 2rem; }
        .btn-primary-custom { background-color: #2563eb; border: none; border-radius: 8px; width: 100%; padding: 0.75rem; font-weight: 600; font-size: 1rem; }
        .btn-primary-custom:hover { background-color: #1d4ed8; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="header-banner">
            <h1 style="font-size:1.8rem; font-weight:700; margin:0;">⚙️ Admin</h1>
            <p class="m-0 mt-1 opacity-75 small">Panel de Control · Porra Mundial</p>
        </div>
        {% if error %}
        <div class="alert alert-danger text-center small">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label fw-semibold">Contraseña</label>
                <input type="password" name="password" class="form-control form-control-lg" autofocus required>
            </div>
            <button type="submit" class="btn btn-primary-custom text-white">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

# ==========================================
# PLANTILLA HTML DEL PANEL DE ADMINISTRADOR
# ==========================================
HTML_ADMIN = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Control · Porra Mundial</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <style>
        body { font-family: 'Poppins', sans-serif; background-color: #f2f9f5; color: #2c3e50; }
        .header-banner { background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); color: white; padding: 1.2rem; border-radius: 15px; box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2); }
        .header-banner h1 { font-size: 2.2rem; font-weight: 700; letter-spacing: 1px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); margin: 0; }
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: none; }
        .btn-primary-custom { background-color: #2563eb; border: none; border-radius: 8px; transition: all 0.3s ease; }
        .btn-primary-custom:hover { background-color: #1d4ed8; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(37, 99, 235, 0.3); }
        .team-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; padding: 6px; background: white; border: 1px solid #dee2e6; border-radius: 6px; }
        .pos-select { width: 80px; font-weight: bold; text-align: center; }
        
        /* Estilos de botones para eliminatorias (Idénticos a app.py) */
        .team-checkbox { display: none; }
        .team-label { cursor: pointer; border: 2px solid #dee2e6; border-radius: 8px; padding: 10px; transition: all 0.2s; display: block; text-align: center; background: white; font-weight: 600;}
        .team-checkbox:checked + .team-label { border-color: #2563eb; background-color: #eff6ff; color: #1e3a8a; box-shadow: 0 4px 8px rgba(37,99,235,0.2); transform: scale(1.02); }
    </style>
</head>
<body>
    <div class="container-fluid px-4 mt-4 mb-5">
        
        <div class="header-banner text-center mb-4 mx-auto position-relative" style="max-width: 1200px;">
            <h1>⚙️ PANEL DE ADMINISTRADOR</h1>
            <p class="m-0 mt-1 opacity-75">Actualiza los resultados reales con botones interactivos</p>
            <a href="/logout" class="btn btn-sm btn-outline-light position-absolute top-50 end-0 translate-middle-y me-3">Cerrar sesión</a>
        </div>

        {% if mensaje %}
        <div class="alert alert-success text-center mx-auto fw-bold" style="max-width: 1200px;">
            {{ mensaje }}
        </div>
        {% endif %}

        <form method="POST" class="mx-auto" style="max-width: 1400px;">
            
            <div class="card p-3 mb-4 border-start border-primary border-4 shadow-sm">
                <h5 class="fw-bold text-primary mb-1">1. Fase de Grupos</h5>
                <p class="small text-muted m-0">Indica si el equipo ha quedado 1º, 2º o 3º. (Los equipos seleccionados pasarán automáticamente a la zona de Octavos de Final).</p>
            </div>

            <div class="row">
                {% for letra, equipos in grupos.items() %}
                <div class="col-md-6 col-lg-3 mb-4">
                    <div class="card h-100 shadow-sm bg-light">
                        <div class="card-header bg-dark text-white fw-bold text-center">Grupo {{ letra }}</div>
                        <div class="card-body p-2">
                            {% for iso, pais in equipos %}
                            <div class="team-row">
                                <div class="d-flex align-items-center gap-2">
                                    <img src="https://flagcdn.com/w20/{{ iso }}.png" width="20" alt="{{ pais }}">
                                    <span class="fw-semibold text-dark small">{{ pais }}</span>
                                </div>
                                <select name="pos_{{ pais }}" data-pais="{{ pais }}" class="form-select form-select-sm pos-select border-secondary">
                                    <option value="" {% if posiciones_actuales.get(pais) == '' %}selected{% endif %}>-</option>
                                    <option value="1" {% if posiciones_actuales.get(pais) == '1' %}selected{% endif %}>1º</option>
                                    <option value="2" {% if posiciones_actuales.get(pais) == '2' %}selected{% endif %}>2º</option>
                                    <option value="3" {% if posiciones_actuales.get(pais) == '3' %}selected{% endif %}>3º</option>
                                </select>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>

            <div class="card p-4 mt-2 shadow-sm mb-5 border-start border-primary border-4">
                <h5 class="fw-bold text-primary mb-4 border-bottom pb-2">2. Rondas Eliminatorias</h5>
                
                <div id="sec-octavos" class="mb-4">
                    <h6 class="bg-dark text-white p-2 rounded text-center fw-bold">Octavos de Final</h6>
                    <div class="row g-2" id="grid-octavos"></div>
                </div>

                <div id="sec-cuartos" class="mb-4 border-top pt-3">
                    <h6 class="bg-dark text-white p-2 rounded text-center fw-bold">Cuartos de Final</h6>
                    <div class="row g-2" id="grid-cuartos"></div>
                </div>

                <div id="sec-semis" class="mb-4 border-top pt-3">
                    <h6 class="bg-dark text-white p-2 rounded text-center fw-bold">Semifinales</h6>
                    <div class="row g-2" id="grid-semis"></div>
                </div>

                <div id="sec-final" class="mb-4 border-top pt-3">
                    <h6 class="bg-dark text-white p-2 rounded text-center fw-bold">La Final</h6>
                    <div class="row g-2 justify-content-center" id="grid-final"></div>
                </div>

                <div id="sec-campeon" class="mb-4 border-top pt-3">
                    <h6 class="bg-warning text-dark p-2 rounded text-center fw-bold">🏆 Campeón Mundial</h6>
                    <div class="row g-2 justify-content-center" id="grid-campeon"></div>
                    <input type="hidden" name="subcampeon" id="input-subcampeon">
                </div>
                
                <div class="mt-4 border-top pt-4 row justify-content-center">
                    <div class="col-md-6 text-center">
                        <label class="fw-bold fs-5 text-primary mb-2">⚽ Pichichi (Goleador)</label>
                        <p class="small text-muted mb-2">Si quieres aceptar varios nombres, sepáralos por comas (Ej: Mbappé, Kylian Mbappe)</p>
                        <input type="text" class="form-control form-control-lg text-center border-primary shadow-sm" name="pichichi" value="{{ extras.get('pichichi', '') }}">
                    </div>
                </div>

            </div>

            <div class="text-center sticky-bottom p-3 bg-white border-top shadow-lg rounded-top-4 mx-auto" style="max-width: 1400px; z-index: 1000;">
                <button type="submit" class="btn btn-primary-custom text-white px-5 py-3 fw-bold fs-4 w-50">💾 Guardar Resultados en el Servidor</button>
            </div>
        </form>

        <script>
            // Datos inyectados desde Python (lo que ya está guardado en el .txt)
            const savedData = {{ extras | tojson }};
            let isInitialLoad = true;

            function renderGrids() {
                // 1. Obtener equipos clasificados de los desplegables de grupos
                let clasificados = [];
                document.querySelectorAll('.pos-select').forEach(sel => {
                    if(sel.value !== "") {
                        clasificados.push(sel.dataset.pais);
                    }
                });

                // 2. Cascadas de Eliminatorias (Permite guardar selecciones parciales)
                updateGrid('octavos', clasificados, isInitialLoad ? savedData.octavos || [] : getChecked('octavos'), 'checkbox');
                
                let selOctavos = getChecked('octavos');
                updateGrid('cuartos', selOctavos, isInitialLoad ? savedData.cuartos || [] : getChecked('cuartos'), 'checkbox');

                let selCuartos = getChecked('cuartos');
                updateGrid('semis', selCuartos, isInitialLoad ? savedData.semis || [] : getChecked('semis'), 'checkbox');

                let selSemis = getChecked('semis');
                updateGrid('final', selSemis, isInitialLoad ? savedData.final || [] : getChecked('final'), 'checkbox');

                let selFinal = getChecked('final');
                let savedCamp = savedData.campeon ? [savedData.campeon] : [];
                updateGrid('campeon', selFinal, isInitialLoad ? savedCamp : getChecked('campeon'), 'radio');

                // 3. Subcampeón automático
                let selCampeon = getChecked('campeon')[0];
                if(selCampeon) {
                    let sub = selFinal.find(e => e !== selCampeon);
                    document.getElementById('input-subcampeon').value = sub || '';
                } else {
                    document.getElementById('input-subcampeon').value = savedData.subcampeon || '';
                }
                
                isInitialLoad = false;
            }

            function updateGrid(nameAttr, availableTeams, activeTeams, inputType) {
                const container = document.getElementById('grid-' + nameAttr);
                container.innerHTML = '';
                
                availableTeams.forEach((equipo, index) => {
                    let isChecked = activeTeams.includes(equipo) ? 'checked' : '';
                    const html = `
                        <div class="col-6 col-md-3 col-lg-2">
                            <input type="${inputType}" name="${nameAttr}" value="${equipo}" id="${nameAttr}_${index}" class="team-checkbox chk-${nameAttr}" ${isChecked}>
                            <label class="team-label text-truncate" for="${nameAttr}_${index}">${equipo}</label>
                        </div>
                    `;
                    container.innerHTML += html;
                });

                // Añadir eventos a los nuevos botones para que la cascada siga funcionando en tiempo real
                document.querySelectorAll(`.chk-${nameAttr}`).forEach(chk => {
                    chk.addEventListener('change', renderGrids);
                });
            }

            function getChecked(nameAttr) {
                let checked = [];
                document.querySelectorAll(`.chk-${nameAttr}:checked`).forEach(chk => {
                    checked.push(chk.value);
                });
                return checked;
            }

            // Detectar cambios en los desplegables de grupos
            document.querySelectorAll('.pos-select').forEach(sel => {
                sel.addEventListener('change', renderGrids);
            });

            // Arrancar la cascada al cargar la página
            document.addEventListener("DOMContentLoaded", renderGrids);
        </script>

    </div>
</body>
</html>
"""

# ==========================================
# LÓGICA DE LECTURA Y ESCRITURA
# ==========================================
def leer_archivo_txt():
    """Lee el TXT para rellenar los datos actuales en el panel."""
    posiciones = {}
    extras = {'octavos': [], 'cuartos': [], 'semis': [], 'final': [], 'campeon': '', 'subcampeon': '', 'pichichi': ''}
    
    if os.path.exists(RUTA_RESULTADOS):
        with open(RUTA_RESULTADOS, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith('#') and ':' in linea:
                    clave, valor = linea.split(':', 1)
                    clave = clave.strip()
                    valor = valor.strip()
                    
                    if clave.startswith('g_'):
                        partes = clave.split('_')
                        if len(partes) == 3:
                            posicion = partes[2]
                            posiciones[valor] = posicion
                    elif clave in ['octavos', 'cuartos', 'semis', 'final']:
                        # Convertimos el string separado por comas en una lista de Python
                        extras[clave] = [e.strip() for e in valor.split(',') if e.strip()]
                    else:
                        extras[clave] = valor
    return posiciones, extras

def escribir_archivo_txt(datos_form):
    """Convierte los datos del formulario de vuelta al formato del TXT y lo guarda."""
    with open(RUTA_RESULTADOS, 'w', encoding='utf-8') as f:
        f.write("# ========================================================\n")
        f.write("# ARCHIVO GENERADO AUTOMÁTICAMENTE POR EL PANEL DE ADMIN\n")
        f.write("# ========================================================\n\n")
        f.write("# --- FASE DE GRUPOS ---\n")
        
        for letra, equipos in GRUPOS.items():
            equipo_1 = ""
            equipo_2 = ""
            equipo_3 = ""
            
            for iso, pais in equipos:
                pos = datos_form.get(f'pos_{pais}', '')
                if pos == '1': equipo_1 = pais
                elif pos == '2': equipo_2 = pais
                elif pos == '3': equipo_3 = pais
                
            if equipo_1 or equipo_2 or equipo_3:
                if equipo_1: f.write(f"g_{letra}_1: {equipo_1}\n")
                if equipo_2: f.write(f"g_{letra}_2: {equipo_2}\n")
                if equipo_3: f.write(f"g_{letra}_3: {equipo_3}\n")
                f.write("\n")

        f.write("\n# --- ELIMINATORIAS ---\n")
        for clave in ['octavos', 'cuartos', 'semis', 'final']:
            # getlist obtiene todos los checkbox marcados de esa ronda
            lista_equipos = datos_form.getlist(clave)
            f.write(f"{clave}: {', '.join(lista_equipos)}\n")
            
        f.write(f"campeon: {datos_form.get('campeon', '').strip()}\n")
        f.write(f"subcampeon: {datos_form.get('subcampeon', '').strip()}\n")
        
        f.write("\n# --- EXTRAS ---\n")
        f.write(f"pichichi: {datos_form.get('pichichi', '').strip()}\n")

# ==========================================
# RUTAS DE LA APLICACIÓN
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('autenticado'):
        return redirect(url_for('admin_panel'))
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['autenticado'] = True
            return redirect(url_for('admin_panel'))
        error = 'Contraseña incorrecta. Inténtalo de nuevo.'
    return render_template_string(HTML_LOGIN, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def admin_panel():
    if not session.get('autenticado'):
        return redirect(url_for('login'))

    mensaje = ""
    if request.method == 'POST':
        escribir_archivo_txt(request.form)
        mensaje = "¡Resultados guardados y actualizados correctamente! La web principal ya tiene los nuevos puntos."

    posiciones_actuales, extras_actuales = leer_archivo_txt()
    return render_template_string(HTML_ADMIN,
                                  grupos=GRUPOS,
                                  posiciones_actuales=posiciones_actuales,
                                  extras=extras_actuales,
                                  mensaje=mensaje)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)