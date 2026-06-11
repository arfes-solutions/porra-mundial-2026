from flask import Flask, render_template_string, request, redirect, url_for
import json
import os

app = Flask(__name__)

# --- CONFIGURACIÓN PRINCIPAL ---
TORNEO_INICIADO = False 
RUTA_PARTICIPANTES = 'participantes.json'
RUTA_RESULTADOS = 'resultados.txt'

# --- DATOS DEL TORNEO (Grupos Reales Oficiales Mundial 2026) ---
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
# CÓDIGO HTML / DISEÑO (TODO EN UNO)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Porra Mundial 2026</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏆</text></svg>">
    
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <style>
        body { font-family: 'Poppins', sans-serif; background-color: #f2f9f5; color: #2c3e50; padding-top: 110px; }
        
        .header-banner { 
            position: fixed; 
            top: 0; 
            left: 0; 
            right: 0; 
            z-index: 1050; 
            background: linear-gradient(135deg, #0f5132 0%, #198754 100%); 
            color: white; 
            padding: 1rem 1.5rem; 
            border-radius: 0 0 40px 40px; 
            box-shadow: 0 4px 15px rgba(25, 135, 84, 0.3); 
        }
        
        .header-banner h1 { font-size: clamp(1.2rem, 3vw, 1.6rem); font-weight: 700; letter-spacing: 1px; text-shadow: 1px 1px 3px rgba(0,0,0,0.2); margin: 0; }
        .header-banner p { font-size: clamp(0.7rem, 1.5vw, 0.9rem); font-weight: 400; margin: 0; opacity: 0.9; }
        
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: none; background-color: rgba(255, 255, 255, 0.98); }
        .table-custom-header { background-color: #0f5132 !important; color: white !important; }
        .puntos-oro { color: #d4af37; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
        .btn-success-custom { background-color: #198754; border: none; border-radius: 8px; transition: all 0.3s ease; }
        .btn-success-custom:hover:not(:disabled) { background-color: #146c43; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(25, 135, 84, 0.3); }
        .btn-success-custom:disabled { opacity: 0.5; cursor: not-allowed; background-color: #6c757d; }
        .btn-outline-custom { color: #0f5132; border-color: #0f5132; border-radius: 8px; }
        .btn-outline-custom:hover { background-color: #0f5132; color: white; }
        
        select option { font-weight: bold; color: #2c3e50; }
        select option:disabled { font-weight: normal; color: #adb5bd; font-style: italic; }
        
        .team-checkbox { display: none; }
        .team-label { cursor: pointer; border: 2px solid #dee2e6; border-radius: 8px; padding: 10px; transition: all 0.2s; display: block; text-align: center; background: white; font-weight: 600;}
        .team-checkbox:checked + .team-label { border-color: #198754; background-color: #e8f5e9; color: #0f5132; box-shadow: 0 4px 8px rgba(25,135,84,0.2); transform: scale(1.02); }
        .team-checkbox:disabled + .team-label { opacity: 0.5; cursor: not-allowed; }
        .fase-section { display: none; }
        .fase-active { display: block; animation: fadeIn 0.5s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body>
    
    <div class="header-banner">
        <div class="d-flex flex-wrap justify-content-between align-items-center mx-auto gap-2" style="max-width: 1400px;">
            <div class="d-flex gap-2">
                <a href="{{ url_for('index') }}" class="btn btn-light text-success fw-bold px-3">Inicio</a>
                <button type="button" class="btn btn-light text-success fw-bold px-3" data-bs-toggle="modal" data-bs-target="#modalReglas">
                    Reglas
                </button>
            </div>
            
            <div class="text-center flex-grow-1 d-none d-md-block">
                <h1>PORRA MUNDIAL 2026</h1>
                
            </div>
            
            <div class="d-flex gap-2">
                <a href="{{ url_for('ver_grupos') }}" class="btn btn-light text-success fw-bold px-3">Grupos</a>
                <a href="{{ url_for('ver_horarios') }}" class="btn btn-light text-success fw-bold px-3">Horarios</a>
            </div>
        </div>
    </div>

    <div class="container-fluid px-4 mb-5">

        {% if vista == 'inicio' %}
        <div class="card p-2 p-md-4 mx-auto" style="max-width: 1200px;">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
                    <h3 class="card-title m-0 fw-bold text-success">Clasificación General</h3>
                    {% if not torneo_iniciado %}
                    <a href="{{ url_for('nuevo_participante') }}" class="btn btn-success-custom text-white fw-bold px-4 py-2">
                        ➕ Nuevo participante
                    </a>
                    {% endif %}
                </div>
                
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-custom-header">
                            <tr>
                                <th scope="col" class="py-3 rounded-start-2">Pos</th>
                                <th scope="col" class="py-3">Nombre</th>
                                <th scope="col" class="text-center py-3">Puntos</th>
                                <th scope="col" class="text-end py-3 rounded-end-2">Acción</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for jug in clasificacion %}
                            <tr>
                                <td class="fw-bold fs-5">{{ loop.index }}º</td>
                                <td class="fw-bold fs-5">{{ jug.nombre }}</td>
                                <td class="text-center fw-bold fs-4 puntos-oro">{{ jug.puntos }} pts</td>
                                <td class="text-end">
                                    <a href="{{ url_for('ver_prediccion', nombre=jug.nombre) }}" class="btn btn-sm btn-outline-custom px-3">Ver predicción</a>
                                </td>
                            </tr>
                            {% else %}
                            <tr><td colspan="4" class="text-center py-5 text-muted fs-5">El campo está vacío. ¡Sé el primero en participar! ⚽</td></tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        {% elif vista == 'ver_grupos' %}
        <div class="card p-3 p-md-4 mx-auto mb-4 bg-transparent border-0 shadow-none" style="max-width: 1400px;">
            <div class="d-flex justify-content-between align-items-center border-bottom border-success pb-3 mb-4">
                <h3 class="m-0 fw-bold text-success">Clasificación de Grupos en Directo</h3>
                <a href="{{ url_for('index') }}" class="btn btn-outline-secondary fw-bold px-4">← Volver</a>
            </div>
            
            <div class="row">
                {% for letra, equipos_ordenados in grupos_ordenados.items() %}
                <div class="col-md-6 col-lg-3 mb-4">
                    <div class="card h-100 shadow-sm border-0 bg-light">
                        <div class="card-header bg-success text-white fw-bold text-center py-2">
                            Grupo {{ letra }}
                        </div>
                        <div class="card-body p-2">
                            <div class="d-flex flex-column gap-2">
                                {% for iso, pais, puesto in equipos_ordenados %}
                                    <div class="bg-white border rounded px-2 py-2 shadow-sm d-flex align-items-center justify-content-between">
                                        <div class="d-flex align-items-center gap-2">
                                            <img src="https://flagcdn.com/w20/{{ iso }}.png" width="20" alt="{{ pais }}">
                                            <span class="fw-semibold text-dark small">{{ pais }}</span>
                                        </div>
                                        {% if puesto == '1º' %}
                                            <span class="badge bg-success shadow-sm">{{ puesto }}</span>
                                        {% elif puesto == '2º' %}
                                            <span class="badge bg-primary shadow-sm">{{ puesto }}</span>
                                        {% elif puesto == '3º' %}
                                            <span class="badge bg-warning text-dark shadow-sm">{{ puesto }}</span>
                                        {% else %}
                                            <span class="badge bg-secondary opacity-25">-</span>
                                        {% endif %}
                                    </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        {% elif vista == 'ver_horarios' %}
        <div class="card p-3 p-md-4 mx-auto mb-4 bg-transparent border-0 shadow-none" style="max-width: 1400px;">
            <div class="d-flex justify-content-between align-items-center border-bottom border-success pb-3 mb-4">
                <h3 class="m-0 fw-bold text-success">📅 Horarios del Mundial (Hora Peninsular)</h3>
                <a href="{{ url_for('index') }}" class="btn btn-outline-secondary fw-bold px-4">← Volver</a>
            </div>
            
            <div class="row">
                {% for letra, partidos in calendario.items() %}
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card h-100 shadow-sm border-0 bg-light">
                        <div class="card-header bg-success text-white fw-bold text-center py-2">
                            Grupo {{ letra }}
                        </div>
                        <div class="card-body p-3">
                            <div class="d-flex flex-column gap-3">
                                {% for p in partidos %}
                                <div class="bg-white border rounded p-2 shadow-sm">
                                    <div class="text-center text-muted small mb-2 fw-bold border-bottom pb-1">
                                        <span class="text-success">{{ p.jornada }}</span> • {{ p.fecha }} - {{ p.hora }}
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div class="text-end" style="width: 40%; font-size: 0.9rem;">
                                            <span class="fw-bold">{{ p.eq1[1] }}</span>
                                            <img src="https://flagcdn.com/w20/{{ p.eq1[0] }}.png" width="20" alt="{{ p.eq1[1] }}" class="ms-1">
                                        </div>
                                        <div class="text-center fw-bold text-secondary" style="width: 20%;">vs</div>
                                        <div class="text-start" style="width: 40%; font-size: 0.9rem;">
                                            <img src="https://flagcdn.com/w20/{{ p.eq2[0] }}.png" width="20" alt="{{ p.eq2[1] }}" class="me-1">
                                            <span class="fw-bold">{{ p.eq2[1] }}</span>
                                        </div>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        {% elif vista == 'ver_prediccion' %}
        <div class="card p-3 p-md-4 mx-auto" style="max-width: 1200px;">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center border-bottom pb-3 mb-4">
                    <h3 class="m-0 fw-bold text-success">Predicción de {{ nombre }}</h3>
                    <a href="{{ url_for('index') }}" class="btn btn-outline-secondary fw-bold px-4">← Volver</a>
                </div>

                <h5 class="fw-bold text-secondary mb-3">Fase de Grupos</h5>
                <div class="row g-3 mb-5">
                    {% set letras = ['A','B','C','D','E','F','G','H','I','J','K','L'] %}
                    {% for letra in letras %}
                        {% set p1 = predicciones.grupos.get('g_' ~ letra ~ '_1', '') %}
                        {% set p2 = predicciones.grupos.get('g_' ~ letra ~ '_2', '') %}
                        {% set p3 = predicciones.grupos.get('g_' ~ letra ~ '_3', '') %}
                        
                        <div class="col-6 col-md-4 col-lg-3">
                            <div class="card shadow-sm h-100 border-0 bg-light">
                                <div class="card-header bg-success text-white text-center fw-bold py-2">Grupo {{ letra }}</div>
                                <div class="card-body p-2 text-center small">
                                    <div class="fw-bold text-dark mb-1"><span class="text-success me-1">1º</span> {{ p1 }}</div>
                                    <div class="fw-bold text-dark mb-1"><span class="text-primary me-1">2º</span> {{ p2 }}</div>
                                    {% if p3 %}
                                        <div class="fw-bold text-muted"><span class="text-warning me-1">3º</span> {{ p3 }}</div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>

                <h5 class="fw-bold text-secondary mb-3 border-top pt-4">Rondas Finales</h5>
                <div class="row g-4">
                    <div class="col-md-6">
                        <h6 class="bg-success text-white p-2 rounded text-center fw-bold">Octavos de Final</h6>
                        <div class="d-flex flex-wrap justify-content-center gap-1">
                            {% for eq in predicciones.eliminatorias.get('octavos', []) %}
                                <span class="badge bg-white text-dark border border-secondary p-2">{{ eq }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="bg-success text-white p-2 rounded text-center fw-bold">Cuartos de Final</h6>
                        <div class="d-flex flex-wrap justify-content-center gap-1">
                            {% for eq in predicciones.eliminatorias.get('cuartos', []) %}
                                <span class="badge bg-white text-dark border border-secondary p-2">{{ eq }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="bg-success text-white p-2 rounded text-center fw-bold">Semifinales</h6>
                        <div class="d-flex flex-wrap justify-content-center gap-2">
                            {% for eq in predicciones.eliminatorias.get('semis', []) %}
                                <span class="badge bg-white text-dark border border-secondary p-2 fs-6">{{ eq }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <h6 class="bg-success text-white p-2 rounded text-center fw-bold">La Final</h6>
                        <div class="d-flex flex-wrap justify-content-center gap-3">
                            {% for eq in predicciones.eliminatorias.get('final', []) %}
                                <span class="badge bg-white text-dark border border-success p-2 fs-5">{{ eq }}</span>
                            {% endfor %}
                        </div>
                    </div>
                </div>
                
                <div class="row mt-5 justify-content-center text-center bg-light p-4 rounded-4 shadow-sm mx-1">
                    <div class="col-md-4 mb-3 mb-md-0 border-end border-2">
                        <h6 class="text-muted fw-bold mb-2">SUBCAMPEÓN</h6>
                        <h4 class="fw-bold text-secondary m-0">{{ predicciones.eliminatorias.get('subcampeon', '-') }}</h4>
                    </div>
                    <div class="col-md-4 mb-3 mb-md-0 border-end border-2">
                        <h6 class="text-warning fw-bold mb-2">🏆 CAMPEÓN MUNDIAL</h6>
                        <h3 class="fw-bold text-success m-0">{{ predicciones.eliminatorias.get('campeon', '-') }}</h3>
                    </div>
                    <div class="col-md-4">
                        <h6 class="text-primary fw-bold mb-2">⚽ PICHICHI</h6>
                        <h4 class="fw-bold text-dark m-0">{{ predicciones.eliminatorias.get('pichichi', '-') }}</h4>
                    </div>
                </div>

            </div>
        </div>

        {% elif vista == 'nuevo_nombre' %}
        <div class="row justify-content-center">
            <div class="col-md-8 col-lg-6">
                <div class="card p-2 p-md-4 mt-4">
                    <div class="card-body">
                        <h3 class="mb-4 fw-bold text-success border-bottom pb-3 text-center">Inscripción</h3>
                        <form method="POST">
                            <div class="mb-4 p-3 mt-3">
                                <label for="nombre" class="form-label fw-bold fs-5 text-success text-center w-100">Introduce tu nombre:</label>
                                <input type="text" autocomplete="off" class="form-control form-control-lg text-center shadow-sm border-success" id="nombre" name="nombre" required placeholder="Ej: Benito Martínez">
                            </div>
                            <div class="d-flex justify-content-between mt-5 pt-3 border-top">
                                <a href="{{ url_for('index') }}" class="btn btn-light border px-4 py-2 fw-bold text-secondary">Cancelar</a>
                                <button type="submit" class="btn btn-success-custom text-white px-5 py-2 fw-bold fs-5">Siguiente →</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        {% elif vista == 'fase_grupos' %}
        <div class="card p-3 mb-4 shadow-sm border-start border-success border-4 mx-auto" style="max-width: 1200px; background-color: #fff;">
            <h5 class="fw-bold text-success mb-2">📋 Reglas de Clasificación de la Fase de Grupos</h5>

            <p class="text-muted small mb-2">
                En el Mundial 2026, se clasifican para dieciseisavos de final los dos primeros equipos de cada grupo y además los 8 mejores terceros clasificados en general.
                <br>
                Por tanto:
            </p>

            <ul class="text-muted small" style="line-height: 1.6;">
                <li>Debes seleccionar obligatoriamente el <strong>1º y 2º puesto</strong> de cada uno de los 12 grupos.</li>
                <li>Debes elegir exactamente a <strong>8 equipos como mejores terceros</strong> en total.</li>
            </ul>

            <p class="text-muted small mb-0">
                El botón para avanzar al final de la página se habilitará automáticamente cuando completes todos los requisitos.
            </p>
        </div>

        <form method="POST" class="mx-auto" style="max-width: 1400px;">
            <div class="row">
                {% for letra, equipos in grupos.items() %}
                <div class="col-md-6 col-lg-3 mb-4">
                    <div class="card h-100 shadow-sm">
                        <div class="card-header bg-success text-white fw-bold text-center fs-5">
                            Grupo {{ letra }}
                        </div>
                        <div class="card-body bg-light p-3">
                            <div class="d-flex flex-column gap-1 mb-3">
                                {% for iso, pais in equipos %}
                                    <div class="bg-white border rounded px-2 py-1 shadow-sm d-flex align-items-center gap-2">
                                        <img src="https://flagcdn.com/w20/{{ iso }}.png" width="20" alt="{{ pais }}"> 
                                        <span class="fw-semibold text-dark small">{{ pais }}</span>
                                    </div>
                                {% endfor %}
                            </div>
                            <hr class="my-2">
                            <div class="mb-2">
                                <label class="form-label text-muted small fw-bold mb-1">1º Puesto <span class="text-danger">*</span></label>
                                <select class="form-select form-select-sm fw-bold border-secondary text-secondary" name="g_{{ letra }}_1" required>
                                    <option value="" disabled selected hidden>Elegir 1º...</option>
                                    {% for iso, pais in equipos %}
                                        <option value="{{ pais }}">{{ pais }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-2">
                                <label class="form-label text-muted small fw-bold mb-1">2º Puesto <span class="text-danger">*</span></label>
                                <select class="form-select form-select-sm fw-bold border-secondary text-secondary" name="g_{{ letra }}_2" required>
                                    <option value="" disabled selected hidden>Elegir 2º...</option>
                                    {% for iso, pais in equipos %}
                                        <option value="{{ pais }}">{{ pais }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-2">
                                <label class="form-label text-muted small fw-bold mb-1">Mejor 3º (Opcional)</label>
                                <select class="form-select form-select-sm border-secondary text-secondary select-tercero" name="g_{{ letra }}_3">
                                    <option value="">Ninguno / Eliminado</option>
                                    {% for iso, pais in equipos %}
                                        <option value="{{ pais }}">{{ pais }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            
            <div class="card p-4 mt-2 shadow-sm text-center mx-auto mb-5" style="max-width: 1200px;">
                <div class="mb-3 d-flex justify-content-center gap-3 flex-wrap">
                    <span id="counter-grupos" class="badge bg-danger fs-6 p-2">Grupos: 0 / 12 completados</span>
                    <span id="terceros-counter" class="badge bg-danger fs-6 p-2">Mejores Terceros: 0 / 8 elegidos</span>
                </div>
                <button type="submit" id="btn-siguiente" class="btn btn-success-custom text-white px-5 py-3 fw-bold fs-5 mx-auto" disabled>Continuar</button>
            </div>
        </form>

        <script>
            function validarFormulario() {
                let gruposCompletos = 0;
                let tercerosContados = 0;
                const letras = ['A','B','C','D','E','F','G','H','I','J','K','L'];
                
                letras.forEach(letra => {
                    const s1 = document.querySelector('select[name="g_' + letra + '_1"]');
                    const s2 = document.querySelector('select[name="g_' + letra + '_2"]');
                    const s3 = document.querySelector('select[name="g_' + letra + '_3"]');
                    
                    const selects = [s1, s2, s3];
                    for (let i = 0; i < selects.length; i++) {
                        for (let j = 0; j < selects[i].options.length; j++) {
                            let opt = selects[i].options[j];
                            if (opt.value === "") continue;
                            let isDisabled = false;
                            for (let k = 0; k < selects.length; k++) {
                                if (i !== k && selects[k].value === opt.value) { isDisabled = true; break; }
                            }
                            opt.disabled = isDisabled;
                        }
                    }
                    
                    if (s1.value !== "" && s2.value !== "") gruposCompletos++;
                    if (s3 && s3.value !== "") tercerosContados++;
                });
                
                const btnSubmit = document.getElementById('btn-siguiente');
                const lblGrupos = document.getElementById('counter-grupos');
                const lblTerceros = document.getElementById('terceros-counter');
                
                lblGrupos.innerText = "Grupos: " + gruposCompletos + " / 12 completados";
                lblGrupos.className = (gruposCompletos === 12) ? "badge bg-success fs-6 p-2" : "badge bg-danger fs-6 p-2";
                
                lblTerceros.innerText = "Mejores Terceros: " + tercerosContados + " / 8 elegidos";
                lblTerceros.className = (tercerosContados === 8) ? "badge bg-success fs-6 p-2" : "badge bg-danger fs-6 p-2";
                
                btnSubmit.disabled = !(gruposCompletos === 12 && tercerosContados === 8);
            }

            document.addEventListener("DOMContentLoaded", function() {
                document.querySelectorAll("select").forEach(select => {
                    select.addEventListener("change", validarFormulario);
                });
                validarFormulario();
            });
        </script>

        {% elif vista == 'eliminatorias' %}
        <div class="card p-4 mx-auto shadow-sm" style="max-width: 1200px;">
            <h3 class="fw-bold text-success border-bottom pb-3 text-center">Fase Eliminatoria - {{ nombre }}</h3>
            <p class="text-center text-muted">Selecciona los equipos que avanzan en cada ronda.</p>

            <form method="POST" id="form-eliminatorias">
                <div id="sec-octavos" class="fase-section fase-active mb-5">
                    <h5 class="bg-success text-white p-2 rounded text-center">1. Selecciona 16 equipos para OCTAVOS DE FINAL</h5>
                    <div class="text-center mb-3"><span id="count-octavos" class="badge bg-warning text-dark fs-6">0 / 16 seleccionados</span></div>
                    <div class="row g-2">
                        {% for equipo in clasificados %}
                        <div class="col-4 col-md-3 col-lg-2">
                            <input type="checkbox" name="octavos" value="{{ equipo }}" id="oct_{{ loop.index }}" class="team-checkbox chk-octavos">
                            <label class="team-label text-truncate" for="oct_{{ loop.index }}">{{ equipo }}</label>
                        </div>
                        {% endfor %}
                    </div>
                </div>

                <div id="sec-cuartos" class="fase-section mb-5 border-top pt-4">
                    <h5 class="bg-success text-white p-2 rounded text-center">2. Selecciona 8 equipos para CUARTOS DE FINAL</h5>
                    <div class="text-center mb-3"><span id="count-cuartos" class="badge bg-warning text-dark fs-6">0 / 8 seleccionados</span></div>
                    <div class="row g-2" id="grid-cuartos"></div>
                </div>

                <div id="sec-semis" class="fase-section mb-5 border-top pt-4">
                    <h5 class="bg-success text-white p-2 rounded text-center">3. Selecciona 4 equipos para SEMIFINALES</h5>
                    <div class="text-center mb-3"><span id="count-semis" class="badge bg-warning text-dark fs-6">0 / 4 seleccionados</span></div>
                    <div class="row g-2" id="grid-semis"></div>
                </div>

                <div id="sec-final" class="fase-section mb-5 border-top pt-4">
                    <h5 class="bg-success text-white p-2 rounded text-center">4. Selecciona 2 equipos para LA FINAL</h5>
                    <div class="text-center mb-3"><span id="count-final" class="badge bg-warning text-dark fs-6">0 / 2 seleccionados</span></div>
                    <div class="row g-2 justify-content-center" id="grid-final"></div>
                </div>

                <div id="sec-campeon" class="fase-section mb-5 border-top pt-4">
                    <h5 class="bg-warning text-dark p-2 rounded text-center fw-bold">5. ¡Elige al Campeón Mundial!</h5>
                    <div class="row g-2 justify-content-center mb-4" id="grid-campeon"></div>
                    
                    <input type="hidden" name="subcampeon" id="input-subcampeon">
                    
                    <h5 class="bg-primary text-white p-2 rounded text-center mt-4">6. Pichichi del Torneo (Máximo Goleador)</h5>
                    <div class="row justify-content-center">
                        <div class="col-md-6">
                            <input type="text" name="pichichi" class="form-control form-control-lg text-center" placeholder="Ej: Kylian Mbappé" required>
                        </div>
                    </div>
                </div>

                <div class="text-center mt-4">
                    <button type="submit" id="btn-finalizar" class="btn btn-success-custom text-white px-5 py-3 fw-bold fs-4 w-100 d-none">🎉 Terminar Predicción 🎉</button>
                </div>
            </form>
        </div>

        <script>
            function setupFase(origenClase, destinoGrid, destinoPrefijo, maxSelect, counterId, nextSectionId, nameAttr) {
                const checkboxes = document.querySelectorAll('.' + origenClase);
                let selected = [];

                checkboxes.forEach(chk => {
                    chk.addEventListener('change', function() {
                        selected = Array.from(checkboxes).filter(c => c.checked).map(c => c.value);
                        
                        const counter = document.getElementById(counterId);
                        counter.innerText = selected.length + " / " + maxSelect + " seleccionados";
                        
                        if (selected.length >= maxSelect) {
                            counter.className = "badge bg-success fs-6";
                            checkboxes.forEach(c => { if(!c.checked) c.disabled = true; });
                            generarSiguienteFase(selected, destinoGrid, destinoPrefijo, nameAttr, nextSectionId);
                        } else {
                            counter.className = "badge bg-warning text-dark fs-6";
                            checkboxes.forEach(c => c.disabled = false);
                            document.getElementById(nextSectionId).classList.remove('fase-active');
                            limpiarFasesDesde(nextSectionId);
                        }
                    });
                });
            }

            function generarSiguienteFase(equipos, contenedorId, prefijoId, nameAttr, sectionId) {
                if(!contenedorId) return;
                const contenedor = document.getElementById(contenedorId);
                contenedor.innerHTML = '';
                
                equipos.forEach((equipo, index) => {
                    const type = (nameAttr === 'campeon') ? 'radio' : 'checkbox';
                    const html = `
                        <div class="col-6 col-md-3">
                            <input type="${type}" name="${nameAttr}" value="${equipo}" id="${prefijoId}_${index}" class="team-checkbox chk-${nameAttr}">
                            <label class="team-label text-truncate" for="${prefijoId}_${index}">${equipo}</label>
                        </div>
                    `;
                    contenedor.innerHTML += html;
                });
                
                document.getElementById(sectionId).classList.add('fase-active');
                
                if(nameAttr === 'cuartos') setupFase('chk-cuartos', 'grid-semis', 'sem', 8, 'count-cuartos', 'sec-semis', 'semis');
                if(nameAttr === 'semis') setupFase('chk-semis', 'grid-final', 'fin', 4, 'count-semis', 'sec-final', 'final');
                if(nameAttr === 'final') setupFase('chk-final', 'grid-campeon', 'camp', 2, 'count-final', 'sec-campeon', 'campeon');
                
                if(nameAttr === 'campeon') {
                    const radios = document.querySelectorAll('.chk-campeon');
                    radios.forEach(radio => {
                        radio.addEventListener('change', function() {
                            const finalistas = Array.from(document.querySelectorAll('.chk-final')).filter(c=>c.checked).map(c=>c.value);
                            const ganador = this.value;
                            const sub = finalistas.find(f => f !== ganador);
                            document.getElementById('input-subcampeon').value = sub;
                            document.getElementById('btn-finalizar').classList.remove('d-none');
                        });
                    });
                }
            }

            function limpiarFasesDesde(sectionId) {
                const fases = ['sec-cuartos', 'sec-semis', 'sec-final', 'sec-campeon'];
                let index = fases.indexOf(sectionId);
                if(index !== -1) {
                    for(let i = index; i < fases.length; i++) {
                        document.getElementById(fases[i]).classList.remove('fase-active');
                    }
                }
                document.getElementById('btn-finalizar').classList.add('d-none');
            }

            setupFase('chk-octavos', 'grid-cuartos', 'cua', 16, 'count-octavos', 'sec-cuartos', 'cuartos');
        </script>

        {% endif %}

    </div>

    <div class="modal fade" id="modalReglas" tabindex="-1" aria-labelledby="modalReglasLabel" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-lg">
            <div class="modal-content border-0 shadow">
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title fw-bold" id="modalReglasLabel">📋 Reglas y Puntuaciones</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body p-4 text-dark">
                    <h6 class="fw-bold text-success border-bottom pb-2 mb-3">🌍 Sistema de Clasificación (Mundial 2026)</h6>
                    <p class="small text-muted mb-4">
                        En esta edición compiten 48 selecciones repartidas en 12 grupos. Se clasifican para la ronda de <strong>Dieciseisavos de Final (32 equipos en total):</strong><br>
                        - Los <strong>2 primeros</strong> equipos de cada grupo.<br>
                        - Los <strong>8 mejores terceros</strong> en el cómputo global.
                    </p>

                    <h6 class="fw-bold text-primary border-bottom pb-2 mb-3">🔢 Sistema de Puntuación de la Porra</h6>
                    <ul class="list-group list-group-flush small">
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                            Fase de Grupos (acertar que un equipo se clasifica)
                            <span class="badge bg-secondary rounded-pill">+1 pt</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                            Fase de Grupos (acertar también su posición exacta: 1º, 2º o 3º)
                            <span class="badge bg-secondary rounded-pill">+1 pt extra</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                            Acertar cada equipo en Octavos de Final
                            <span class="badge bg-primary rounded-pill">+3 pts</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                            Acertar cada equipo en Cuartos de Final
                            <span class="badge bg-primary rounded-pill">+5 pts</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                            Acertar cada equipo en Semifinales
                            <span class="badge bg-primary rounded-pill">+8 pts</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">
                            Acertar cada equipo en La Final
                            <span class="badge bg-primary rounded-pill">+12 pts</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0 bg-light mt-2 fw-bold text-secondary">
                            Acertar el Subcampeón
                            <span class="badge bg-warning text-dark rounded-pill">+10 pts</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0 bg-light fw-bold text-success">
                            🏆 Acertar el Campeón Mundial
                            <span class="badge bg-success rounded-pill">+20 pts</span>
                        </li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0 bg-light fw-bold text-dark">
                            ⚽ Acertar el Pichichi (Máximo Goleador)
                            <span class="badge bg-dark rounded-pill">+7 pts</span>
                        </li>
                    </ul>
                </div>
                <div class="modal-footer border-0 pt-0">
                    <button type="button" class="btn btn-secondary fw-bold" data-bs-dismiss="modal">Entendido</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# ==========================================
# FUNCIONES DE LECTURA, ESCRITURA Y PUNTOS
# ==========================================
def cargar_participantes():
    if not os.path.exists(RUTA_PARTICIPANTES):
        return {}
    with open(RUTA_PARTICIPANTES, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return {}

def guardar_participantes(datos):
    with open(RUTA_PARTICIPANTES, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def leer_resultados_reales():
    resultados = {}
    if os.path.exists(RUTA_RESULTADOS):
        with open(RUTA_RESULTADOS, 'r', encoding='utf-8') as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith('#') and ':' in linea:
                    clave, valor = linea.split(':', 1)
                    clave = clave.strip().lower()
                    
                    if clave == 'pichichi':
                        opciones = valor.split(',')
                        resultados[clave] = [opcion.strip().lower() for opcion in opciones if opcion.strip()]
                    elif clave in ['octavos', 'cuartos', 'semis', 'final']:
                        equipos = valor.split(',')
                        resultados[clave] = [equipo.strip() for equipo in equipos if equipo.strip()]
                    else:
                        resultados[clave] = valor.strip()
    return resultados

def calcular_puntos(predicciones, resultados_reales):
    puntos = 0
    grupos_user = predicciones.get('grupos', {})
    elim_user = predicciones.get('eliminatorias', {})
    
    letras_grupos = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']
    for letra in letras_grupos:
        letra_min = letra.lower()
        
        real_1 = resultados_reales.get(f'g_{letra_min}_1')
        real_2 = resultados_reales.get(f'g_{letra_min}_2')
        real_3 = resultados_reales.get(f'g_{letra_min}_3')
        clasificados_reales = [e for e in [real_1, real_2, real_3] if e]
        
        for pos in ['1', '2', '3']:
            key_user = f'g_{letra}_{pos}'
            key_real = f'g_{letra_min}_{pos}'
            
            equipo_user = grupos_user.get(key_user)
            
            if equipo_user and equipo_user.strip():
                if equipo_user in clasificados_reales:
                    puntos += 1
                    if equipo_user == resultados_reales.get(key_real):
                        puntos += 1

    for eq in elim_user.get('octavos', []):
        if eq in resultados_reales.get('octavos', []): puntos += 3
        
    for eq in elim_user.get('cuartos', []):
        if eq in resultados_reales.get('cuartos', []): puntos += 5
        
    for eq in elim_user.get('semis', []):
        if eq in resultados_reales.get('semis', []): puntos += 8
        
    for eq in elim_user.get('final', []):
        if eq in resultados_reales.get('final', []): puntos += 12
        
    campeon_user = elim_user.get('campeon')
    if campeon_user and campeon_user == resultados_reales.get('campeon'):
        puntos += 20
        
    subcampeon_user = elim_user.get('subcampeon')
    if subcampeon_user and subcampeon_user == resultados_reales.get('subcampeon'):
        puntos += 10
        
    pichichi_user = elim_user.get('pichichi', '').strip().lower()
    if pichichi_user and pichichi_user in resultados_reales.get('pichichi', []):
        puntos += 7

    return puntos

def generar_calendario():
    return {
        'A': [
            {'jornada': 'Jornada 1', 'eq1': ('mx', 'México'), 'eq2': ('za', 'Sudáfrica'), 'fecha': '11 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 1', 'eq1': ('kr', 'Corea del Sur'), 'eq2': ('cz', 'Chequia'), 'fecha': '12 Jun', 'hora': '04:00'},
            {'jornada': 'Jornada 2', 'eq1': ('cz', 'Chequia'), 'eq2': ('za', 'Sudáfrica'), 'fecha': '18 Jun', 'hora': '18:00'},
            {'jornada': 'Jornada 2', 'eq1': ('mx', 'México'), 'eq2': ('kr', 'Corea del Sur'), 'fecha': '19 Jun', 'hora': '03:00'},
            {'jornada': 'Jornada 3', 'eq1': ('za', 'Sudáfrica'), 'eq2': ('kr', 'Corea del Sur'), 'fecha': '25 Jun', 'hora': '03:00'},
            {'jornada': 'Jornada 3', 'eq1': ('cz', 'Chequia'), 'eq2': ('mx', 'México'), 'fecha': '25 Jun', 'hora': '03:00'}
        ],
        'B': [
            {'jornada': 'Jornada 1', 'eq1': ('ca', 'Canadá'), 'eq2': ('ba', 'Bosnia y Herzegovina'), 'fecha': '12 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 1', 'eq1': ('qa', 'Qatar'), 'eq2': ('ch', 'Suiza'), 'fecha': '13 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 2', 'eq1': ('ch', 'Suiza'), 'eq2': ('ba', 'Bosnia y Herzegovina'), 'fecha': '18 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 2', 'eq1': ('ca', 'Canadá'), 'eq2': ('qa', 'Qatar'), 'fecha': '19 Jun', 'hora': '00:00'},
            {'jornada': 'Jornada 3', 'eq1': ('ba', 'Bosnia y Herzegovina'), 'eq2': ('qa', 'Qatar'), 'fecha': '24 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 3', 'eq1': ('ch', 'Suiza'), 'eq2': ('ca', 'Canadá'), 'fecha': '24 Jun', 'hora': '21:00'}
        ],
        'C': [
            {'jornada': 'Jornada 1', 'eq1': ('br', 'Brasil'), 'eq2': ('ma', 'Marruecos'), 'fecha': '14 Jun', 'hora': '00:00'},
            {'jornada': 'Jornada 1', 'eq1': ('ht', 'Haití'), 'eq2': ('gb-sct', 'Escocia'), 'fecha': '14 Jun', 'hora': '03:00'},
            {'jornada': 'Jornada 2', 'eq1': ('gb-sct', 'Escocia'), 'eq2': ('ma', 'Marruecos'), 'fecha': '20 Jun', 'hora': '00:00'},
            {'jornada': 'Jornada 2', 'eq1': ('br', 'Brasil'), 'eq2': ('ht', 'Haití'), 'fecha': '20 Jun', 'hora': '02:30'},
            {'jornada': 'Jornada 3', 'eq1': ('gb-sct', 'Escocia'), 'eq2': ('br', 'Brasil'), 'fecha': '25 Jun', 'hora': '00:00'},
            {'jornada': 'Jornada 3', 'eq1': ('ma', 'Marruecos'), 'eq2': ('ht', 'Haití'), 'fecha': '25 Jun', 'hora': '00:00'}
        ],
        'D': [
            {'jornada': 'Jornada 1', 'eq1': ('us', 'Estados Unidos'), 'eq2': ('py', 'Paraguay'), 'fecha': '13 Jun', 'hora': '03:00'},
            {'jornada': 'Jornada 1', 'eq1': ('au', 'Australia'), 'eq2': ('tr', 'Turquía'), 'fecha': '14 Jun', 'hora': '06:00'},
            {'jornada': 'Jornada 2', 'eq1': ('us', 'Estados Unidos'), 'eq2': ('au', 'Australia'), 'fecha': '19 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 2', 'eq1': ('tr', 'Turquía'), 'eq2': ('py', 'Paraguay'), 'fecha': '20 Jun', 'hora': '05:00'},
            {'jornada': 'Jornada 3', 'eq1': ('tr', 'Turquía'), 'eq2': ('us', 'Estados Unidos'), 'fecha': '26 Jun', 'hora': '04:00'},
            {'jornada': 'Jornada 3', 'eq1': ('py', 'Paraguay'), 'eq2': ('au', 'Australia'), 'fecha': '26 Jun', 'hora': '04:00'}
        ],
        'E': [
            {'jornada': 'Jornada 1', 'eq1': ('de', 'Alemania'), 'eq2': ('cw', 'Curazao'), 'fecha': '14 Jun', 'hora': '19:00'},
            {'jornada': 'Jornada 1', 'eq1': ('ci', 'Costa de Marfil'), 'eq2': ('ec', 'Ecuador'), 'fecha': '15 Jun', 'hora': '01:00'},
            {'jornada': 'Jornada 2', 'eq1': ('de', 'Alemania'), 'eq2': ('ci', 'Costa de Marfil'), 'fecha': '20 Jun', 'hora': '22:00'},
            {'jornada': 'Jornada 2', 'eq1': ('ec', 'Ecuador'), 'eq2': ('cw', 'Curazao'), 'fecha': '21 Jun', 'hora': '02:00'},
            {'jornada': 'Jornada 3', 'eq1': ('ec', 'Ecuador'), 'eq2': ('de', 'Alemania'), 'fecha': '25 Jun', 'hora': '22:00'},
            {'jornada': 'Jornada 3', 'eq1': ('cw', 'Curazao'), 'eq2': ('ci', 'Costa de Marfil'), 'fecha': '25 Jun', 'hora': '22:00'}
        ],
        'F': [
            {'jornada': 'Jornada 1', 'eq1': ('nl', 'Países Bajos'), 'eq2': ('jp', 'Japón'), 'fecha': '14 Jun', 'hora': '22:00'},
            {'jornada': 'Jornada 1', 'eq1': ('se', 'Suecia'), 'eq2': ('tn', 'Túnez'), 'fecha': '15 Jun', 'hora': '04:00'},
            {'jornada': 'Jornada 2', 'eq1': ('nl', 'Países Bajos'), 'eq2': ('se', 'Suecia'), 'fecha': '20 Jun', 'hora': '19:00'},
            {'jornada': 'Jornada 2', 'eq1': ('tn', 'Túnez'), 'eq2': ('jp', 'Japón'), 'fecha': '21 Jun', 'hora': '06:00'},
            {'jornada': 'Jornada 3', 'eq1': ('jp', 'Japón'), 'eq2': ('se', 'Suecia'), 'fecha': '26 Jun', 'hora': '01:00'},
            {'jornada': 'Jornada 3', 'eq1': ('tn', 'Túnez'), 'eq2': ('nl', 'Países Bajos'), 'fecha': '26 Jun', 'hora': '01:00'}
        ],
        'G': [
            {'jornada': 'Jornada 1', 'eq1': ('be', 'Bélgica'), 'eq2': ('eg', 'Egipto'), 'fecha': '15 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 1', 'eq1': ('ir', 'Irán'), 'eq2': ('nz', 'Nueva Zelanda'), 'fecha': '16 Jun', 'hora': '03:00'},
            {'jornada': 'Jornada 2', 'eq1': ('be', 'Bélgica'), 'eq2': ('ir', 'Irán'), 'fecha': '21 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 2', 'eq1': ('nz', 'Nueva Zelanda'), 'eq2': ('eg', 'Egipto'), 'fecha': '22 Jun', 'hora': '03:00'},
            {'jornada': 'Jornada 3', 'eq1': ('nz', 'Nueva Zelanda'), 'eq2': ('be', 'Bélgica'), 'fecha': '27 Jun', 'hora': '05:00'},
            {'jornada': 'Jornada 3', 'eq1': ('eg', 'Egipto'), 'eq2': ('ir', 'Irán'), 'fecha': '27 Jun', 'hora': '05:00'}
        ],
        'H': [
            {'jornada': 'Jornada 1', 'eq1': ('es', 'España'), 'eq2': ('cv', 'Cabo Verde'), 'fecha': '15 Jun', 'hora': '18:00'},
            {'jornada': 'Jornada 1', 'eq1': ('sa', 'Arabia Saudita'), 'eq2': ('uy', 'Uruguay'), 'fecha': '16 Jun', 'hora': '00:00'},
            {'jornada': 'Jornada 2', 'eq1': ('es', 'España'), 'eq2': ('sa', 'Arabia Saudita'), 'fecha': '21 Jun', 'hora': '18:00'},
            {'jornada': 'Jornada 2', 'eq1': ('uy', 'Uruguay'), 'eq2': ('cv', 'Cabo Verde'), 'fecha': '22 Jun', 'hora': '00:00'},
            {'jornada': 'Jornada 3', 'eq1': ('uy', 'Uruguay'), 'eq2': ('es', 'España'), 'fecha': '27 Jun', 'hora': '02:00'},
            {'jornada': 'Jornada 3', 'eq1': ('cv', 'Cabo Verde'), 'eq2': ('sa', 'Arabia Saudita'), 'fecha': '27 Jun', 'hora': '02:00'}
        ],
        'I': [
            {'jornada': 'Jornada 1', 'eq1': ('fr', 'Francia'), 'eq2': ('sn', 'Senegal'), 'fecha': '16 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 1', 'eq1': ('iq', 'Irak'), 'eq2': ('no', 'Noruega'), 'fecha': '17 Jun', 'hora': '00:00'},
            {'jornada': 'Jornada 2', 'eq1': ('fr', 'Francia'), 'eq2': ('iq', 'Irak'), 'fecha': '22 Jun', 'hora': '23:00'},
            {'jornada': 'Jornada 2', 'eq1': ('no', 'Noruega'), 'eq2': ('sn', 'Senegal'), 'fecha': '23 Jun', 'hora': '02:00'},
            {'jornada': 'Jornada 3', 'eq1': ('sn', 'Senegal'), 'eq2': ('iq', 'Irak'), 'fecha': '26 Jun', 'hora': '21:00'},
            {'jornada': 'Jornada 3', 'eq1': ('no', 'Noruega'), 'eq2': ('fr', 'Francia'), 'fecha': '26 Jun', 'hora': '21:00'}
        ],
        'J': [
            {'jornada': 'Jornada 1', 'eq1': ('ar', 'Argentina'), 'eq2': ('dz', 'Argelia'), 'fecha': '17 Jun', 'hora': '03:00'},
            {'jornada': 'Jornada 1', 'eq1': ('at', 'Austria'), 'eq2': ('jo', 'Jordania'), 'fecha': '17 Jun', 'hora': '06:00'},
            {'jornada': 'Jornada 2', 'eq1': ('ar', 'Argentina'), 'eq2': ('at', 'Austria'), 'fecha': '22 Jun', 'hora': '19:00'},
            {'jornada': 'Jornada 2', 'eq1': ('jo', 'Jordania'), 'eq2': ('dz', 'Argelia'), 'fecha': '23 Jun', 'hora': '05:00'},
            {'jornada': 'Jornada 3', 'eq1': ('jo', 'Jordania'), 'eq2': ('ar', 'Argentina'), 'fecha': '28 Jun', 'hora': '04:00'},
            {'jornada': 'Jornada 3', 'eq1': ('dz', 'Argelia'), 'eq2': ('at', 'Austria'), 'fecha': '28 Jun', 'hora': '04:00'}
        ],
        'K': [
            {'jornada': 'Jornada 1', 'eq1': ('pt', 'Portugal'), 'eq2': ('cd', 'RD Congo'), 'fecha': '17 Jun', 'hora': '19:00'},
            {'jornada': 'Jornada 1', 'eq1': ('uz', 'Uzbekistán'), 'eq2': ('co', 'Colombia'), 'fecha': '18 Jun', 'hora': '04:00'},
            {'jornada': 'Jornada 2', 'eq1': ('pt', 'Portugal'), 'eq2': ('uz', 'Uzbekistán'), 'fecha': '23 Jun', 'hora': '19:00'},
            {'jornada': 'Jornada 2', 'eq1': ('co', 'Colombia'), 'eq2': ('cd', 'RD Congo'), 'fecha': '24 Jun', 'hora': '04:00'},
            {'jornada': 'Jornada 3', 'eq1': ('co', 'Colombia'), 'eq2': ('pt', 'Portugal'), 'fecha': '28 Jun', 'hora': '01:30'},
            {'jornada': 'Jornada 3', 'eq1': ('cd', 'RD Congo'), 'eq2': ('uz', 'Uzbekistán'), 'fecha': '28 Jun', 'hora': '01:30'}
        ],
        'L': [
            {'jornada': 'Jornada 1', 'eq1': ('gb-eng', 'Inglaterra'), 'eq2': ('hr', 'Croacia'), 'fecha': '17 Jun', 'hora': '22:00'},
            {'jornada': 'Jornada 1', 'eq1': ('gh', 'Ghana'), 'eq2': ('pa', 'Panamá'), 'fecha': '18 Jun', 'hora': '01:00'},
            {'jornada': 'Jornada 2', 'eq1': ('gb-eng', 'Inglaterra'), 'eq2': ('gh', 'Ghana'), 'fecha': '23 Jun', 'hora': '22:00'},
            {'jornada': 'Jornada 2', 'eq1': ('pa', 'Panamá'), 'eq2': ('hr', 'Croacia'), 'fecha': '24 Jun', 'hora': '01:00'},
            {'jornada': 'Jornada 3', 'eq1': ('hr', 'Croacia'), 'eq2': ('gh', 'Ghana'), 'fecha': '27 Jun', 'hora': '23:00'},
            {'jornada': 'Jornada 3', 'eq1': ('pa', 'Panamá'), 'eq2': ('gb-eng', 'Inglaterra'), 'fecha': '27 Jun', 'hora': '23:00'}
        ]
    }

# ==========================================
# RUTAS DE LA APLICACIÓN
# ==========================================
@app.route('/')
def index():
    participantes = cargar_participantes()
    resultados_reales = leer_resultados_reales()
    
    clasificacion = []
    for nom, pred in participantes.items():
        pts = calcular_puntos(pred, resultados_reales)
        clasificacion.append({'nombre': nom, 'puntos': pts})
        
    clasificacion = sorted(clasificacion, key=lambda x: x['puntos'], reverse=True)
    
    return render_template_string(HTML_TEMPLATE, vista='inicio', clasificacion=clasificacion, torneo_iniciado=TORNEO_INICIADO)

@app.route('/grupos')
def ver_grupos():
    resultados = leer_resultados_reales()
    grupos_ordenados = {}
    
    for letra, equipos in GRUPOS.items():
        letra_min = letra.lower()
        r1 = resultados.get(f'g_{letra_min}_1', '')
        r2 = resultados.get(f'g_{letra_min}_2', '')
        r3 = resultados.get(f'g_{letra_min}_3', '')
        
        equipos_dict = {pais: iso for iso, pais in equipos}
        
        ordenados = []
        if r1 in equipos_dict: ordenados.append((equipos_dict[r1], r1, '1º'))
        if r2 in equipos_dict: ordenados.append((equipos_dict[r2], r2, '2º'))
        if r3 in equipos_dict: ordenados.append((equipos_dict[r3], r3, '3º'))
        
        puestos_ocupados = [e[1] for e in ordenados]
        for iso, pais in equipos:
            if pais not in puestos_ocupados:
                ordenados.append((iso, pais, '-'))
        
        grupos_ordenados[letra] = ordenados

    return render_template_string(HTML_TEMPLATE, vista='ver_grupos', grupos_ordenados=grupos_ordenados)

@app.route('/horarios')
def ver_horarios():
    calendario = generar_calendario()
    return render_template_string(HTML_TEMPLATE, vista='ver_horarios', calendario=calendario)

@app.route('/prediccion/<nombre>')
def ver_prediccion(nombre):
    participantes = cargar_participantes()
    if nombre not in participantes:
        return redirect(url_for('index'))
    
    predicciones = participantes[nombre]
    return render_template_string(HTML_TEMPLATE, vista='ver_prediccion', nombre=nombre, predicciones=predicciones)

@app.route('/nuevo', methods=['GET', 'POST'])
def nuevo_participante():
    if TORNEO_INICIADO: return "El torneo ha comenzado.", 403
    if request.method == 'POST':
        return redirect(url_for('fase_grupos', nombre=request.form.get('nombre')))
    return render_template_string(HTML_TEMPLATE, vista='nuevo_nombre')

@app.route('/fase_grupos/<nombre>', methods=['GET', 'POST'])
def fase_grupos(nombre):
    if request.method == 'POST':
        datos_grupos = request.form.to_dict()
        participantes = cargar_participantes()
        if nombre not in participantes: participantes[nombre] = {}
        participantes[nombre]['grupos'] = datos_grupos
        guardar_participantes(participantes)
        return redirect(url_for('eliminatorias', nombre=nombre))
        
    return render_template_string(HTML_TEMPLATE, vista='fase_grupos', nombre=nombre, grupos=GRUPOS)

@app.route('/eliminatorias/<nombre>', methods=['GET', 'POST'])
def eliminatorias(nombre):
    participantes = cargar_participantes()
    if nombre not in participantes or 'grupos' not in participantes[nombre]:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        datos_eliminatorias = {
            'octavos': request.form.getlist('octavos'),
            'cuartos': request.form.getlist('cuartos'),
            'semis': request.form.getlist('semis'),
            'final': request.form.getlist('final'),
            'campeon': request.form.get('campeon'),
            'subcampeon': request.form.get('subcampeon'),
            'pichichi': request.form.get('pichichi')
        }
        participantes[nombre]['eliminatorias'] = datos_eliminatorias
        guardar_participantes(participantes)
        return redirect(url_for('index'))
    
    datos_grupos = participantes[nombre]['grupos']
    clasificados = []
    for key, equipo in datos_grupos.items():
        if equipo and equipo.strip() != "" and not key.endswith('_3'):
            clasificados.append(equipo)
        elif key.endswith('_3') and equipo and equipo.strip() != "":
            clasificados.append(equipo)
            
    return render_template_string(HTML_TEMPLATE, vista='eliminatorias', nombre=nombre, clasificados=clasificados)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)