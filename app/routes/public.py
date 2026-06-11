import os
from flask import Blueprint, redirect, render_template_string, request, session, url_for, send_file, Response
from werkzeug.security import check_password_hash, generate_password_hash

from app.data.tournament import GROUPS, TEAMS
from app.services.scoring import build_standings
from app.storage import get_storage


public_bp = Blueprint("public", __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _grupos_fmt():
    """Convert GROUPS/TEAMS to the original {letra: [(iso, name)]} format."""
    return {
        letra: [(TEAMS[tid]["flag"], TEAMS[tid]["name"]) for tid in team_ids]
        for letra, team_ids in GROUPS.items()
    }


def _logged_in():
    return session.get("authenticated", False)


# ---------------------------------------------------------------------------
# ORIGINAL HTML TEMPLATE (from legacy_app.py, adapted url_for + auth views)
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Porra Mundial 2026</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🏆</text></svg>">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Oswald:wght@500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Poppins', sans-serif; background-color: transparent; color: #2c3e50; padding-top: 110px; }
        body.login-page { background-color: #000; padding-top: 0; overflow: hidden; }
        body:not(.login-page) { background: transparent; }
        .header-banner {
            position: fixed; top: 0; left: 0; right: 0; z-index: 1050;
            background: linear-gradient(135deg, #0f5132 0%, #198754 100%);
            color: white; padding: 1rem 1.5rem;
            border-radius: 0 0 40px 40px;
            box-shadow: 0 4px 15px rgba(25, 135, 84, 0.3);
        }
        .header-banner h1 { font-size: clamp(1rem, 2.5vw, 1.6rem); font-weight: 700; letter-spacing: 1px; text-shadow: 1px 1px 3px rgba(0,0,0,0.2); margin: 0; }
        .header-banner p { font-size: clamp(0.65rem, 1.2vw, 0.9rem); font-weight: 400; margin: 0; opacity: 0.9; }
        .card { border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: none; background-color: rgba(255,255,255,0.98); }
        .table-custom-header { background-color: #0f5132 !important; color: white !important; }
        .puntos-oro { color: #d4af37; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }
        .btn-success-custom { background-color: #198754; border: none; border-radius: 8px; transition: all 0.3s ease; }
        .btn-success-custom:hover:not(:disabled) { background-color: #146c43; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(25,135,84,0.3); }
        .btn-success-custom:disabled { opacity: 0.5; cursor: not-allowed; background-color: #6c757d; }
        .btn-outline-custom { color: #0f5132; border-color: #0f5132; border-radius: 8px; }
        .btn-outline-custom:hover { background-color: #0f5132; color: white; }
        select option { font-weight: bold; color: #2c3e50; }
        select option:disabled { font-weight: normal; color: #adb5bd; font-style: italic; }
        .team-checkbox { display: none; }
        .team-label { cursor: pointer; border: 2px solid #dee2e6; border-radius: 8px; padding: 10px; transition: all 0.2s; display: block; text-align: center; background: white; font-weight: 600; }
        .team-checkbox:checked + .team-label { border-color: #198754; background-color: #e8f5e9; color: #0f5132; box-shadow: 0 4px 8px rgba(25,135,84,0.2); transform: scale(1.02); }
        .team-checkbox:disabled + .team-label { opacity: 0.5; cursor: not-allowed; }
        .fase-section { display: none; }
        .fase-active { display: block; animation: fadeIn 0.5s; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }

        /* Próximo partido / EN VIVO en navbar */
        .nav-match-pill {
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 20px;
            padding: 4px 12px;
            font-size: clamp(0.62rem, 1.1vw, 0.78rem);
            color: white;
            white-space: nowrap;
            display: flex; align-items: center; gap: 6px;
        }
        .nav-match-pill.live { background: rgba(220,53,69,0.25); border-color: rgba(220,53,69,0.5); }

        /* Navbar desktop/mobile */
        .nav-desktop { display:none; }
        .nav-mobile  { display:flex; }
        @media (min-width: 768px) {
            .nav-desktop { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:8px; }
            .nav-mobile  { display:none; }
        }

        /* Responsive */
        @media (max-width: 767px) {
            body { padding-top: 130px; }
            .header-banner { padding: .7rem 1rem; }
            .nav-match-pill { font-size: .62rem; padding: 3px 8px; }
            .table td, .table th { font-size: .82rem; padding: .4rem .5rem; }
            .fs-4 { font-size: 1rem !important; }
            .fs-5 { font-size: .9rem !important; }
            .px-4 { padding-left: .75rem !important; padding-right: .75rem !important; }
        }
        @media (max-width: 480px) {
            body { padding-top: 150px; }
            .btn { padding: .35rem .6rem; font-size: .78rem; }
        }

        /* ══════════════════════════════════════
           LOGIN PAGE — estilos exclusivos
        ══════════════════════════════════════ */
        .login-page .header-banner {
            position: relative !important;
            border-radius: 0 0 18px 18px;
            background: rgba(10,46,25,.65) !important;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: 0 2px 20px rgba(0,0,0,.5) !important;
            border-bottom: 1px solid rgba(255,255,255,.1);
        }
        /* Capas de fondo */
        .lp-bg-img {
            position: fixed; inset: 0; z-index: 0;
            background: url('/login-bg.png') center center / cover no-repeat;
        }
        .lp-bg-overlay {
            position: fixed; inset: 0; z-index: 1;
            background: rgba(0,0,0,.18);
        }
        .lp-crowd-canvas, .lp-spot-canvas {
            position: fixed; inset: 0; pointer-events: none;
        }
        .lp-crowd-canvas { z-index: 2; }
        .lp-spot-canvas  { z-index: 3; }
        .lp-confetti-piece {
            position: fixed; top: -24px; z-index: 4; pointer-events: none;
        }
        /* Contenedor login centrado */
        .lp-center {
            position: relative; z-index: 40;
            display: flex; align-items: center; justify-content: center;
            min-height: calc(100vh - 68px);
            padding: 24px 16px;
        }
        /* Texto derecho */
        .lp-right-deco {
            position: fixed; right: 4%; bottom: 10%;
            text-align: right; pointer-events: none; user-select: none;
            z-index: 40;
            animation: lpDecoIn .9s cubic-bezier(.22,1,.36,1) .3s both;
        }
        @keyframes lpDecoIn { from { opacity:0; transform: translateX(30px); } to { opacity:1; transform:none; } }
        .lp-right-deco .lp-trophy {
            font-size: 3.5rem; display: block; text-align: right;
            filter: drop-shadow(0 0 18px rgba(255,200,50,.7));
            animation: lpTrophy 2.8s ease-in-out infinite;
        }
        @keyframes lpTrophy {
            0%,100% { filter: drop-shadow(0 0 18px rgba(255,200,50,.5)); transform: scale(1) translateY(0); }
            50%      { filter: drop-shadow(0 0 34px rgba(255,220,80,1));  transform: scale(1.07) translateY(-4px); }
        }
        .lp-right-deco .lp-slogan {
            font-size: 2.4rem; font-weight: 900; color: #fff;
            text-transform: uppercase; line-height: 1.05; letter-spacing: 1px;
            text-shadow: 3px 3px 0 rgba(0,0,0,.9), 0 0 30px rgba(255,200,50,.3);
        }
        .lp-right-deco .lp-slogan span {
            display: block; color: #f0c040;
            text-shadow: 3px 3px 0 rgba(0,0,0,.9), 0 0 20px rgba(255,200,50,.7);
        }
        /* Card glassmorphism */
        .lp-card {
            background: rgba(10,30,15,.55);
            backdrop-filter: blur(22px) saturate(1.4);
            -webkit-backdrop-filter: blur(22px) saturate(1.4);
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,.13);
            box-shadow: 0 32px 80px rgba(0,0,0,.7),
                        0 0 0 1px rgba(255,255,255,.06) inset,
                        0 1px 0 rgba(255,255,255,.15) inset;
            padding: 44px 48px 40px;
            width: 100%; max-width: 420px;
            position: relative; overflow: hidden;
            animation: lpCardIn .8s cubic-bezier(.22,1,.36,1) both;
        }
        @keyframes lpCardIn { from { opacity:0; transform:translateY(40px) scale(.95); } to { opacity:1; transform:none; } }
        @keyframes lpShimmer { 0% { transform:translateX(-100%); } 100% { transform:translateX(200%); } }
        .lp-card::before {
            content:''; position:absolute; top:0; left:0; right:0; height:2px;
            background: linear-gradient(90deg,transparent 0%,rgba(46,204,113,.0) 10%,rgba(46,204,113,.9) 40%,rgba(240,192,64,1) 50%,rgba(46,204,113,.9) 60%,rgba(46,204,113,.0) 90%,transparent 100%);
            animation: lpShimmer 3s ease-in-out infinite;
        }
        .lp-card::after {
            content:''; position:absolute; bottom:-60px; left:50%; transform:translateX(-50%);
            width:260px; height:120px;
            background: radial-gradient(ellipse, rgba(46,204,113,.18) 0%, transparent 70%);
            pointer-events:none;
        }
        .lp-card-header { text-align:center; margin-bottom:28px; }
        .lp-badge {
            display:inline-flex; align-items:center; gap:8px;
            background: linear-gradient(135deg,rgba(26,92,56,.8),rgba(46,160,80,.6));
            border:1px solid rgba(46,204,113,.3); border-radius:50px;
            padding:6px 18px 6px 10px; margin-bottom:14px;
        }
        .lp-badge-icon {
            width:28px; height:28px;
            background: linear-gradient(135deg,#1a5c38,#2ecc71);
            border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:1rem;
        }
        .lp-badge span { color:rgba(255,255,255,.9); font-size:.78rem; font-weight:700; letter-spacing:.5px; }
        .lp-card h2 { color:#fff; font-size:1.55rem; font-weight:800; letter-spacing:.5px; text-shadow:0 2px 12px rgba(0,0,0,.5); margin-bottom:4px; }
        .lp-card .lp-sub { color:rgba(255,255,255,.5); font-size:.82rem; }
        .lp-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(255,255,255,.12),transparent); margin:20px 0 24px; }
        .lp-input-group { margin-bottom:18px; }
        .lp-input-group label { color:rgba(255,255,255,.75); font-weight:600; font-size:.82rem; display:block; margin-bottom:7px; letter-spacing:.3px; }
        .lp-input-wrap { position:relative; }
        .lp-input-icon { position:absolute; left:14px; top:50%; transform:translateY(-50%); font-size:1rem; opacity:.5; pointer-events:none; }
        .lp-input-wrap input {
            width:100%; padding:13px 14px 13px 40px;
            background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.14);
            border-radius:12px; color:#fff; font-size:.97rem; outline:none;
            transition:border-color .2s,background .2s,box-shadow .2s;
            backdrop-filter:blur(4px); font-family:'Poppins',sans-serif;
        }
        .lp-input-wrap input::placeholder { color:rgba(255,255,255,.25); }
        .lp-input-wrap input:focus { border-color:rgba(46,204,113,.6); background:rgba(255,255,255,.13); box-shadow:0 0 0 3px rgba(46,204,113,.12); }
        .lp-btn {
            width:100%; padding:15px;
            background:linear-gradient(135deg,#1a7a40 0%,#2ecc71 50%,#1a7a40 100%);
            background-size:200% auto; color:#fff; border:none; border-radius:12px;
            font-size:1rem; font-weight:800; cursor:pointer; letter-spacing:1px;
            text-transform:uppercase; font-family:'Poppins',sans-serif;
            box-shadow:0 6px 24px rgba(46,204,113,.35),0 0 0 1px rgba(255,255,255,.1) inset;
            transition:background-position .4s,transform .15s,box-shadow .2s;
            position:relative; overflow:hidden;
        }
        .lp-btn:hover { background-position:right center; transform:translateY(-2px); box-shadow:0 10px 32px rgba(46,204,113,.5),0 0 0 1px rgba(255,255,255,.15) inset; }
        .lp-btn:active { transform:translateY(0); }
        .lp-btn::after { content:''; position:absolute; top:0; left:-80%; width:60%; height:100%; background:linear-gradient(90deg,transparent,rgba(255,255,255,.25),transparent); transform:skewX(-20deg); transition:left .5s; }
        .lp-btn:hover::after { left:130%; }
        .lp-card-footer { text-align:center; margin-top:20px; }
        .lp-card-footer p { color:rgba(255,255,255,.25); font-size:.7rem; letter-spacing:.3px; }
        .lp-alert-error { background:rgba(220,53,69,.2); border:1px solid rgba(220,53,69,.4); color:#f8d7da; border-radius:10px; padding:10px 14px; margin-bottom:16px; font-size:.85rem; text-align:center; }
        @media (max-width:576px) {
            .lp-card { padding:36px 24px 32px; }
            .lp-right-deco { display:none; }
        }

        /* ══════════════════════════════════════════════════════
           INNER PAGE THEMES — Foto de fondo + UI dark glass
        ══════════════════════════════════════════════════════ */

        /* Texto claro en páginas interiores */
        body:not(.login-page) { color: rgba(255,255,255,0.92); }

        /* Capa de foto de fondo */
        .page-bg {
            position: fixed; inset: 0; z-index: -2; pointer-events: none;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
        }
        /* Overlay oscuro encima de la foto */
        .page-bg::after {
            content: ''; position: absolute; inset: 0;
            background: rgba(0,0,0,0.30);
        }
        #page-canvas {
            position: fixed; inset: 0; z-index: -1; pointer-events: none;
        }

        /* Animaciones Ken Burns */
        @keyframes kb-zoom-in  { from { transform: scale(1);    } to { transform: scale(1.10); } }
        @keyframes kb-zoom-out { from { transform: scale(1.10); } to { transform: scale(1);    } }
        @keyframes kb-pan-r    { from { transform: scale(1.06) translateX(-2%); } to { transform: scale(1.06) translateX(2%); } }
        @keyframes kb-pulse    { 0%,100% { filter: brightness(0.88); } 50% { filter: brightness(1.05); } }

        /* ── Fondos por página ── */
        body.page-inicio .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-inicio.png') }}");
            animation: kb-zoom-in 28s ease-out both;
        }
        body.page-fase_grupos .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-fase-grupos.png') }}");
            animation: kb-zoom-out 30s ease-out both;
        }
        body.page-eliminatorias .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-eliminatorias.png') }}");
            animation: kb-pulse 8s ease-in-out infinite;
        }
        body.page-prediccion_completa .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-prediccion-completa.png') }}");
        }
        body.page-ver_grupos .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-ver-grupos.png') }}");
            animation: kb-pan-r 25s ease-in-out alternate infinite;
        }
        body.page-ver_horarios .page-bg,
        body.page-ver_horarios_dinamico .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-ver-horarios.png') }}");
            animation: kb-zoom-out 30s ease-out both;
        }
        body.page-ver_prediccion .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-ver-prediccion.png') }}");
            animation: kb-zoom-in 28s ease-out both;
        }
        body.page-nuevo_nombre .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-nuevo-nombre.png') }}");
            animation: kb-zoom-in 28s ease-out both;
        }
        body.page-ver_eliminatorias .page-bg {
            background-image: url("{{ url_for('static', filename='img/bg-ver-eliminatorias.png') }}");
            animation: kb-zoom-in 30s ease-out both;
        }

        /* ══════════════════════════════════════════════════════
           DARK GLASS UI — cards, tablas, botones, formularios
        ══════════════════════════════════════════════════════ */

        /* Header glassmorphism verde oscuro */
        body:not(.login-page) .header-banner {
            background: rgba(4, 20, 10, 0.72) !important;
            backdrop-filter: blur(20px) saturate(1.6);
            -webkit-backdrop-filter: blur(20px) saturate(1.6);
            box-shadow: 0 4px 32px rgba(0,0,0,0.5) !important;
            border-bottom: 1px solid rgba(255,255,255,0.10);
        }

        /* Cards dark glass */
        body:not(.login-page) .card {
            background: rgba(5, 18, 10, 0.68) !important;
            backdrop-filter: blur(24px) saturate(1.5);
            -webkit-backdrop-filter: blur(24px) saturate(1.5);
            border: 1px solid rgba(255,255,255,0.12) !important;
            box-shadow: 0 20px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.06) inset !important;
            border-radius: 20px !important;
            color: rgba(255,255,255,0.92) !important;
        }
        body:not(.login-page) .card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(46,204,113,0.6), rgba(240,192,64,0.8), rgba(46,204,113,0.6), transparent);
            border-radius: 20px 20px 0 0;
        }
        body:not(.login-page) .card { position: relative; overflow: hidden; }

        /* Tablas dark */
        body:not(.login-page) .table { color: rgba(255,255,255,0.88) !important; }
        body:not(.login-page) .table thead th,
        body:not(.login-page) .table-custom-header {
            background: rgba(15,81,50,0.9) !important;
            color: #fff !important;
            border-bottom: 2px solid rgba(46,204,113,0.4) !important;
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        body:not(.login-page) .table tbody tr {
            border-bottom: 1px solid rgba(255,255,255,0.07) !important;
            transition: background 0.2s;
        }
        body:not(.login-page) .table tbody tr:hover {
            background: rgba(46,204,113,0.10) !important;
        }
        body:not(.login-page) .table td, body:not(.login-page) .table th {
            border-color: rgba(255,255,255,0.07) !important;
            vertical-align: middle;
        }
        body:not(.login-page) .table-striped>tbody>tr:nth-of-type(odd)>* {
            background-color: rgba(255,255,255,0.04) !important;
            color: rgba(255,255,255,0.88) !important;
        }

        /* Badges dark */
        body:not(.login-page) .badge.bg-secondary { background: rgba(108,117,125,0.7) !important; }
        body:not(.login-page) .badge.bg-primary   { background: rgba(13,110,253,0.8) !important; }
        body:not(.login-page) .badge.bg-success    { background: rgba(25,135,84,0.85) !important; }
        body:not(.login-page) .badge.bg-warning    { background: rgba(255,193,7,0.85) !important; color:#000 !important; }
        body:not(.login-page) .badge.bg-dark       { background: rgba(33,37,41,0.9) !important; }

        /* list-group dark */
        body:not(.login-page) .list-group-item {
            background: transparent !important;
            border-color: rgba(255,255,255,0.10) !important;
            color: rgba(255,255,255,0.85) !important;
        }
        body:not(.login-page) .list-group-item.bg-light { background: rgba(255,255,255,0.06) !important; }
        body:not(.login-page) .list-group-item.text-dark { color: rgba(255,255,255,0.88) !important; }
        body:not(.login-page) .list-group-item.text-success { color: #2ecc71 !important; }
        body:not(.login-page) .list-group-item.text-secondary { color: rgba(255,255,255,0.6) !important; }

        /* Botón principal */
        body:not(.login-page) .btn-success-custom {
            background: linear-gradient(135deg, #1a7a40 0%, #2ecc71 50%, #1a7a40 100%) !important;
            background-size: 200% auto !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px;
            box-shadow: 0 6px 20px rgba(46,204,113,0.35) !important;
            transition: background-position 0.4s, transform 0.15s, box-shadow 0.2s !important;
            color: #fff !important;
        }
        body:not(.login-page) .btn-success-custom:hover:not(:disabled) {
            background-position: right center !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 28px rgba(46,204,113,0.5) !important;
        }
        body:not(.login-page) .btn-outline-custom {
            color: rgba(255,255,255,0.85) !important;
            border-color: rgba(255,255,255,0.25) !important;
            border-radius: 12px !important;
            background: rgba(255,255,255,0.07) !important;
            font-weight: 600;
        }
        body:not(.login-page) .btn-outline-custom:hover {
            background: rgba(255,255,255,0.15) !important;
            color: #fff !important;
            border-color: rgba(255,255,255,0.4) !important;
        }
        body:not(.login-page) .btn-secondary {
            background: rgba(108,117,125,0.6) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            border-radius: 12px !important;
            color: #fff !important;
        }

        /* Selects y form controls dark */
        body:not(.login-page) select,
        body:not(.login-page) input[type="text"],
        body:not(.login-page) input[type="number"] {
            background: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 10px !important;
            color: #fff !important;
            backdrop-filter: blur(4px);
        }
        body:not(.login-page) select:focus,
        body:not(.login-page) input:focus {
            border-color: rgba(46,204,113,0.6) !important;
            box-shadow: 0 0 0 3px rgba(46,204,113,0.14) !important;
            background: rgba(255,255,255,0.13) !important;
            outline: none !important;
        }
        body:not(.login-page) select option { background: #0a2010; color: #fff; }
        body:not(.login-page) input::placeholder { color: rgba(255,255,255,0.40) !important; }
        body:not(.login-page) input::-webkit-input-placeholder { color: rgba(255,255,255,0.40) !important; }
        body:not(.login-page) input::-moz-placeholder { color: rgba(255,255,255,0.40) !important; }

        /* Team labels dark */
        body:not(.login-page) .team-label {
            background: rgba(255,255,255,0.07) !important;
            border: 2px solid rgba(255,255,255,0.18) !important;
            color: rgba(255,255,255,0.88) !important;
            border-radius: 10px;
            transition: all 0.2s;
        }
        body:not(.login-page) .team-checkbox:checked + .team-label {
            border-color: #2ecc71 !important;
            background: rgba(46,204,113,0.20) !important;
            color: #fff !important;
            box-shadow: 0 4px 14px rgba(46,204,113,0.30) !important;
        }
        body:not(.login-page) .team-checkbox:disabled + .team-label {
            opacity: 0.35 !important;
        }

        /* Headings dentro de cards — Oswald */
        body:not(.login-page) .card h1,
        body:not(.login-page) .card h2,
        body:not(.login-page) .card h3,
        body:not(.login-page) .card h4,
        body:not(.login-page) .card h5,
        body:not(.login-page) .card h6 {
            color: #fff !important;
            font-family: 'Oswald', 'Poppins', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
        }
        /* Título principal de cada page (h2/h3 fuera de card también) */
        body:not(.login-page) h1, body:not(.login-page) h2,
        body:not(.login-page) h3, body:not(.login-page) h4 {
            font-family: 'Oswald', 'Poppins', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
        }
        /* Header principal */
        body:not(.login-page) .header-banner h1 {
            font-family: 'Oswald', sans-serif !important;
            font-weight: 700 !important;
            letter-spacing: 2px !important;
            font-size: clamp(1.1rem, 2.8vw, 1.8rem) !important;
        }
        body:not(.login-page) .card .text-muted    { color: rgba(255,255,255,0.5) !important; }
        body:not(.login-page) .card .text-success  { color: #2ecc71 !important; }
        body:not(.login-page) .card .text-primary  { color: #74b9ff !important; }
        body:not(.login-page) .card .text-secondary{ color: rgba(255,255,255,0.55) !important; }
        body:not(.login-page) .card .text-dark     { color: rgba(255,255,255,0.88) !important; }
        body:not(.login-page) .card .fw-bold       { color: inherit; }
        body:not(.login-page) .card strong         { color: #fff; }

        /* Modal dark glass */
        body:not(.login-page) .modal-content {
            background: rgba(5,18,10,0.90) !important;
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            border: 1px solid rgba(255,255,255,0.12) !important;
            color: rgba(255,255,255,0.90) !important;
            border-radius: 20px !important;
        }
        body:not(.login-page) .modal-header {
            border-bottom: 1px solid rgba(255,255,255,0.10) !important;
        }
        body:not(.login-page) .modal-footer {
            border-top: 1px solid rgba(255,255,255,0.10) !important;
        }
        body:not(.login-page) .modal-title { color: #fff !important; }
        body:not(.login-page) .btn-close { filter: invert(1) opacity(0.7); }

        /* Puntos oro */
        .puntos-oro { color: #f0c040 !important; text-shadow: 0 0 10px rgba(240,192,64,0.5); }

        /* Nav pills en header — estilo glassmorphism */
        body:not(.login-page) .nav-match-pill {
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.22);
        }
        body:not(.login-page) .nav-match-pill.live {
            background: rgba(220,53,69,0.30);
            border-color: rgba(220,53,69,0.55);
        }

        /* ══ OVERRIDE FORZADO: eliminar todos los fondos blancos ══ */
        body:not(.login-page) .bg-light,
        body:not(.login-page) .bg-white,
        body:not(.login-page) .card.bg-light,
        body:not(.login-page) .card-body.bg-light {
            background: rgba(255,255,255,0.06) !important;
            color: rgba(255,255,255,0.88) !important;
        }
        body:not(.login-page) .bg-white {
            background: rgba(255,255,255,0.07) !important;
        }
        /* Filas y celdas de tablas — transparentes */
        body:not(.login-page) .table,
        body:not(.login-page) .table-responsive,
        body:not(.login-page) .table > :not(caption) > * > *,
        body:not(.login-page) .table tbody,
        body:not(.login-page) .table tbody tr,
        body:not(.login-page) .table tbody td,
        body:not(.login-page) .table tbody th {
            background-color: transparent !important;
            color: rgba(255,255,255,0.88) !important;
            border-color: rgba(255,255,255,0.08) !important;
        }
        body:not(.login-page) .table tbody tr:hover > td,
        body:not(.login-page) .table tbody tr:hover > th {
            background-color: rgba(46,204,113,0.10) !important;
        }
        /* Items de partido / equipo con fondo blanco en horarios y grupos */
        body:not(.login-page) .rounded.bg-white,
        body:not(.login-page) .rounded.border,
        body:not(.login-page) [class*="bg-white"],
        body:not(.login-page) .shadow-sm.bg-white,
        body:not(.login-page) .shadow-sm.border.rounded {
            background: rgba(255,255,255,0.07) !important;
            border-color: rgba(255,255,255,0.12) !important;
            color: rgba(255,255,255,0.88) !important;
        }
        /* Botón Cancelar y todos btn-light en páginas interiores */
        body:not(.login-page) .btn-light,
        body:not(.login-page) .btn.btn-light {
            background: rgba(255,255,255,0.10) !important;
            border: 1px solid rgba(255,255,255,0.22) !important;
            color: rgba(255,255,255,0.80) !important;
            border-radius: 12px !important;
        }
        body:not(.login-page) .btn-light:hover {
            background: rgba(255,255,255,0.20) !important;
            color: #fff !important;
        }
        /* Botones de nav (Inicio, Reglas, Grupos, Horarios) — mantener estilo */
        body:not(.login-page) .header-banner .btn-light {
            background: rgba(255,255,255,0.92) !important;
            color: #0f5132 !important;
            border: none !important;
        }
        body:not(.login-page) .header-banner .btn-light:hover {
            background: #fff !important;
            color: #0f5132 !important;
        }
        /* badge bg-light */
        body:not(.login-page) .badge.bg-light {
            background: rgba(255,255,255,0.15) !important;
            color: rgba(255,255,255,0.7) !important;
        }
        /* text colors genéricos que quedan oscuros */
        body:not(.login-page) .text-muted  { color: rgba(255,255,255,0.50) !important; }
        body:not(.login-page) .text-dark   { color: rgba(255,255,255,0.88) !important; }
        body:not(.login-page) .text-black  { color: #fff !important; }
        body:not(.login-page) p, body:not(.login-page) span, body:not(.login-page) small { color: inherit; }
    </style>
</head>
<body class="{% if vista == 'login_register' %}login-page{% else %}page-{{ vista }}{% endif %}">
    {% if vista != 'login_register' %}
    <div class="page-bg"></div>
    <canvas id="page-canvas"></canvas>
    {% endif %}
    <div class="header-banner">
        <div class="mx-auto" style="max-width:1400px;">

            <!-- DESKTOP: grid 3 columnas -->
            <div class="nav-desktop">
                <div class="d-flex gap-2">
                    {% if authenticated %}
                    <a href="{{ url_for('public.welcome') }}" class="btn btn-light text-success fw-bold px-3">Inicio</a>
                    <button type="button" class="btn btn-light text-success fw-bold px-3" data-bs-toggle="modal" data-bs-target="#modalReglas">Reglas</button>
                    {% endif %}
                </div>
                <div class="text-center">
                    <h1>PORRA MUNDIAL 2026</h1>
                    <p></p>
                </div>
                <div class="d-flex align-items-center gap-2 justify-content-end">
                    {% if authenticated %}
                    <a href="{{ url_for('public.ver_grupos') }}" class="btn btn-light text-success fw-bold px-3">Grupos</a>
                    <a href="{{ url_for('public.ver_horarios') }}" class="btn btn-light text-success fw-bold px-3">Horarios</a>
                    {% endif %}
                </div>
            </div>

            <!-- MOBILE: título + hamburguesa -->
            <div class="nav-mobile justify-content-between align-items-center">
                <div class="text-center flex-grow-1">
                    <h1 style="font-size:1.1rem;margin:0;font-weight:700;">PORRA MUNDIAL 2026</h1>
                    <p style="font-size:.7rem;margin:0;opacity:.85;"></p>
                </div>
                {% if authenticated %}
                <button class="btn btn-light text-success fw-bold px-2 py-1" type="button"
                        data-bs-toggle="collapse" data-bs-target="#mobileMenu" aria-expanded="false">
                    ☰
                </button>
                {% endif %}
            </div>
            {% if authenticated %}
            <!-- MOBILE: menú desplegable -->
            <div class="collapse" id="mobileMenu">
                <div class="d-flex flex-column gap-2 pt-2">
                    <div class="d-flex flex-wrap gap-2 justify-content-center pb-1">
                        <a href="{{ url_for('public.welcome') }}" class="btn btn-light text-success fw-bold px-3">Inicio</a>
                        <button type="button" class="btn btn-light text-success fw-bold px-3" data-bs-toggle="modal" data-bs-target="#modalReglas">Reglas</button>
                        <a href="{{ url_for('public.ver_grupos') }}" class="btn btn-light text-success fw-bold px-3">Grupos</a>
                        <a href="{{ url_for('public.ver_horarios') }}" class="btn btn-light text-success fw-bold px-3">Horarios</a>
                    </div>
                </div>
            </div>
            {% endif %}

        </div>
    </div>

    <div class="container-fluid px-4 mb-5">

        {% if vista == 'inicio' %}

        {# ── BANNER EN VIVO (solo mobile, en desktop va en navbar) ── #}
        {% if live_matches %}
        <div class="mx-auto mb-3 d-md-none" style="max-width:1200px;">
            {% for m in live_matches %}
            <div class="alert mb-2 py-2 px-3 d-flex align-items-center justify-content-between flex-wrap gap-2"
                 style="background:#0f5132;color:white;border-radius:12px;border:none;">
                <span class="badge bg-danger">🔴 EN VIVO</span>
                <span class="fw-bold">
                    {% if m.home.flag %}<img src="https://flagcdn.com/w20/{{ m.home.flag }}.png" width="18" class="me-1">{% endif %}
                    {{ m.home.name }} <span class="text-warning mx-2">{{ m.home_score }}-{{ m.away_score }}</span> {{ m.away.name }}
                    {% if m.away.flag %}<img src="https://flagcdn.com/w20/{{ m.away.flag }}.png" width="18" class="ms-1">{% endif %}
                </span>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="card p-2 p-md-4 mx-auto" style="max-width: 1200px;">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
                    <h3 class="card-title m-0 fw-bold text-success">Clasificación General</h3>
                    <a href="{{ url_for('public.nueva_prediccion') }}" class="btn btn-success-custom text-white fw-bold px-4 py-2">➕ Añadir predicción</a>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-custom-header">
                            <tr>
                                <th scope="col" class="py-3 rounded-start-2">Pos</th>
                                <th scope="col" class="py-3">Nombre</th>
                                <th scope="col" class="text-center py-3">Puntos</th>
                                <th scope="col" class="text-end py-3 rounded-end-2">Predicciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for jug in clasificacion %}
                            <tr>
                                <td class="fw-bold fs-5">
                                    {% if loop.index == 1 %}🥇
                                    {% elif loop.index == 2 %}🥈
                                    {% elif loop.index == 3 %}🥉
                                    {% else %}{{ loop.index }}º{% endif %}
                                </td>
                                <td class="fw-bold fs-5">{{ jug.name }}</td>
                                <td class="text-center fw-bold fs-4 puntos-oro" data-pts="{{ jug.points }}" data-name="{{ jug.name }}">
                                    {{ jug.points }} pts
                                    <span class="pts-delta d-none fw-bold text-success small"></span>
                                </td>
                                <td class="text-end">
                                    <a href="{{ url_for('public.ver_prediccion', participant_id=jug.id) }}" class="btn btn-sm btn-outline-custom px-3">Ver predicción</a>
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

        <style>
            @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
            @keyframes popUp { 0%{opacity:0;transform:translateY(-8px) scale(.8)} 60%{transform:translateY(2px) scale(1.1)} 100%{opacity:1;transform:none} }
            .pts-delta { animation: popUp .5s ease forwards; font-size:1rem; margin-left:6px; }
        </style>

        <script>
        // ── Auto-refresh cada 2 minutos ──────────────────────────────
        setTimeout(function(){ location.reload(); }, 120000);

        // ── Cuenta atrás próximo partido ───────────────────────────────
        {% if next_match and not live_matches %}
        (function(){
            var target = new Date("{{ next_match.utc_date }}");
            function tick(){
                var diff = target - new Date();
                var el = document.getElementById('countdown-nav');
                if(!el) return;
                if(diff <= 0){ el.textContent = '¡Ya!'; return; }
                var h = Math.floor(diff/3600000);
                var m = Math.floor((diff%3600000)/60000);
                var s = Math.floor((diff%60000)/1000);
                el.textContent = (h>0 ? String(h).padStart(2,'0')+':' : '') +
                    String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
                setTimeout(tick, 1000);
            }
            tick();
        })();
        {% endif %}

        // ── Animación de puntos (compara con localStorage) ─────────────
        (function(){
            var stored = {};
            try { stored = JSON.parse(localStorage.getItem('porra_pts') || '{}'); } catch(e){}
            var current = {};
            document.querySelectorAll('[data-pts]').forEach(function(el){
                var name = el.dataset.name;
                var pts  = parseInt(el.dataset.pts);
                current[name] = pts;
                if(stored[name] !== undefined && pts > stored[name]){
                    var delta = el.querySelector('.pts-delta');
                    delta.textContent = '+' + (pts - stored[name]);
                    delta.classList.remove('d-none');
                }
            });
            localStorage.setItem('porra_pts', JSON.stringify(current));
        })();
        </script>

        {% elif vista == 'login_register' %}
        <!-- Capas de fondo -->
        <div class="lp-bg-img"></div>
        <div class="lp-bg-overlay"></div>
        <canvas class="lp-crowd-canvas" id="lpCrowd"></canvas>
        <canvas class="lp-spot-canvas"  id="lpSpot"></canvas>
        <div id="lpConfetti"></div>

        <!-- Card glassmorphism -->
        <div class="lp-center">
          <div class="lp-card">
            <div class="lp-card-header">
              <div class="lp-badge">
                <div class="lp-badge-icon">⚽</div>
                <span>PORRA MUNDIAL 2026</span>
              </div>
              <h2>Porra Mundial 2026</h2>
              <p class="lp-sub">Introduce tu nombre para participar</p>
            </div>
            {% if auth_error %}
            <div class="lp-alert-error">⚠️ {{ auth_error }}</div>
            {% endif %}
            <div class="lp-divider"></div>
            <form method="POST" action="{{ url_for('public.login') }}">
              <div class="lp-input-group">
                <label>Usuario</label>
                <div class="lp-input-wrap">
                  <span class="lp-input-icon">👤</span>
                  <input type="text" name="username" autocomplete="username" placeholder="Tu nombre de usuario" required>
                </div>
              </div>
              <div class="lp-input-group">
                <label>Contraseña</label>
                <div class="lp-input-wrap">
                  <span class="lp-input-icon">🔒</span>
                  <input type="password" name="password" autocomplete="current-password" placeholder="••••••••" required>
                </div>
              </div>
              <button type="submit" class="lp-btn">⚡ Entrar al torneo</button>
            </form>
            <div class="lp-card-footer">
              <p>🏆 USA · México · Canadá 2026</p>
            </div>
          </div>
        </div>

        <script>
        /* ── GRADAS ── */
        (function(){
          const cv=document.getElementById('lpCrowd'), ctx=cv.getContext('2d');
          let W,H; function resize(){W=cv.width=innerWidth;H=cv.height=innerHeight;} resize(); addEventListener('resize',resize);
          const DOTS=280; let dots=[];
          function init(){dots=[];for(let i=0;i<DOTS;i++){dots.push({x:Math.random()*W,y:Math.random()*H*.52,r:1+Math.random()*2.2,hue:Math.floor(Math.random()*360),sat:40+Math.random()*60,alpha:.1+Math.random()*.3,phase:Math.random()*Math.PI*2,speed:.02+Math.random()*.05,waveAmp:2+Math.random()*4,waveFreq:.5+Math.random()*1.5});}} init(); addEventListener('resize',init);
          let f=0;
          function draw(){ctx.clearRect(0,0,W,H);f++;dots.forEach(d=>{const wx=Math.sin(f*.012*d.waveFreq+d.x*.01)*d.waveAmp,pulse=Math.abs(Math.sin(f*d.speed+d.phase)),a=d.alpha*(.5+pulse*.5);ctx.beginPath();ctx.arc(d.x+wx,d.y,d.r,0,Math.PI*2);ctx.fillStyle=`hsla(${d.hue},${d.sat}%,70%,${a})`;ctx.fill();});requestAnimationFrame(draw);}
          draw();
        })();

        /* ── FOCOS ── */
        (function(){
          const cv=document.getElementById('lpSpot'), ctx=cv.getContext('2d');
          let W,H; function resize(){W=cv.width=innerWidth;H=cv.height=innerHeight;} resize(); addEventListener('resize',resize);
          const spots=[
            {ox:.04,oy:.02,baseAng:.55,   angAmp:.30,angSpd:.007,phase:0,   intBase:.14,intAmp:.08,intSpd:.019},
            {ox:.96,oy:.02,baseAng:Math.PI-.55,angAmp:.30,angSpd:.008,phase:2.1,intBase:.14,intAmp:.07,intSpd:.022},
            {ox:.08,oy:.0, baseAng:.65,   angAmp:.20,angSpd:.011,phase:4.2,intBase:.10,intAmp:.06,intSpd:.015},
            {ox:.92,oy:.0, baseAng:Math.PI-.65,angAmp:.20,angSpd:.009,phase:1.3,intBase:.10,intAmp:.06,intSpd:.017},
          ];
          let t=0;
          function draw(){
            ctx.clearRect(0,0,W,H);
            spots.forEach(sp=>{
              const ox=sp.ox*W,oy=sp.oy*H,ang=sp.baseAng+Math.sin(t*sp.angSpd+sp.phase)*sp.angAmp;
              const len=Math.max(W,H)*1.1,tx=ox+Math.cos(ang)*len,ty=oy+Math.sin(ang)*len;
              const intensity=sp.intBase+Math.sin(t*sp.intSpd+sp.phase*1.3)*sp.intAmp;
              const spread=.065,ra=Math.atan2(ty-oy,tx-ox),dist=Math.hypot(tx-ox,ty-oy);
              const g=ctx.createRadialGradient(ox,oy,0,ox,oy,dist);
              g.addColorStop(0,`rgba(255,245,200,${intensity})`);
              g.addColorStop(.3,`rgba(255,245,200,${intensity*.5})`);
              g.addColorStop(1,`rgba(255,245,200,0)`);
              ctx.save();ctx.beginPath();ctx.moveTo(ox,oy);ctx.arc(ox,oy,dist,ra-spread,ra+spread);ctx.closePath();
              ctx.fillStyle=g;ctx.globalCompositeOperation='lighter';ctx.fill();ctx.restore();
              ctx.save();ctx.beginPath();ctx.arc(ox,oy,4,0,Math.PI*2);
              ctx.fillStyle=`rgba(255,245,200,${.7+intensity*2})`;ctx.shadowColor='rgba(255,240,180,1)';ctx.shadowBlur=14;ctx.fill();ctx.restore();
            });
            t++;requestAnimationFrame(draw);
          }
          draw();
        })();

        /* ── CONFETI ── */
        (function(){
          const wrap=document.getElementById('lpConfetti');
          const COLORS=['#f0c040','#2ecc71','#ffffff','#e74c3c','#3498db','#f39c12','#1abc9c','#e91e63','#9c27b0'];
          for(let i=0;i<60;i++){
            const el=document.createElement('div');
            el.className='lp-confetti-piece';
            const color=COLORS[Math.floor(Math.random()*COLORS.length)];
            const isCircle=Math.random()>.55,w=isCircle?5+Math.random()*6:4+Math.random()*7,h=isCircle?w:9+Math.random()*13;
            const left=Math.random()*100,dur=5+Math.random()*9,delay=-(Math.random()*dur),drift=(Math.random()-.5)*120;
            el.style.cssText=`left:${left}vw;width:${w}px;height:${h}px;background:${color};border-radius:${isCircle?'50%':'2px'};opacity:${.7+Math.random()*.3};box-shadow:0 0 4px ${color}88;`;
            el.animate([
              {transform:`translateY(-24px) translateX(0px) rotate(0deg) scaleX(1)`,opacity:0},
              {transform:`translateY(5vh) translateX(${drift*.1}px) rotate(60deg)`,opacity:1,offset:.06},
              {transform:`translateY(50vh) translateX(${drift*.6}px) rotate(300deg) scaleX(-1)`,opacity:.95,offset:.5},
              {transform:`translateY(108vh) translateX(${drift}px) rotate(740deg) scaleX(1)`,opacity:0}
            ],{duration:dur*1000,delay:delay*1000,iterations:Infinity,easing:'linear'});
            wrap.appendChild(el);
          }
        })();
        </script>

        {% elif vista == 'nuevo_nombre' %}
        <div class="row justify-content-center">
            <div class="col-md-8 col-lg-5">
                <div class="card p-2 p-md-4 mt-4">
                    <div class="card-body">
                        <h3 class="mb-4 fw-bold text-success border-bottom pb-3 text-center">➕ Añadir predicción</h3>
                        {% if nombre_error %}
                        <div class="alert alert-danger py-2">{{ nombre_error }}</div>
                        {% endif %}
                        <form method="POST">
                            <div class="mb-4 p-3 mt-3">
                                <label for="nombre" class="form-label fw-bold fs-5 text-success text-center w-100">Introduce tu nombre:</label>
                                <input type="text" autocomplete="off" class="form-control form-control-lg text-center shadow-sm border-success"
                                       id="nombre" name="nombre" required placeholder="Ej: Benito Martínez"
                                       value="{{ suggested_name or '' }}">
                                <p class="text-muted small text-center mt-2">Así aparecerás en la clasificación.</p>
                            </div>
                            <div class="d-flex justify-content-between mt-4 pt-3 border-top">
                                <a href="{{ url_for('public.welcome') }}" class="btn btn-light border px-4 py-2 fw-bold text-secondary">Cancelar</a>
                                <button type="submit" class="btn btn-success-custom text-white px-5 py-2 fw-bold fs-5">Siguiente →</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        {% elif vista == 'ver_eliminatorias' %}
        <div class="card p-3 p-md-4 mx-auto mb-4 bg-transparent border-0 shadow-none" style="max-width: 1400px;">
            <div class="d-flex justify-content-between align-items-center border-bottom border-success pb-3 mb-4">
                <h3 class="m-0 fw-bold text-success">⚔️ Fase Eliminatoria</h3>
                
            </div>
            {% for ronda_label, partidos in rondas.items() %}
            <h5 class="fw-bold text-success mb-3 mt-2">{{ ronda_label }}</h5>
            <div class="row mb-4">
                {% for p in partidos %}
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card shadow-sm border-0 {% if p.is_live %}border-warning border-2{% endif %}">
                        <div class="card-body p-3">
                            <div class="text-center text-muted small mb-2 fw-bold border-bottom pb-2 d-flex justify-content-between">
                                <span>{{ p.fecha }} - {{ p.hora }}</span>
                                {% if p.is_live %}
                                    <span class="badge bg-danger">🔴 EN VIVO</span>
                                {% elif p.is_finished %}
                                    <span class="badge bg-secondary">Finalizado</span>
                                {% else %}
                                    <span class="badge bg-light text-muted border">Pendiente</span>
                                {% endif %}
                            </div>
                            <div class="d-flex justify-content-between align-items-center mt-2">
                                {% set home_name = p.home.name if p.home.name and p.home.name not in ('?','None') else 'Por determinar' %}
                                {% set away_name = p.away.name if p.away.name and p.away.name not in ('?','None') else 'Por determinar' %}
                                <div class="text-end" style="width:40%;">
                                    <span class="fw-bold">{{ home_name }}</span>
                                    {% if p.home.flag and home_name != 'Por determinar' %}<img src="https://flagcdn.com/w20/{{ p.home.flag }}.png" width="20" class="ms-1">{% endif %}
                                </div>
                                <div class="text-center fw-bold fs-5" style="width:20%;">
                                    {% if p.is_finished or p.is_live %}
                                        <span class="text-success">{{ p.home_score }} - {{ p.away_score }}</span>
                                    {% else %}
                                        <span class="text-muted">vs</span>
                                    {% endif %}
                                </div>
                                <div class="text-start" style="width:40%;">
                                    {% if p.away.flag and away_name != 'Por determinar' %}<img src="https://flagcdn.com/w20/{{ p.away.flag }}.png" width="20" class="me-1">{% endif %}
                                    <span class="fw-bold">{{ away_name }}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endfor %}
        </div>

        {% elif vista == 'ver_grupos' %}
        <div class="card p-3 p-md-4 mx-auto mb-4 bg-transparent border-0 shadow-none" style="max-width: 1400px;">
            <div class="d-flex justify-content-between align-items-center border-bottom border-success pb-3 mb-4">
                <h3 class="m-0 fw-bold text-success">Clasificación de Grupos en Directo</h3>
                
            </div>
            <div class="row">
                {% for letra, equipos_ordenados in grupos_ordenados.items() %}
                <div class="col-md-6 col-lg-3 mb-4">
                    <div class="card h-100 shadow-sm border-0 bg-light">
                        <div class="card-header bg-success text-white fw-bold text-center py-2">Grupo {{ letra }}</div>
                        <div class="card-body p-2">
                            <div class="d-flex flex-column gap-2">
                                {% for iso, pais, puesto in equipos_ordenados %}
                                <div class="bg-white border rounded px-2 py-2 shadow-sm d-flex align-items-center justify-content-between">
                                    <div class="d-flex align-items-center gap-2">
                                        <img src="https://flagcdn.com/w20/{{ iso }}.png" width="20" alt="{{ pais }}">
                                        <span class="fw-semibold text-dark small">{{ pais }}</span>
                                    </div>
                                    {% if puesto == '1º' %}<span class="badge bg-success shadow-sm">{{ puesto }}</span>
                                    {% elif puesto == '2º' %}<span class="badge bg-primary shadow-sm">{{ puesto }}</span>
                                    {% elif puesto == '3º' %}<span class="badge bg-warning text-dark shadow-sm">{{ puesto }}</span>
                                    {% else %}<span class="badge bg-secondary opacity-25">-</span>{% endif %}
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        {% elif vista == 'ver_horarios_dinamico' %}
        <div class="card p-3 p-md-4 mx-auto mb-4 bg-transparent border-0 shadow-none" style="max-width: 1400px;">
            <div class="d-flex justify-content-between align-items-center border-bottom border-success pb-3 mb-4">
                <h3 class="m-0 fw-bold text-success">📅 Partidos del Mundial (Hora Peninsular)</h3>
                
            </div>
            <div class="row">
                {% for sec_key, sec in sections.items() %}
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card h-100 shadow-sm border-0 bg-light">
                        <div class="card-header bg-success text-white fw-bold text-center py-2">{{ sec.label }}</div>
                        <div class="card-body p-3">
                            <div class="d-flex flex-column gap-3">
                                {% for p in sec.partidos %}
                                <div class="bg-white border rounded p-2 shadow-sm {% if p.is_live %}border-warning border-2{% endif %}">
                                    <div class="text-center text-muted small mb-2 fw-bold border-bottom pb-1 d-flex justify-content-between align-items-center px-1">
                                        <span class="text-success">{{ p.jornada or p.stage_label }}</span>
                                        <span>{{ p.fecha }} - {{ p.hora }}</span>
                                        {% if p.is_live %}
                                        <span class="badge bg-danger">EN VIVO</span>
                                        {% elif p.is_finished %}
                                        <span class="badge bg-secondary">Finalizado</span>
                                        {% endif %}
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div class="text-end" style="width:40%; font-size:0.9rem;">
                                            <span class="fw-bold">{{ p.home.name }}</span>
                                            {% if p.home.flag %}<img src="https://flagcdn.com/w20/{{ p.home.flag }}.png" width="20" class="ms-1">{% endif %}
                                        </div>
                                        <div class="text-center fw-bold" style="width:20%;">
                                            {% if p.is_finished or p.is_live %}
                                            <span class="text-success fs-5">{{ p.home_score }} - {{ p.away_score }}</span>
                                            {% else %}
                                            <span class="text-secondary">vs</span>
                                            {% endif %}
                                        </div>
                                        <div class="text-start" style="width:40%; font-size:0.9rem;">
                                            {% if p.away.flag %}<img src="https://flagcdn.com/w20/{{ p.away.flag }}.png" width="20" class="me-1">{% endif %}
                                            <span class="fw-bold">{{ p.away.name }}</span>
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

        {% elif vista == 'ver_horarios' %}
        <div class="card p-3 p-md-4 mx-auto mb-4 bg-transparent border-0 shadow-none" style="max-width: 1400px;">
            <div class="d-flex justify-content-between align-items-center border-bottom border-success pb-3 mb-4">
                <h3 class="m-0 fw-bold text-success">📅 Horarios del Mundial (Hora Peninsular)</h3>
                
            </div>
            <div class="row">
                {% for letra, partidos in calendario.items() %}
                <div class="col-md-6 col-lg-4 mb-4">
                    <div class="card h-100 shadow-sm border-0 bg-light">
                        <div class="card-header bg-success text-white fw-bold text-center py-2">Grupo {{ letra }}</div>
                        <div class="card-body p-3">
                            <div class="d-flex flex-column gap-3">
                                {% for p in partidos %}
                                <div class="bg-white border rounded p-2 shadow-sm">
                                    <div class="text-center text-muted small mb-2 fw-bold border-bottom pb-1">
                                        <span class="text-success">{{ p.jornada }}</span> • {{ p.fecha }} - {{ p.hora }}
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center">
                                        <div class="text-end" style="width:40%;font-size:0.9rem;">
                                            <span class="fw-bold">{{ p.eq1[1] }}</span>
                                            <img src="https://flagcdn.com/w20/{{ p.eq1[0] }}.png" width="20" alt="{{ p.eq1[1] }}" class="ms-1">
                                        </div>
                                        <div class="text-center fw-bold text-secondary" style="width:20%;">vs</div>
                                        <div class="text-start" style="width:40%;font-size:0.9rem;">
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
        <style>
            .pred-ok  { background:#d4edda!important; color:#155724!important; border-color:#28a745!important; }
            .pred-fail{ background:#f8d7da!important; color:#721c24!important; border-color:#dc3545!important; }
            .pred-none{ background:#fff!important;    color:#333!important;    border-color:#ccc!important; }
        </style>
        <div class="card p-3 p-md-4 mx-auto" style="max-width: 1200px;">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center border-bottom pb-3 mb-4">
                    <h3 class="m-0 fw-bold text-success">Predicción de {{ nombre }}</h3>
                    <small class="text-muted">🟢 Acertado &nbsp; 🔴 Fallado &nbsp; ⚪ Sin resultado aún</small>
                </div>

                <h5 class="fw-bold text-secondary mb-3">Fase de Grupos</h5>
                <div class="row g-3 mb-5">
                    {% for letra in ['A','B','C','D','E','F','G','H','I','J','K','L'] %}
                        {% set p1 = predicciones.get('grupos',{}).get('g_' ~ letra ~ '_1', '') %}
                        {% set p2 = predicciones.get('grupos',{}).get('g_' ~ letra ~ '_2', '') %}
                        {% set p3 = predicciones.get('grupos',{}).get('g_' ~ letra ~ '_3', '') %}
                        {% set r1 = resultados.get('g_' ~ letra.lower() ~ '_1', '') %}
                        {% set r2 = resultados.get('g_' ~ letra.lower() ~ '_2', '') %}
                        {% set r3 = resultados.get('g_' ~ letra.lower() ~ '_3', '') %}
                        {% set clasificados_reales = [r1, r2, r3] | select | list %}
                        <div class="col-6 col-md-4 col-lg-3">
                            <div class="card shadow-sm h-100 border-0 bg-light">
                                <div class="card-header bg-success text-white text-center fw-bold py-2">Grupo {{ letra }}</div>
                                <div class="card-body p-2 text-center small">
                                    {% if p1 %}
                                    {% set c1 = 'pred-ok' if p1 == r1 else ('pred-fail' if r1 else 'pred-none') %}
                                    <div class="fw-bold mb-1 rounded px-1 {{ c1 }}"><span class="me-1">1º</span>{{ p1 }}</div>
                                    {% endif %}
                                    {% if p2 %}
                                    {% set c2 = 'pred-ok' if p2 == r2 else ('pred-fail' if r2 else 'pred-none') %}
                                    <div class="fw-bold mb-1 rounded px-1 {{ c2 }}"><span class="me-1">2º</span>{{ p2 }}</div>
                                    {% endif %}
                                    {% if p3 %}
                                    {% set c3 = 'pred-ok' if p3 == r3 else ('pred-fail' if r3 else 'pred-none') %}
                                    <div class="fw-bold rounded px-1 {{ c3 }}"><span class="me-1">3º</span>{{ p3 }}</div>
                                    {% endif %}
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                </div>

                <h5 class="fw-bold text-secondary mb-3 border-top pt-4">Rondas Finales</h5>
                <div class="row g-4">
                    {% for ronda, label in [('octavos','Octavos de Final'),('cuartos','Cuartos de Final'),('semis','Semifinales'),('final','La Final')] %}
                    {% set equipos_pred = predicciones.get('eliminatorias',{}).get(ronda, []) %}
                    {% set equipos_real = resultados.get(ronda, []) %}
                    <div class="col-md-6">
                        <h6 class="bg-success text-white p-2 rounded text-center fw-bold">{{ label }}</h6>
                        <div class="d-flex flex-wrap justify-content-center gap-1">
                            {% for eq in equipos_pred %}
                                {% if equipos_real %}
                                    {% set cls = 'pred-ok' if eq in equipos_real else 'pred-fail' %}
                                {% else %}
                                    {% set cls = 'pred-none' %}
                                {% endif %}
                                <span class="badge border p-2 {{ cls }}">{{ eq }}</span>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>

                <div class="row mt-5 justify-content-center text-center bg-light p-4 rounded-4 shadow-sm mx-1">
                    {% set pred_sub = predicciones.get('eliminatorias',{}).get('subcampeon', '') %}
                    {% set pred_camp = predicciones.get('eliminatorias',{}).get('campeon', '') %}
                    {% set pred_pich = predicciones.get('eliminatorias',{}).get('pichichi', '') %}
                    {% set real_sub  = resultados.get('subcampeon', '') %}
                    {% set real_camp = resultados.get('campeon', '') %}
                    {% set real_pich = (resultados.get('pichichi', [''])[0] if resultados.get('pichichi') else '') %}

                    <div class="col-md-4 mb-3 mb-md-0 border-end border-2">
                        <h6 class="text-muted fw-bold mb-2">SUBCAMPEÓN</h6>
                        {% set cs = 'text-success' if (pred_sub and pred_sub == real_sub) else ('text-danger' if real_sub else 'text-secondary') %}
                        <h4 class="fw-bold {{ cs }} m-0">{{ pred_sub or '-' }}
                            {% if pred_sub and real_sub %}{% if pred_sub == real_sub %} ✅{% else %} ❌{% endif %}{% endif %}
                        </h4>
                    </div>
                    <div class="col-md-4 mb-3 mb-md-0 border-end border-2">
                        <h6 class="text-warning fw-bold mb-2">🏆 CAMPEÓN MUNDIAL</h6>
                        {% set cc = 'text-success' if (pred_camp and pred_camp == real_camp) else ('text-danger' if real_camp else 'text-success') %}
                        <h3 class="fw-bold {{ cc }} m-0">{{ pred_camp or '-' }}
                            {% if pred_camp and real_camp %}{% if pred_camp == real_camp %} ✅{% else %} ❌{% endif %}{% endif %}
                        </h3>
                    </div>
                    <div class="col-md-4">
                        <h6 class="text-primary fw-bold mb-2">⚽ PICHICHI</h6>
                        {% set cp = 'text-success' if (pred_pich and pred_pich.lower() == real_pich.lower()) else ('text-danger' if real_pich else 'text-dark') %}
                        <h4 class="fw-bold {{ cp }} m-0">{{ pred_pich or '-' }}
                            {% if pred_pich and real_pich %}{% if pred_pich.lower() == real_pich.lower() %} ✅{% else %} ❌{% endif %}{% endif %}
                        </h4>
                    </div>
                </div>
            </div>
        </div>

        {% elif vista == 'fase_grupos' %}
        <div class="card p-3 mb-4 shadow-sm border-start border-success border-4 mx-auto" style="max-width:1200px;">
            <h5 class="fw-bold text-success mb-2">📋 Reglas de Clasificación de la Fase de Grupos</h5>
            <p class="text-muted small mb-2">
                En el Mundial 2026, se clasifican para dieciseisavos de final los dos primeros equipos de cada grupo y además los 8 mejores terceros clasificados en general.<br>Por tanto:
            </p>
            <ul class="text-muted small" style="line-height:1.6;">
                <li>Debes seleccionar obligatoriamente el <strong>1º y 2º puesto</strong> de cada uno de los 12 grupos.</li>
                <li>Debes elegir exactamente a <strong>8 equipos como mejores terceros</strong> en total.</li>
            </ul>
            <p class="text-muted small mb-0">El botón para avanzar al final de la página se habilitará automáticamente cuando completes todos los requisitos.</p>
        </div>

        <form method="POST" class="mx-auto" style="max-width:1400px;">
            <div class="row">
                {% for letra, equipos in grupos.items() %}
                <div class="col-md-6 col-lg-3 mb-4">
                    <div class="card h-100 shadow-sm">
                        <div class="card-header bg-success text-white fw-bold text-center fs-5">Grupo {{ letra }}</div>
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
                                    <option value="{{ pais }}" {{ 'selected' if saved.get('g_' ~ letra ~ '_1') == pais }}>{{ pais }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-2">
                                <label class="form-label text-muted small fw-bold mb-1">2º Puesto <span class="text-danger">*</span></label>
                                <select class="form-select form-select-sm fw-bold border-secondary text-secondary" name="g_{{ letra }}_2" required>
                                    <option value="" disabled selected hidden>Elegir 2º...</option>
                                    {% for iso, pais in equipos %}
                                    <option value="{{ pais }}" {{ 'selected' if saved.get('g_' ~ letra ~ '_2') == pais }}>{{ pais }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="mb-2">
                                <label class="form-label text-muted small fw-bold mb-1">Mejor 3º (Opcional)</label>
                                <select class="form-select form-select-sm border-secondary text-secondary select-tercero" name="g_{{ letra }}_3">
                                    <option value="">Ninguno / Eliminado</option>
                                    {% for iso, pais in equipos %}
                                    <option value="{{ pais }}" {{ 'selected' if saved.get('g_' ~ letra ~ '_3') == pais }}>{{ pais }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            <div class="card p-4 mt-2 shadow-sm text-center mx-auto mb-5" style="max-width:1200px;">
                <div class="mb-3 d-flex justify-content-center gap-3 flex-wrap">
                    <span id="counter-grupos" class="badge bg-danger fs-6 p-2">Grupos: 0 / 12 completados</span>
                    <span id="terceros-counter" class="badge bg-danger fs-6 p-2">Mejores Terceros: 0 / 8 elegidos</span>
                </div>
                <button type="submit" id="btn-siguiente" class="btn btn-success-custom text-white px-5 py-3 fw-bold fs-5 mx-auto" disabled>Continuar</button>
            </div>
        </form>

        <script>
            function validarFormulario() {
                let gruposCompletos = 0, tercerosContados = 0;
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
                document.querySelectorAll("select").forEach(s => s.addEventListener("change", validarFormulario));
                validarFormulario();
            });
        </script>

        {% elif vista == 'prediccion_completa' %}
        {# ── RESUMEN FASE DE GRUPOS (solo lectura) ── #}
        <div class="card p-3 mb-4 shadow-sm mx-auto" style="max-width:1400px;">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h5 class="fw-bold text-success m-0">✅ Fase de Grupos guardada</h5>
                <a href="{{ url_for('public.grupos_fase') }}" class="btn btn-sm btn-outline-custom px-3">✏️ Modificar grupos</a>
            </div>
            <div class="row g-2">
                {% for letra, equipos in grupos.items() %}
                <div class="col-6 col-md-3 col-lg-2">
                    <div class="card border-0 bg-light h-100">
                        <div class="card-header bg-success text-white text-center fw-bold py-1 small">Grupo {{ letra }}</div>
                        <div class="card-body p-2 text-center small">
                            {% set p1 = saved.get('g_' ~ letra ~ '_1', '—') %}
                            {% set p2 = saved.get('g_' ~ letra ~ '_2', '—') %}
                            {% set p3 = saved.get('g_' ~ letra ~ '_3', '') %}
                            <div class="fw-bold"><span class="text-success">1º</span> {{ p1 }}</div>
                            <div class="fw-bold"><span class="text-primary">2º</span> {{ p2 }}</div>
                            {% if p3 %}<div class="text-muted"><span class="text-warning">3º</span> {{ p3 }}</div>{% endif %}
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        {# ── FASE ELIMINATORIA ── #}
        <div class="card p-4 mx-auto shadow-sm" style="max-width:1200px;">
            <h3 class="fw-bold text-success border-bottom pb-3 text-center">Fase Eliminatoria - {{ nombre }}</h3>
            <form method="POST" action="{{ url_for('public.eliminatorias_fase') }}" id="form-eliminatorias">
                <div id="sec-octavos" class="fase-section fase-active mb-5">
                    <div class="mb-4">
                        <h6 class="text-center fw-bold text-success mb-1">🏟️ Emparejamientos de Dieciseisavos</h6>
                        <div class="mx-auto mb-3" style="max-width:100%; background:rgba(46,204,113,0.10); border-left:4px solid rgba(46,204,113,0.7); border-radius:6px; padding:16px 20px; text-align:center; backdrop-filter:blur(8px);">
                            <div style="color:rgba(255,255,255,0.88); font-size:.98rem; font-weight:500; line-height:1.6;">
                                <div>ℹ️ &nbsp;Así es como quedarían los cruces de acuerdo a tus predicciones en la fase de grupos.</div>
                                <div><strong>El cuadro real se conocerá cuando finalice la fase de grupos.</strong></div>
                            </div>
                        </div>
                        <div class="row g-2" id="matchups-r32"></div>
                    </div>
                    <hr>
                    <h5 class="bg-success text-white p-2 rounded text-center mb-3">1. Selecciona 16 equipos para OCTAVOS DE FINAL</h5>
                    <p class="text-center text-muted small mb-2">Ahora marca libremente los equipos que crees que pasan. Puedes marcar los dos de un partido, uno solo, o ninguno.</p>
                    <div class="text-center mb-3"><span id="count-octavos" class="badge bg-warning text-dark fs-6">0 / 16 seleccionados</span></div>
                    <div class="row g-2" id="bracket-container"></div>
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
        <style>
            /* ── Bracket tree ───────────────────────────────────────────────── */
            .bkt-wrap { display:flex; overflow-x:auto; justify-content:center; align-items:stretch; min-height:600px; padding:4px 0 8px; }
            .bkt-half { display:flex; align-items:stretch; flex:0 0 auto; }
            .bkt-half-l { flex-direction:row; }
            .bkt-half-r { flex-direction:row; }
            .bkt-center { display:flex; align-items:center; justify-content:center; flex-shrink:0; padding:0 6px; font-size:2.8rem; }

            /* Columns */
            .bkt-col { display:flex; flex-direction:column; flex-shrink:0; }
            .bkt-col-r32 { width:188px; }
            .bkt-col-mid { width:100px; }

            /* Groups — 2 children, bracket arm on the side */
            .bkt-grp { flex:1; display:flex; flex-direction:column; position:relative; gap:4px; padding:4px 0; }

            /* Left pathway: arm on RIGHT */
            .bkt-half-l .bkt-col-r32 .bkt-grp,
            .bkt-half-l .bkt-col-mid .bkt-grp { padding-right:14px; }
            .bkt-half-l .bkt-col-r32 .bkt-grp::after,
            .bkt-half-l .bkt-col-mid .bkt-grp::after {
                content:''; position:absolute; right:0; top:25%; height:50%; width:14px;
                border-top:2px solid #adb5bd; border-right:2px solid #adb5bd; border-bottom:2px solid #adb5bd;
                border-radius:0 4px 4px 0;
            }
            /* SF → Final tick */
            .bkt-half-l .bkt-col-sf .bkt-grp { padding-right:8px; }
            .bkt-half-l .bkt-col-sf .bkt-grp::after {
                content:''; position:absolute; right:0; top:50%; width:8px; height:0;
                border-top:2px solid #adb5bd; transform:translateY(-1px);
            }

            /* Right pathway: arm on LEFT */
            .bkt-half-r .bkt-col-r32 .bkt-grp,
            .bkt-half-r .bkt-col-mid .bkt-grp { padding-left:14px; }
            .bkt-half-r .bkt-col-r32 .bkt-grp::after,
            .bkt-half-r .bkt-col-mid .bkt-grp::after {
                content:''; position:absolute; left:0; top:25%; height:50%; width:14px;
                border-top:2px solid #adb5bd; border-left:2px solid #adb5bd; border-bottom:2px solid #adb5bd;
                border-radius:4px 0 0 4px;
            }
            .bkt-half-r .bkt-col-sf .bkt-grp { padding-left:8px; }
            .bkt-half-r .bkt-col-sf .bkt-grp::after {
                content:''; position:absolute; left:0; top:50%; width:8px; height:0;
                border-top:2px solid #adb5bd; transform:translateY(-1px);
            }

            /* R32 match slot */
            .bkt-mslot { flex:1; min-height:56px; background:rgba(5,20,10,0.72); border:1px solid rgba(255,255,255,0.15); border-radius:6px; overflow:hidden; backdrop-filter:blur(8px); }
            .bkt-mslot-l { border:2px solid rgba(46,204,113,0.7); box-shadow:0 0 8px rgba(46,204,113,0.2); }
            .bkt-mslot-r { border:2px solid rgba(100,160,255,0.7); box-shadow:0 0 8px rgba(100,160,255,0.2); }
            .bkt-mrow { display:flex; align-items:center; gap:6px; padding:6px 8px; font-size:.75rem; font-weight:600; color:rgba(255,255,255,0.88); }
            .bkt-mrow + .bkt-mrow { border-top:1px solid rgba(255,255,255,0.08); }
            .bkt-mflag { width:18px; height:13px; border-radius:2px; object-fit:cover; flex-shrink:0; }
            .bkt-mname { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
            .bkt-mtbd { color:rgba(255,255,255,0.3); font-style:italic; font-weight:400; font-size:.68rem; }

            /* Placeholder slots (R16, QF, SF) */
            .bkt-ph { flex:none; height:60px; background:rgba(5,20,10,0.55); border:1px solid rgba(255,255,255,0.10); border-radius:5px; display:flex; align-items:center; justify-content:center; font-size:.58rem; color:rgba(255,255,255,0.3); }
            .bkt-col-mid .bkt-grp { justify-content:space-around; }

            /* Connector arms — color verde/dorado */
            .bkt-half-l .bkt-col-r32 .bkt-grp::after,
            .bkt-half-l .bkt-col-mid .bkt-grp::after,
            .bkt-half-l .bkt-col-sf .bkt-grp::after {
                border-color: rgba(46,204,113,0.45) !important;
            }
            .bkt-half-r .bkt-col-r32 .bkt-grp::after,
            .bkt-half-r .bkt-col-mid .bkt-grp::after,
            .bkt-half-r .bkt-col-sf .bkt-grp::after {
                border-color: rgba(100,160,255,0.45) !important;
            }

            /* Thirds pool */
            .bkt-thirds { text-align:center; margin-top:14px; padding-top:12px; border-top:1px dashed rgba(255,255,255,0.15); }
            .bkt-third-pill {
                display:inline-flex; align-items:center; gap:6px;
                background:rgba(5,20,10,0.72); color:rgba(255,255,255,0.88); border:2px solid rgba(253,126,20,0.6);
                border-radius:20px; padding:7px 14px;
                font-size:.82rem; font-weight:700; margin:4px;
                backdrop-filter:blur(8px);
                box-shadow: 0 0 8px rgba(253,126,20,0.2);
            }
        </style>
        <script>
            const savedGroups = {{ saved | tojson }};

            const FLAG_MAP = {
                "México":"mx","Sudáfrica":"za","Corea del Sur":"kr","Chequia":"cz",
                "Canadá":"ca","Bosnia y Herzegovina":"ba","Qatar":"qa","Suiza":"ch",
                "Brasil":"br","Marruecos":"ma","Haití":"ht","Escocia":"gb-sct",
                "Estados Unidos":"us","Paraguay":"py","Australia":"au","Turquía":"tr",
                "Alemania":"de","Curazao":"cw","Costa de Marfil":"ci","Ecuador":"ec",
                "Países Bajos":"nl","Japón":"jp","Suecia":"se","Túnez":"tn",
                "Bélgica":"be","Egipto":"eg","Irán":"ir","Nueva Zelanda":"nz",
                "España":"es","Cape Verde":"cv","Cabo Verde":"cv","Arabia Saudita":"sa","Uruguay":"uy",
                "Francia":"fr","Senegal":"sn","Iraq":"iq","Irak":"iq","Noruega":"no",
                "Argentina":"ar","Argelia":"dz","Austria":"at","Jordania":"jo",
                "Portugal":"pt","RD Congo":"cd","Uzbekistán":"uz","Colombia":"co",
                "Inglaterra":"gb-eng","Croacia":"hr","Ghana":"gh","Panamá":"pa",
            };

            /* 16 R32 matchups grouped by pathway (L = Camino 1, R = Camino 2) */
            const MATCHUPS_R32 = {
                L: [
                    {h:{p:'2',g:'A'}, a:{p:'2',g:'B'}},
                    {h:{p:'1',g:'E'}, a:{p:'3',g:null}},
                    {h:{p:'1',g:'F'}, a:{p:'2',g:'C'}},
                    {h:{p:'1',g:'I'}, a:{p:'3',g:null}},
                    {h:{p:'2',g:'K'}, a:{p:'2',g:'L'}},
                    {h:{p:'1',g:'H'}, a:{p:'2',g:'J'}},
                    {h:{p:'1',g:'D'}, a:{p:'3',g:null}},
                    {h:{p:'1',g:'G'}, a:{p:'3',g:null}},
                ],
                R: [
                    {h:{p:'1',g:'C'}, a:{p:'2',g:'F'}},
                    {h:{p:'2',g:'E'}, a:{p:'2',g:'I'}},
                    {h:{p:'1',g:'A'}, a:{p:'3',g:null}},
                    {h:{p:'1',g:'L'}, a:{p:'3',g:null}},
                    {h:{p:'1',g:'J'}, a:{p:'2',g:'H'}},
                    {h:{p:'2',g:'D'}, a:{p:'2',g:'G'}},
                    {h:{p:'1',g:'B'}, a:{p:'3',g:null}},
                    {h:{p:'1',g:'K'}, a:{p:'3',g:null}},
                ],
            };

            function mrow(slot) {
                if (!slot.g) return `<div class="bkt-mrow"><span class="bkt-mtbd">Tercero por determinar</span></div>`;
                const name = savedGroups['g_'+slot.g+'_'+slot.p];
                if (!name) return `<div class="bkt-mrow"><span class="bkt-mtbd">${slot.p}º Grupo ${slot.g}</span></div>`;
                const code = FLAG_MAP[name] || '';
                const flag = code ? `<img class="bkt-mflag" src="https://flagcdn.com/w20/${code}.png" alt="">` : '';
                return `<div class="bkt-mrow">${flag}<span class="bkt-mname">${name}</span></div>`;
            }

            function mslot(m, path) {
                return `<div class="bkt-mslot bkt-mslot-${path.toLowerCase()}">${mrow(m.h)}${mrow(m.a)}</div>`;
            }

            function ph() { return `<div class="bkt-ph"></div>`; }

            function r32col(matches, path) {
                let html = `<div class="bkt-col bkt-col-r32">`;
                for (let i = 0; i < matches.length; i += 2)
                    html += `<div class="bkt-grp">${mslot(matches[i],path)}${mslot(matches[i+1],path)}</div>`;
                return html + '</div>';
            }

            function midcol(n, extraCls) {
                let html = `<div class="bkt-col bkt-col-mid ${extraCls||''}">`;
                for (let i = 0; i < n; i += 2)
                    html += `<div class="bkt-grp">${ph()}${ph()}</div>`;
                return html + '</div>';
            }

            function sfcol() {
                return `<div class="bkt-col bkt-col-mid bkt-col-sf"><div class="bkt-grp">${ph()}</div></div>`;
            }

            function renderMatchups() {
                const cont = document.getElementById('matchups-r32');
                if (!cont) return;

                // Thirds pool — teams the user picked 3rd in each group
                const thirds = 'ABCDEFGHIJKL'.split('').map(g => {
                    const name = savedGroups['g_'+g+'_3'];
                    if (!name) return null;
                    const code = FLAG_MAP[name] || '';
                    const flag = code ? `<img class="bkt-mflag" src="https://flagcdn.com/w20/${code}.png" alt="">` : '';
                    return `<span class="bkt-third-pill">${flag}${name}</span>`;
                }).filter(Boolean);

                function mobileMatch(m, path) {
                    const cls = path === 'L' ? 'bkt-mslot-l' : 'bkt-mslot-r';
                    return `<div class="bkt-mslot ${cls}" style="margin-bottom:6px;">${mrow(m.h)}${mrow(m.a)}</div>`;
                }

                const isMobile = window.innerWidth <= 768;

                if (isMobile) {
                    const leftMatches = MATCHUPS_R32.L.map(m => mobileMatch(m,'L')).join('');
                    const rightMatches = MATCHUPS_R32.R.map(m => mobileMatch(m,'R')).join('');
                    cont.innerHTML = `
                    <div style="display:flex; gap:8px; width:100%;">
                        <div style="flex:1;">
                            <div class="text-center fw-bold text-success mb-2" style="font-size:.8rem;">Lado Izquierdo</div>
                            ${leftMatches}
                        </div>
                        <div style="flex:1;">
                            <div class="text-center fw-bold primary mb-2" style="font-size:.8rem; color:#0d6efd;">Lado Derecho</div>
                            ${rightMatches}
                        </div>
                    </div>
                    ${thirds.length ? `<div class="bkt-thirds"><strong>Terceros posibles:</strong><div class="mt-2">${thirds.join('')}</div></div>` : ''}`;
                } else {
                    cont.innerHTML = `
                    <div class="bkt-wrap">
                        <div class="bkt-half bkt-half-l">
                            ${r32col(MATCHUPS_R32.L,'L')}
                            ${midcol(4)}
                            ${midcol(2)}
                            ${sfcol()}
                        </div>
                        <div class="bkt-center">🏆</div>
                        <div class="bkt-half bkt-half-r">
                            ${sfcol()}
                            ${midcol(2)}
                            ${midcol(4)}
                            ${r32col(MATCHUPS_R32.R,'R')}
                        </div>
                    </div>
                    ${thirds.length ? `<div class="bkt-thirds"><strong>Terceros posibles:</strong><div class="mt-2">${thirds.join('')}</div></div>` : ''}`;
                }
            }

            function setupFase(origenClase, destinoGrid, destinoPrefijo, maxSelect, counterId, nextSectionId, nameAttr) {
                const checkboxes = document.querySelectorAll('.' + origenClase);
                checkboxes.forEach(chk => {
                    chk.addEventListener('change', function() {
                        const selected = Array.from(checkboxes).filter(c => c.checked).map(c => c.value);
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
                    contenedor.innerHTML += `<div class="col-6 col-md-3"><input type="${type}" name="${nameAttr}" value="${equipo}" id="${prefijoId}_${index}" class="team-checkbox chk-${nameAttr}"><label class="team-label text-truncate" for="${prefijoId}_${index}">${equipo}</label></div>`;
                });
                document.getElementById(sectionId).classList.add('fase-active');
                if(nameAttr === 'cuartos') setupFase('chk-cuartos', 'grid-semis', 'sem', 8, 'count-cuartos', 'sec-semis', 'semis');
                if(nameAttr === 'semis') setupFase('chk-semis', 'grid-final', 'fin', 4, 'count-semis', 'sec-final', 'final');
                if(nameAttr === 'final') setupFase('chk-final', 'grid-campeon', 'camp', 2, 'count-final', 'sec-campeon', 'campeon');
                if(nameAttr === 'campeon') {
                    document.querySelectorAll('.chk-campeon').forEach(radio => {
                        radio.addEventListener('change', function() {
                            const finalistas = Array.from(document.querySelectorAll('.chk-final')).filter(c=>c.checked).map(c=>c.value);
                            document.getElementById('input-subcampeon').value = finalistas.find(f => f !== this.value);
                            document.getElementById('btn-finalizar').classList.remove('d-none');
                        });
                    });
                }
            }
            function limpiarFasesDesde(sectionId) {
                ['sec-cuartos','sec-semis','sec-final','sec-campeon'].forEach((id, i, arr) => {
                    if(arr.indexOf(sectionId) <= i) document.getElementById(id).classList.remove('fase-active');
                });
                document.getElementById('btn-finalizar').classList.add('d-none');
            }
            document.addEventListener('DOMContentLoaded', function() {
                renderMatchups();
                const grupos = 'ABCDEFGHIJKL'.split('');
                const contenedor = document.getElementById('bracket-container');
                grupos.forEach(g => {
                    for (let p = 1; p <= 3; p++) {
                        const equipo = savedGroups['g_'+g+'_'+p];
                        if (equipo) {
                            contenedor.innerHTML += `<div class="col-4 col-md-3 col-lg-2">
                                <input type="checkbox" name="octavos" value="${equipo}" id="oct_${g}${p}" class="team-checkbox chk-octavos">
                                <label class="team-label text-truncate" for="oct_${g}${p}">${equipo}</label>
                            </div>`;
                        }
                    }
                });
                setupFase('chk-octavos', 'grid-cuartos', 'cua', 16, 'count-octavos', 'sec-cuartos', 'cuartos');
                document.getElementById('sec-octavos').scrollIntoView({behavior: 'smooth', block: 'start'});
            });
        </script>

        {% elif vista == 'eliminatorias' %}
        <div class="card p-4 mx-auto shadow-sm" style="max-width:1200px;">
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
                checkboxes.forEach(chk => {
                    chk.addEventListener('change', function() {
                        const selected = Array.from(checkboxes).filter(c => c.checked).map(c => c.value);
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
                    contenedor.innerHTML += `
                        <div class="col-6 col-md-3">
                            <input type="${type}" name="${nameAttr}" value="${equipo}" id="${prefijoId}_${index}" class="team-checkbox chk-${nameAttr}">
                            <label class="team-label text-truncate" for="${prefijoId}_${index}">${equipo}</label>
                        </div>`;
                });
                document.getElementById(sectionId).classList.add('fase-active');
                if(nameAttr === 'cuartos') setupFase('chk-cuartos', 'grid-semis', 'sem', 8, 'count-cuartos', 'sec-semis', 'semis');
                if(nameAttr === 'semis') setupFase('chk-semis', 'grid-final', 'fin', 4, 'count-semis', 'sec-final', 'final');
                if(nameAttr === 'final') setupFase('chk-final', 'grid-campeon', 'camp', 2, 'count-final', 'sec-campeon', 'campeon');
                if(nameAttr === 'campeon') {
                    document.querySelectorAll('.chk-campeon').forEach(radio => {
                        radio.addEventListener('change', function() {
                            const finalistas = Array.from(document.querySelectorAll('.chk-final')).filter(c=>c.checked).map(c=>c.value);
                            const sub = finalistas.find(f => f !== this.value);
                            document.getElementById('input-subcampeon').value = sub;
                            document.getElementById('btn-finalizar').classList.remove('d-none');
                        });
                    });
                }
            }
            function limpiarFasesDesde(sectionId) {
                const fases = ['sec-cuartos', 'sec-semis', 'sec-final', 'sec-campeon'];
                const index = fases.indexOf(sectionId);
                if(index !== -1) { for(let i = index; i < fases.length; i++) document.getElementById(fases[i]).classList.remove('fase-active'); }
                document.getElementById('btn-finalizar').classList.add('d-none');
            }
            setupFase('chk-octavos', 'grid-cuartos', 'cua', 16, 'count-octavos', 'sec-cuartos', 'cuartos');
        </script>

        {% endif %}
    </div>

    <!-- MODAL REGLAS -->
    <div class="modal fade" id="modalReglas" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered modal-lg">
            <div class="modal-content border-0 shadow">
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title fw-bold">📋 Reglas y Puntuaciones</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
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
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">Fase de Grupos (acertar que un equipo se clasifica)<span class="badge bg-secondary rounded-pill">+1 pt</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">Fase de Grupos (acertar también su posición exacta)<span class="badge bg-secondary rounded-pill">+1 pt extra</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">Acertar cada equipo en Octavos de Final<span class="badge bg-primary rounded-pill">+3 pts</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">Acertar cada equipo en Cuartos de Final<span class="badge bg-primary rounded-pill">+5 pts</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">Acertar cada equipo en Semifinales<span class="badge bg-primary rounded-pill">+8 pts</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0">Acertar cada equipo en La Final<span class="badge bg-primary rounded-pill">+12 pts</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0 bg-light mt-2 fw-bold text-secondary">Acertar el Subcampeón<span class="badge bg-warning text-dark rounded-pill">+10 pts</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0 bg-light fw-bold text-success">🏆 Acertar el Campeón Mundial<span class="badge bg-success rounded-pill">+20 pts</span></li>
                        <li class="list-group-item d-flex justify-content-between align-items-center px-0 bg-light fw-bold text-dark">⚽ Acertar el Pichichi (Máximo Goleador)<span class="badge bg-dark rounded-pill">+7 pts</span></li>
                    </ul>
                </div>
                <div class="modal-footer border-0 pt-0">
                    <button type="button" class="btn btn-secondary fw-bold" data-bs-dismiss="modal">Entendido</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    // ── INNER PAGE CANVAS EFFECTS — stadium atmosphere ──────────────────
    (function() {
        const canvas = document.getElementById('page-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        resize(); window.addEventListener('resize', resize);

        // ── Bokeh: círculos de luz difusa (como focos de estadio desenfocados) ──
        const bokeh = Array.from({length: 18}, () => ({
            x: Math.random(), y: Math.random(),
            r: Math.random() * 80 + 30,
            vx: (Math.random() - .5) * .00015,
            vy: (Math.random() - .5) * .0001,
            alpha: Math.random() * .12 + .03,
            phase: Math.random() * Math.PI * 2,
            color: Math.random() > .5
                ? `rgba(255,220,80,`   // dorado
                : `rgba(180,230,255,`, // blanco-azulado (focos)
        }));

        // ── Partículas: polvo de estadio / luz ──
        const dust = Array.from({length: 55}, () => ({
            x: Math.random(), y: Math.random(),
            r: Math.random() * 1.8 + .4,
            vx: (Math.random() - .5) * .0003,
            vy: -(Math.random() * .0004 + .0001),
            alpha: Math.random() * .35 + .08,
            phase: Math.random() * Math.PI * 2,
        }));

        // ── Focos rotativos (2 rayos que barren) ──
        const spotlights = [
            { angle: 0,     speed: .003, color: 'rgba(255,255,255,' },
            { angle: Math.PI, speed: -.002, color: 'rgba(255,230,120,' },
        ];

        let t = 0;
        (function tick() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const W = canvas.width, H = canvas.height;

            // Focos rotativos desde arriba
            spotlights.forEach(sp => {
                sp.angle += sp.speed;
                const cx = W * .5 + Math.cos(sp.angle * .7) * W * .3;
                const targetX = W * .5 + Math.sin(sp.angle) * W * .4;
                const targetY = H * .85;
                const grad = ctx.createLinearGradient(cx, -20, targetX, targetY);
                grad.addColorStop(0, sp.color + '.10)');
                grad.addColorStop(.4, sp.color + '.04)');
                grad.addColorStop(1, sp.color + '0)');
                ctx.beginPath();
                const spread = .06;
                ctx.moveTo(cx, -20);
                ctx.lineTo(targetX - spread * W, targetY);
                ctx.lineTo(targetX + spread * W, targetY);
                ctx.closePath();
                ctx.fillStyle = grad; ctx.fill();
            });

            // Bokeh flotante
            bokeh.forEach(b => {
                b.x += b.vx; b.y += b.vy;
                if (b.x < -.1) b.x = 1.1; if (b.x > 1.1) b.x = -.1;
                if (b.y < -.1) b.y = 1.1; if (b.y > 1.1) b.y = -.1;
                const a = b.alpha * (.5 + .5 * Math.sin(b.phase + t * .012));
                const grad = ctx.createRadialGradient(b.x*W, b.y*H, 0, b.x*W, b.y*H, b.r);
                grad.addColorStop(0, b.color + a + ')');
                grad.addColorStop(1, b.color + '0)');
                ctx.beginPath(); ctx.arc(b.x*W, b.y*H, b.r, 0, Math.PI*2);
                ctx.fillStyle = grad; ctx.fill();
            });

            // Partículas de polvo/luz
            dust.forEach(d => {
                d.x += d.vx; d.y += d.vy;
                if (d.y < -.01) { d.y = 1.01; d.x = Math.random(); }
                if (d.x < 0) d.x = 1; if (d.x > 1) d.x = 0;
                const a = d.alpha * (.4 + .6 * Math.sin(d.phase + t * .02));
                ctx.beginPath(); ctx.arc(d.x*W, d.y*H, d.r, 0, Math.PI*2);
                ctx.fillStyle = `rgba(255,255,220,${a})`; ctx.fill();
            });

            t++; requestAnimationFrame(tick);
        })();
    })();
    // ── end canvas effects ──
    /*
        function drawBall(ctx, cx, cy, r, alpha) {
            ctx.globalAlpha = alpha;
            ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2);
            ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = r*.12; ctx.stroke();
            ctx.fillStyle = 'rgba(255,255,255,0.07)'; ctx.fill();
            // manchas hexagonales simplificadas
            const spots = [[0,-1],[.87,.5],[-.87,.5],[0,.85],[.75,-.5],[-.75,-.5]];
            spots.forEach(([sx,sy]) => {
                ctx.beginPath();
                ctx.arc(cx+sx*r*.55, cy+sy*r*.55, r*.22, 0, Math.PI*2);
                ctx.fillStyle='rgba(0,0,0,0.25)'; ctx.fill();
            });
            ctx.globalAlpha = 1;
        }

        // ── INICIO: balones flotando + campo al fondo ──
        if (page === 'inicio') {
            const balls=Array.from({length:8},()=>({
                x:Math.random(), y:Math.random(),
                r:Math.random()*28+12,
                vx:(Math.random()-.5)*.0004, vy:(Math.random()-.5)*.0003,
                rot:Math.random()*Math.PI*2, rotV:(Math.random()-.5)*.012,
                alpha:Math.random()*.18+.06,
            }));
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                // línea de medio campo sutil
                ctx.strokeStyle='rgba(255,255,255,0.06)'; ctx.lineWidth=2;
                ctx.beginPath(); ctx.moveTo(0,H/2); ctx.lineTo(W,H/2); ctx.stroke();
                ctx.beginPath(); ctx.arc(W/2,H/2,Math.min(W,H)*.12,0,Math.PI*2); ctx.stroke();
                balls.forEach(b=>{
                    b.x+=b.vx; b.y+=b.vy; b.rot+=b.rotV;
                    if(b.x<-.05)b.x=1.05; if(b.x>1.05)b.x=-.05;
                    if(b.y<-.05)b.y=1.05; if(b.y>1.05)b.y=-.05;
                    ctx.save(); ctx.translate(b.x*W,b.y*H); ctx.rotate(b.rot);
                    drawBall(ctx,0,0,b.r,b.alpha);
                    ctx.restore();
                });
                t++; requestAnimationFrame(tick);
            })();
        }

        // ── FASE_GRUPOS: campo de fútbol completo pulsante ──
        else if (page === 'fase_grupos') {
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                const a=0.12+0.06*Math.sin(t*.006);
                ctx.strokeStyle=`rgba(255,255,255,${a})`; ctx.lineWidth=2;
                // rayas de césped
                for(let i=0;i<10;i++){
                    const stripe=W*.88/10;
                    ctx.fillStyle=`rgba(255,255,255,${i%2===0?0.02:0.035})`;
                    ctx.fillRect(W*.06+i*stripe, H*.07, stripe, H*.86);
                }
                ctx.beginPath(); ctx.moveTo(W/2,H*.07); ctx.lineTo(W/2,H*.93); ctx.stroke();
                ctx.beginPath(); ctx.arc(W/2,H/2,Math.min(W,H)*.13,0,Math.PI*2); ctx.stroke();
                ctx.strokeRect(W*.06,H*.07,W*.88,H*.86);
                ctx.strokeRect(W*.06,H*.28,W*.18,H*.44);
                ctx.strokeRect(W*.76,H*.28,W*.18,H*.44);
                ctx.strokeRect(W*.06,H*.38,W*.07,H*.24);
                ctx.strokeRect(W*.87,H*.38,W*.07,H*.24);
                // punto central
                ctx.beginPath(); ctx.arc(W/2,H/2,5,0,Math.PI*2);
                ctx.fillStyle=`rgba(255,255,255,${a*3})`; ctx.fill();
                // arcos de corner
                [[W*.06,H*.07],[W*.94,H*.07],[W*.06,H*.93],[W*.94,H*.93]].forEach(([cx,cy],i)=>{
                    const angle=i*Math.PI/2+Math.PI/4;
                    ctx.beginPath(); ctx.arc(cx,cy,W*.04,angle-Math.PI/4,angle+Math.PI/4);
                    ctx.stroke();
                });
                t++; requestAnimationFrame(tick);
            })();
        }

        // ── ELIMINATORIAS: trofeo de rayos dorados desde abajo ──
        else if (page === 'eliminatorias') {
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height,cx=W/2,cy=H*1.1;
                for(let i=0;i<18;i++){
                    const angle=(i/18)*Math.PI-Math.PI/2+t*.0006;
                    const a=(0.07+0.04*Math.sin(t*.02+i))*(i%2===0?1.6:.7);
                    const spread=Math.PI/18*.65;
                    const gold=i%3!==0;
                    const gx=cx+Math.cos(angle)*H*1.8,gy=cy+Math.sin(angle)*H*1.8;
                    const grad=ctx.createLinearGradient(cx,cy,gx,gy);
                    grad.addColorStop(0,gold?`rgba(240,190,30,${a*2.5})`:`rgba(255,255,255,${a*1.5})`);
                    grad.addColorStop(1,'rgba(240,190,30,0)');
                    ctx.beginPath(); ctx.moveTo(cx,cy);
                    ctx.arc(cx,cy,H*2,angle-spread,angle+spread);
                    ctx.closePath(); ctx.fillStyle=grad; ctx.fill();
                }
                // balón en el centro con brillo
                const pulse=1+0.08*Math.sin(t*.04);
                ctx.save(); ctx.translate(cx,H*.35);
                drawBall(ctx,0,0,22*pulse,0.35+0.1*Math.sin(t*.04));
                ctx.restore();
                t++; requestAnimationFrame(tick);
            })();
        }

        // ── PREDICCION_COMPLETA: confeti en colores de selecciones (verde/dorado/blanco) ──
        else if (page === 'prediccion_completa') {
            const COLORS=['#f0c020','#ffffff','#2ecc71','#27ae60','#f39c12','#ecf0f1'];
            const pieces=Array.from({length:110},()=>({
                x:Math.random(), y:Math.random(),
                vx:(Math.random()-.5)*.004, vy:Math.random()*.006+.002,
                size:Math.random()*9+4, angle:Math.random()*Math.PI*2,
                spin:(Math.random()-.5)*.07,
                color:COLORS[Math.floor(Math.random()*COLORS.length)],
                alpha:Math.random()*.5+.3,
            }));
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                pieces.forEach(p=>{
                    p.x+=p.vx; p.y+=p.vy; p.angle+=p.spin;
                    if(p.y>1.02){p.y=-.02;p.x=Math.random();}
                    ctx.save(); ctx.translate(p.x*W,p.y*H); ctx.rotate(p.angle);
                    ctx.globalAlpha=p.alpha; ctx.fillStyle=p.color;
                    ctx.fillRect(-p.size/2,-p.size/4,p.size,p.size/2.5);
                    ctx.restore();
                });
                ctx.globalAlpha=1; requestAnimationFrame(tick);
            })();
        }

        // ── VER_GRUPOS: ola del estadio (crowd wave) ──
        else if (page === 'ver_grupos') {
            // puntos de aficionados organizados en filas que hacen la ola
            const ROWS=12, COLS=30;
            const crowd=[];
            for(let r=0;r<ROWS;r++) for(let c=0;c<COLS;c++)
                crowd.push({r,c,phase:c*(Math.PI*2/COLS)+r*.3});
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                const cellW=W/COLS, cellH=(H*.6)/ROWS;
                crowd.forEach(p=>{
                    const wave=Math.sin(p.phase+t*.06);
                    const y=H*.15+p.r*cellH - wave*cellH*.35;
                    const a=0.12+0.1*(wave+1)/2;
                    const hue=p.r%2===0?120:100;
                    ctx.beginPath(); ctx.arc((p.c+.5)*cellW, y, cellW*.3, 0, Math.PI*2);
                    ctx.fillStyle=`hsla(${hue},60%,55%,${a})`; ctx.fill();
                });
                t++; requestAnimationFrame(tick);
            })();
        }

        // ── VER_HORARIOS: marcador de estadio con dígitos parpadeantes ──
        else if (page === 'ver_horarios' || page === 'ver_horarios_dinamico') {
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                // cuadrícula verde tipo marcador
                ctx.strokeStyle='rgba(100,220,100,0.06)'; ctx.lineWidth=1;
                const sp=28;
                for(let x=0;x<W;x+=sp){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
                for(let y=0;y<H;y+=sp){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
                // línea scanline de marcador
                const sy=(t*1.5)%H;
                const g=ctx.createLinearGradient(0,sy-50,0,sy+50);
                g.addColorStop(0,'rgba(80,220,80,0)');
                g.addColorStop(.5,'rgba(80,220,80,0.1)');
                g.addColorStop(1,'rgba(80,220,80,0)');
                ctx.fillStyle=g; ctx.fillRect(0,sy-50,W,100);
                // pequeños balones que caen como lluvia
                if(t%90===0 || !tick._balls){
                    tick._balls=tick._balls||[];
                    if(tick._balls.length<12) tick._balls.push({x:Math.random(),y:0,vy:Math.random()*.003+.001,r:Math.random()*6+4,alpha:Math.random()*.2+.1});
                }
                tick._balls=(tick._balls||[]).filter(b=>{
                    b.y+=b.vy;
                    drawBall(ctx,b.x*W,b.y*H,b.r,b.alpha);
                    return b.y<1.05;
                });
                t++; requestAnimationFrame(tick);
            })();
        }

        // ── VER_PREDICCION: trayectorias de balón (arcos parabólicos) ──
        else if (page === 'ver_prediccion') {
            const arcs=Array.from({length:6},()=>({
                x0:Math.random(), x1:Math.random(),
                y0:.8+Math.random()*.15, y1:.75+Math.random()*.2,
                peak:.1+Math.random()*.35,
                prog:Math.random(), speed:Math.random()*.004+.002,
                alpha:Math.random()*.15+.06,
                r:Math.random()*7+5,
            }));
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                arcs.forEach(a=>{
                    a.prog+=a.speed; if(a.prog>1){a.prog=0;a.x0=Math.random();a.x1=Math.random();}
                    const p=a.prog;
                    // traza el arco pasado
                    ctx.beginPath();
                    ctx.strokeStyle=`rgba(255,255,255,${a.alpha*.6})`; ctx.lineWidth=1.5;
                    for(let i=0;i<p;i+=0.02){
                        const bx=(1-i)*a.x0+i*a.x1;
                        const by=(1-i)*i*(-2*a.peak)+((1-i)*a.y0+i*a.y1);
                        i===0?ctx.moveTo(bx*W,by*H):ctx.lineTo(bx*W,by*H);
                    }
                    ctx.stroke();
                    // balón en la posición actual
                    const bx=(1-p)*a.x0+p*a.x1;
                    const by=(1-p)*p*(-2*a.peak)+((1-p)*a.y0+p*a.y1);
                    drawBall(ctx,bx*W,by*H,a.r,a.alpha*2);
                });
                t++; requestAnimationFrame(tick);
            })();
        }

        // ── VER_ELIMINATORIAS: bracket lines de torneo ──
        else if (page === 'ver_eliminatorias') {
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                const a=0.1+0.05*Math.sin(t*.007);
                ctx.strokeStyle=`rgba(200,220,200,${a})`; ctx.lineWidth=1.5;
                // dibuja estructura de bracket de 8 equipos (4 rondas)
                const rounds=4, teams=8;
                const colW=W/(rounds+1);
                for(let r=0;r<rounds;r++){
                    const slots=teams>>r;
                    const rowH=H/slots;
                    for(let s=0;s<slots;s+=2){
                        const x1=colW*(r+.5), x2=colW*(r+1.5);
                        const y1=rowH*(s+.5), y2=rowH*(s+1.5), ym=(y1+y2)/2;
                        // líneas verticales de cada equipo
                        ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x1+colW*.4,y1); ctx.stroke();
                        ctx.beginPath(); ctx.moveTo(x1,y2); ctx.lineTo(x1+colW*.4,y2); ctx.stroke();
                        // conector vertical
                        ctx.beginPath(); ctx.moveTo(x1+colW*.4,y1); ctx.lineTo(x1+colW*.4,y2); ctx.stroke();
                        // línea al ganador
                        ctx.beginPath(); ctx.moveTo(x1+colW*.4,ym); ctx.lineTo(x2,ym); ctx.stroke();
                    }
                }
                // balón central con pulso
                const pulse=1+0.1*Math.sin(t*.05);
                ctx.save(); ctx.translate(W/2,H/2);
                drawBall(ctx,0,0,18*pulse,0.3+0.1*Math.sin(t*.05));
                ctx.restore();
                t++; requestAnimationFrame(tick);
            })();
        }

        // ── NUEVO_NOMBRE: líneas de césped creciendo desde abajo ──
        else if (page === 'nuevo_nombre') {
            const blades=Array.from({length:60},()=>({
                x:Math.random(),
                h:Math.random()*.18+.04,
                phase:Math.random()*Math.PI*2,
                width:Math.random()*3+1.5,
                alpha:Math.random()*.25+.08,
            }));
            let t=0;
            (function tick(){
                ctx.clearRect(0,0,canvas.width,canvas.height);
                const W=canvas.width,H=canvas.height;
                blades.forEach(b=>{
                    const sway=Math.sin(b.phase+t*.02)*0.015;
                    const tipX=b.x*W+sway*W;
                    const tipY=H-(b.h+0.04*Math.sin(b.phase+t*.025))*H;
                    const a=b.alpha*(0.6+0.4*Math.sin(b.phase+t*.015));
                    ctx.beginPath();
                    ctx.moveTo(b.x*W,H);
                    ctx.quadraticCurveTo(b.x*W+sway*.5*W, H-(b.h*.6)*H, tipX, tipY);
                    ctx.strokeStyle=`rgba(120,220,100,${a})`; ctx.lineWidth=b.width; ctx.stroke();
                });
                t++; requestAnimationFrame(tick);
            })();
        }
    */
    </script>
</body>
</html>
"""


def _get_match_info():
    """Get live matches and next match for navbar widget."""
    import datetime
    try:
        fixtures = get_storage().load_fixtures()
        live = [f for f in fixtures if f.get("is_live")]
        now_utc = datetime.datetime.utcnow()

        # Sort scheduled fixtures by utc_date ascending to get the earliest one
        scheduled = []
        for f in fixtures:
            if f.get("status") == "SCHEDULED":
                try:
                    if f.get("utc_date"):
                        dt = datetime.datetime.strptime(f["utc_date"], "%Y-%m-%dT%H:%M:%SZ")
                    else:
                        # Fallback: parse fecha + hora as peninsular time (UTC+2)
                        fecha_hora = f.get("fecha", "") + " " + f.get("hora", "00:00") + " 2026"
                        dt = datetime.datetime.strptime(fecha_hora, "%d %b %H:%M %Y") - datetime.timedelta(hours=2)
                    if dt > now_utc:
                        scheduled.append((dt, f))
                except Exception:
                    pass
        scheduled.sort(key=lambda x: x[0])
        nxt = scheduled[0][1] if scheduled else None
        return live, nxt
    except Exception:
        return [], None


def _render(vista, **kwargs):
    live_matches = kwargs.pop("live_matches", None)
    next_match   = kwargs.pop("next_match", None)
    if live_matches is None and next_match is None:
        live_matches, next_match = _get_match_info()
    return render_template_string(
        HTML_TEMPLATE,
        vista=vista,
        authenticated=session.get("authenticated", False),
        live_matches=live_matches,
        next_match=next_match,
        **kwargs,
    )


def _generar_calendario():
    return {
        'A': [
            {'jornada':'Jornada 1','eq1':('mx','México'),'eq2':('za','Sudáfrica'),'fecha':'11 Jun','hora':'21:00'},
            {'jornada':'Jornada 1','eq1':('kr','Corea del Sur'),'eq2':('cz','Chequia'),'fecha':'12 Jun','hora':'04:00'},
            {'jornada':'Jornada 2','eq1':('cz','Chequia'),'eq2':('za','Sudáfrica'),'fecha':'18 Jun','hora':'18:00'},
            {'jornada':'Jornada 2','eq1':('mx','México'),'eq2':('kr','Corea del Sur'),'fecha':'19 Jun','hora':'03:00'},
            {'jornada':'Jornada 3','eq1':('za','Sudáfrica'),'eq2':('kr','Corea del Sur'),'fecha':'25 Jun','hora':'03:00'},
            {'jornada':'Jornada 3','eq1':('cz','Chequia'),'eq2':('mx','México'),'fecha':'25 Jun','hora':'03:00'},
        ],
        'B': [
            {'jornada':'Jornada 1','eq1':('ca','Canadá'),'eq2':('ba','Bosnia y Herzegovina'),'fecha':'12 Jun','hora':'21:00'},
            {'jornada':'Jornada 1','eq1':('qa','Qatar'),'eq2':('ch','Suiza'),'fecha':'13 Jun','hora':'21:00'},
            {'jornada':'Jornada 2','eq1':('ch','Suiza'),'eq2':('ba','Bosnia y Herzegovina'),'fecha':'18 Jun','hora':'21:00'},
            {'jornada':'Jornada 2','eq1':('ca','Canadá'),'eq2':('qa','Qatar'),'fecha':'19 Jun','hora':'00:00'},
            {'jornada':'Jornada 3','eq1':('ba','Bosnia y Herzegovina'),'eq2':('qa','Qatar'),'fecha':'24 Jun','hora':'21:00'},
            {'jornada':'Jornada 3','eq1':('ch','Suiza'),'eq2':('ca','Canadá'),'fecha':'24 Jun','hora':'21:00'},
        ],
        'C': [
            {'jornada':'Jornada 1','eq1':('br','Brasil'),'eq2':('ma','Marruecos'),'fecha':'14 Jun','hora':'00:00'},
            {'jornada':'Jornada 1','eq1':('ht','Haití'),'eq2':('gb-sct','Escocia'),'fecha':'14 Jun','hora':'03:00'},
            {'jornada':'Jornada 2','eq1':('gb-sct','Escocia'),'eq2':('ma','Marruecos'),'fecha':'20 Jun','hora':'00:00'},
            {'jornada':'Jornada 2','eq1':('br','Brasil'),'eq2':('ht','Haití'),'fecha':'20 Jun','hora':'02:30'},
            {'jornada':'Jornada 3','eq1':('gb-sct','Escocia'),'eq2':('br','Brasil'),'fecha':'25 Jun','hora':'00:00'},
            {'jornada':'Jornada 3','eq1':('ma','Marruecos'),'eq2':('ht','Haití'),'fecha':'25 Jun','hora':'00:00'},
        ],
        'D': [
            {'jornada':'Jornada 1','eq1':('us','Estados Unidos'),'eq2':('py','Paraguay'),'fecha':'13 Jun','hora':'03:00'},
            {'jornada':'Jornada 1','eq1':('au','Australia'),'eq2':('tr','Turquía'),'fecha':'14 Jun','hora':'06:00'},
            {'jornada':'Jornada 2','eq1':('us','Estados Unidos'),'eq2':('au','Australia'),'fecha':'19 Jun','hora':'21:00'},
            {'jornada':'Jornada 2','eq1':('tr','Turquía'),'eq2':('py','Paraguay'),'fecha':'20 Jun','hora':'05:00'},
            {'jornada':'Jornada 3','eq1':('tr','Turquía'),'eq2':('us','Estados Unidos'),'fecha':'26 Jun','hora':'04:00'},
            {'jornada':'Jornada 3','eq1':('py','Paraguay'),'eq2':('au','Australia'),'fecha':'26 Jun','hora':'04:00'},
        ],
        'E': [
            {'jornada':'Jornada 1','eq1':('de','Alemania'),'eq2':('cw','Curazao'),'fecha':'14 Jun','hora':'19:00'},
            {'jornada':'Jornada 1','eq1':('ci','Costa de Marfil'),'eq2':('ec','Ecuador'),'fecha':'15 Jun','hora':'01:00'},
            {'jornada':'Jornada 2','eq1':('de','Alemania'),'eq2':('ci','Costa de Marfil'),'fecha':'20 Jun','hora':'22:00'},
            {'jornada':'Jornada 2','eq1':('ec','Ecuador'),'eq2':('cw','Curazao'),'fecha':'21 Jun','hora':'02:00'},
            {'jornada':'Jornada 3','eq1':('ec','Ecuador'),'eq2':('de','Alemania'),'fecha':'25 Jun','hora':'22:00'},
            {'jornada':'Jornada 3','eq1':('cw','Curazao'),'eq2':('ci','Costa de Marfil'),'fecha':'25 Jun','hora':'22:00'},
        ],
        'F': [
            {'jornada':'Jornada 1','eq1':('nl','Países Bajos'),'eq2':('jp','Japón'),'fecha':'14 Jun','hora':'22:00'},
            {'jornada':'Jornada 1','eq1':('se','Suecia'),'eq2':('tn','Túnez'),'fecha':'15 Jun','hora':'04:00'},
            {'jornada':'Jornada 2','eq1':('nl','Países Bajos'),'eq2':('se','Suecia'),'fecha':'20 Jun','hora':'19:00'},
            {'jornada':'Jornada 2','eq1':('tn','Túnez'),'eq2':('jp','Japón'),'fecha':'21 Jun','hora':'06:00'},
            {'jornada':'Jornada 3','eq1':('jp','Japón'),'eq2':('se','Suecia'),'fecha':'26 Jun','hora':'01:00'},
            {'jornada':'Jornada 3','eq1':('tn','Túnez'),'eq2':('nl','Países Bajos'),'fecha':'26 Jun','hora':'01:00'},
        ],
        'G': [
            {'jornada':'Jornada 1','eq1':('be','Bélgica'),'eq2':('eg','Egipto'),'fecha':'15 Jun','hora':'21:00'},
            {'jornada':'Jornada 1','eq1':('ir','Irán'),'eq2':('nz','Nueva Zelanda'),'fecha':'16 Jun','hora':'03:00'},
            {'jornada':'Jornada 2','eq1':('be','Bélgica'),'eq2':('ir','Irán'),'fecha':'21 Jun','hora':'21:00'},
            {'jornada':'Jornada 2','eq1':('nz','Nueva Zelanda'),'eq2':('eg','Egipto'),'fecha':'22 Jun','hora':'03:00'},
            {'jornada':'Jornada 3','eq1':('nz','Nueva Zelanda'),'eq2':('be','Bélgica'),'fecha':'27 Jun','hora':'05:00'},
            {'jornada':'Jornada 3','eq1':('eg','Egipto'),'eq2':('ir','Irán'),'fecha':'27 Jun','hora':'05:00'},
        ],
        'H': [
            {'jornada':'Jornada 1','eq1':('es','España'),'eq2':('cv','Cabo Verde'),'fecha':'15 Jun','hora':'18:00'},
            {'jornada':'Jornada 1','eq1':('sa','Arabia Saudita'),'eq2':('uy','Uruguay'),'fecha':'16 Jun','hora':'00:00'},
            {'jornada':'Jornada 2','eq1':('es','España'),'eq2':('sa','Arabia Saudita'),'fecha':'21 Jun','hora':'18:00'},
            {'jornada':'Jornada 2','eq1':('uy','Uruguay'),'eq2':('cv','Cabo Verde'),'fecha':'22 Jun','hora':'00:00'},
            {'jornada':'Jornada 3','eq1':('uy','Uruguay'),'eq2':('es','España'),'fecha':'27 Jun','hora':'02:00'},
            {'jornada':'Jornada 3','eq1':('cv','Cabo Verde'),'eq2':('sa','Arabia Saudita'),'fecha':'27 Jun','hora':'02:00'},
        ],
        'I': [
            {'jornada':'Jornada 1','eq1':('fr','Francia'),'eq2':('sn','Senegal'),'fecha':'16 Jun','hora':'21:00'},
            {'jornada':'Jornada 1','eq1':('iq','Irak'),'eq2':('no','Noruega'),'fecha':'17 Jun','hora':'00:00'},
            {'jornada':'Jornada 2','eq1':('fr','Francia'),'eq2':('iq','Irak'),'fecha':'22 Jun','hora':'23:00'},
            {'jornada':'Jornada 2','eq1':('no','Noruega'),'eq2':('sn','Senegal'),'fecha':'23 Jun','hora':'02:00'},
            {'jornada':'Jornada 3','eq1':('sn','Senegal'),'eq2':('iq','Irak'),'fecha':'26 Jun','hora':'21:00'},
            {'jornada':'Jornada 3','eq1':('no','Noruega'),'eq2':('fr','Francia'),'fecha':'26 Jun','hora':'21:00'},
        ],
        'J': [
            {'jornada':'Jornada 1','eq1':('ar','Argentina'),'eq2':('dz','Argelia'),'fecha':'17 Jun','hora':'03:00'},
            {'jornada':'Jornada 1','eq1':('at','Austria'),'eq2':('jo','Jordania'),'fecha':'17 Jun','hora':'06:00'},
            {'jornada':'Jornada 2','eq1':('ar','Argentina'),'eq2':('at','Austria'),'fecha':'22 Jun','hora':'19:00'},
            {'jornada':'Jornada 2','eq1':('jo','Jordania'),'eq2':('dz','Argelia'),'fecha':'23 Jun','hora':'05:00'},
            {'jornada':'Jornada 3','eq1':('jo','Jordania'),'eq2':('ar','Argentina'),'fecha':'28 Jun','hora':'04:00'},
            {'jornada':'Jornada 3','eq1':('dz','Argelia'),'eq2':('at','Austria'),'fecha':'28 Jun','hora':'04:00'},
        ],
        'K': [
            {'jornada':'Jornada 1','eq1':('pt','Portugal'),'eq2':('cd','RD Congo'),'fecha':'17 Jun','hora':'19:00'},
            {'jornada':'Jornada 1','eq1':('uz','Uzbekistán'),'eq2':('co','Colombia'),'fecha':'18 Jun','hora':'04:00'},
            {'jornada':'Jornada 2','eq1':('pt','Portugal'),'eq2':('uz','Uzbekistán'),'fecha':'23 Jun','hora':'19:00'},
            {'jornada':'Jornada 2','eq1':('co','Colombia'),'eq2':('cd','RD Congo'),'fecha':'24 Jun','hora':'04:00'},
            {'jornada':'Jornada 3','eq1':('co','Colombia'),'eq2':('pt','Portugal'),'fecha':'28 Jun','hora':'01:30'},
            {'jornada':'Jornada 3','eq1':('cd','RD Congo'),'eq2':('uz','Uzbekistán'),'fecha':'28 Jun','hora':'01:30'},
        ],
        'L': [
            {'jornada':'Jornada 1','eq1':('gb-eng','Inglaterra'),'eq2':('hr','Croacia'),'fecha':'17 Jun','hora':'22:00'},
            {'jornada':'Jornada 1','eq1':('gh','Ghana'),'eq2':('pa','Panamá'),'fecha':'18 Jun','hora':'01:00'},
            {'jornada':'Jornada 2','eq1':('gb-eng','Inglaterra'),'eq2':('gh','Ghana'),'fecha':'23 Jun','hora':'22:00'},
            {'jornada':'Jornada 2','eq1':('pa','Panamá'),'eq2':('hr','Croacia'),'fecha':'24 Jun','hora':'01:00'},
            {'jornada':'Jornada 3','eq1':('hr','Croacia'),'eq2':('gh','Ghana'),'fecha':'27 Jun','hora':'23:00'},
            {'jornada':'Jornada 3','eq1':('pa','Panamá'),'eq2':('gb-eng','Inglaterra'),'fecha':'27 Jun','hora':'23:00'},
        ],
    }


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------
@public_bp.route("/login-bg.png")
def login_bg():
    """Serve the login background image."""
    img_path = os.path.join(os.path.dirname(__file__), "..", "static", "login_bg.png")
    img_path = os.path.abspath(img_path)
    if os.path.exists(img_path):
        return send_file(img_path, mimetype="image/png")
    return Response("", status=404)


@public_bp.route("/")
def welcome():
    if not _logged_in():
        return _render("login_register")
    return _render_ranking()


SHARED_USERNAME = "Mundial26"
SHARED_PASSWORD = "Mundial26"
ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "porra2026admin"


def _authenticated():
    return session.get("authenticated", False)

def _require_auth():
    return redirect(url_for("public.welcome"))


@public_bp.post("/entrar")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["authenticated"] = True
        session["is_admin"] = True
        return redirect(url_for("public.admin_panel"))
    if username.lower() != SHARED_USERNAME.lower() or password != SHARED_PASSWORD:
        return _render("login_register", auth_error="Usuario o contraseña incorrectos.")
    session["authenticated"] = True
    session["is_admin"] = False
    return redirect(url_for("public.welcome"))


@public_bp.post("/registro")
def register():
    return redirect(url_for("public.welcome"))


@public_bp.route("/salir")
def logout():
    session.clear()
    return redirect(url_for("public.welcome"))


@public_bp.route("/nueva-prediccion", methods=["GET", "POST"])
def nueva_prediccion():
    if not _logged_in():
        return redirect(url_for("public.welcome"))
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            return _render("nuevo_nombre", nombre_error="Introduce tu nombre.")
        session["pred_nombre"] = nombre
        return redirect(url_for("public.grupos_fase"))
    return _render("nuevo_nombre")


def _auto_sync():
    """Sync from API at most once per minute (API free tier: 10 req/min, sync uses 2)."""
    from flask import current_app
    import datetime
    api_key = current_app.config.get("FOOTBALL_DATA_API_KEY", "")
    if not api_key:
        return
    try:
        storage = get_storage()
        now_utc = datetime.datetime.utcnow()
        last_sync_str = storage.get_setting("last_sync", "")
        if last_sync_str:
            elapsed = (now_utc - datetime.datetime.fromisoformat(last_sync_str)).total_seconds()
            if elapsed < 15:
                return  # Already synced less than 15 seconds ago
        from app.services.sync import fetch_all
        data = fetch_all(api_key)
        new_results = data.get("results", {})
        if new_results:
            existing = storage.load_results()
            existing.update(new_results)
            storage.save_results(existing)
        fixtures = data.get("fixtures", [])
        if fixtures:
            storage.save_fixtures(fixtures)
        storage.set_setting("last_sync", now_utc.isoformat())
    except Exception:
        pass


def _render_ranking():
    # Load data FIRST, then sync in background so reads are never blocked by writes
    try:
        storage = get_storage()
        participants = storage.load_participants()
        results = storage.load_results()
        fixtures = storage.load_fixtures()
    except Exception:
        participants, results, fixtures = {}, {}, []
    _auto_sync()  # sync after reading so it doesn't race with our data load

    standings = build_standings(participants, results)
    try:
        all_p = get_storage().load_participants_full()
        id_map = {p["name"]: p["id"] for p in all_p}
        for row in standings:
            row["id"] = id_map.get(row["name"], "")
    except Exception:
        for row in standings:
            row["id"] = ""

    # Live matches
    live_matches = [f for f in fixtures if f.get("is_live")]

    # Next scheduled match: sort by utc_date to get the earliest one
    import datetime
    now_utc = datetime.datetime.utcnow()
    scheduled = []
    for f in fixtures:
        if f.get("status") == "SCHEDULED":
            try:
                if f.get("utc_date"):
                    dt = datetime.datetime.strptime(f["utc_date"], "%Y-%m-%dT%H:%M:%SZ")
                else:
                    fecha_hora = f.get("fecha", "") + " " + f.get("hora", "00:00") + " 2026"
                    dt = datetime.datetime.strptime(fecha_hora, "%d %b %H:%M %Y") - datetime.timedelta(hours=2)
                if dt > now_utc:
                    scheduled.append((dt, f))
            except Exception:
                pass
    scheduled.sort(key=lambda x: x[0])
    next_match = scheduled[0][1] if scheduled else None

    return _render("inicio", clasificacion=standings,
                   live_matches=live_matches, next_match=next_match)


@public_bp.route("/ranking")
def ranking():
    if not _authenticated():
        return redirect(url_for("public.welcome"))
    return _render_ranking()


_KNOCKOUT_STAGES = {"ROUND_OF_32","LAST_32","ROUND_OF_16","LAST_16","QUARTER_FINALS","SEMI_FINALS","FINAL","THIRD_PLACE"}
_KNOCKOUT_ORDER  = ["ROUND_OF_32","LAST_32","ROUND_OF_16","LAST_16","QUARTER_FINALS","SEMI_FINALS","FINAL"]
_KNOCKOUT_LABELS = {
    "ROUND_OF_32":    "Dieciseisavos de Final",
    "LAST_32":        "Dieciseisavos de Final",
    "ROUND_OF_16":    "Octavos de Final",
    "LAST_16":        "Octavos de Final",
    "QUARTER_FINALS": "Cuartos de Final",
    "SEMI_FINALS":    "Semifinales",
    "FINAL":          "Final",
    "THIRD_PLACE":    "3er y 4º Puesto",
}


@public_bp.route("/grupos")
def ver_grupos():
    if not _authenticated():
        return redirect(url_for("public.welcome"))
    try:
        storage  = get_storage()
        results  = storage.load_results()
        fixtures = storage.load_fixtures()
    except Exception:
        results, fixtures = {}, []

    # Only switch to knockout view when at least one knockout match has been played or is live
    knockout_fixtures = [f for f in fixtures if f.get("stage","") in _KNOCKOUT_STAGES]
    in_knockout = any(f.get("is_finished") or f.get("is_live") for f in knockout_fixtures)

    if in_knockout:
        # Group knockout fixtures by stage in order
        from collections import OrderedDict
        rondas = OrderedDict()
        seen_stages = set()
        for stage in _KNOCKOUT_ORDER + ["THIRD_PLACE"]:
            matches = [f for f in knockout_fixtures if f.get("stage") == stage]
            if matches and stage not in seen_stages:
                seen_stages.add(stage)
                rondas[_KNOCKOUT_LABELS[stage]] = matches
        return _render("ver_eliminatorias", rondas=rondas)

    # Group stage view
    grupos_fmt = _grupos_fmt()
    grupos_ordenados = {}
    for letra, equipos in grupos_fmt.items():
        letra_min = letra.lower()
        r1 = results.get(f"g_{letra_min}_1", "")
        r2 = results.get(f"g_{letra_min}_2", "")
        r3 = results.get(f"g_{letra_min}_3", "")
        equipos_dict = {pais: iso for iso, pais in equipos}
        ordenados = []
        if r1 in equipos_dict: ordenados.append((equipos_dict[r1], r1, "1º"))
        if r2 in equipos_dict: ordenados.append((equipos_dict[r2], r2, "2º"))
        if r3 in equipos_dict: ordenados.append((equipos_dict[r3], r3, "3º"))
        puestos = [e[1] for e in ordenados]
        for iso, pais in equipos:
            if pais not in puestos:
                ordenados.append((iso, pais, "-"))
        grupos_ordenados[letra] = ordenados
    return _render("ver_grupos", grupos_ordenados=grupos_ordenados)


@public_bp.route("/horarios")
def ver_horarios():
    if not _authenticated():
        return redirect(url_for("public.welcome"))
    # Try dynamic fixtures from DB first
    fixtures = []
    try:
        fixtures = get_storage().load_fixtures()
    except Exception:
        pass

    if fixtures:
        # Group fixtures by stage/group for display
        from collections import OrderedDict
        sections = OrderedDict()  # key → {"label": str, "partidos": [...]}

        stage_order = [
            "GROUP_STAGE", "ROUND_OF_32", "LAST_32",
            "ROUND_OF_16", "LAST_16", "QUARTER_FINALS",
            "SEMI_FINALS", "THIRD_PLACE", "FINAL",
        ]
        # Sort fixtures by date within each group
        def _sort_key(f):
            stage_idx = stage_order.index(f["stage"]) if f["stage"] in stage_order else 99
            return (stage_idx, f.get("group", ""), f.get("fecha", ""), f.get("hora", ""))

        fixtures_sorted = sorted(fixtures, key=_sort_key)

        for f in fixtures_sorted:
            stage = f["stage"]
            group = f.get("group", "")
            if stage == "GROUP_STAGE":
                sec_key = f"grupo_{group}"
                label   = f"Grupo {group}"
            else:
                sec_key = stage
                label   = f["stage_label"]
            if sec_key not in sections:
                sections[sec_key] = {"label": label, "partidos": []}
            sections[sec_key]["partidos"].append(f)

        return _render("ver_horarios_dinamico", sections=sections)

    # Fallback to hardcoded calendar
    return _render("ver_horarios", calendario=_generar_calendario())


@public_bp.route("/prediccion/ver/<participant_id>")
def ver_prediccion(participant_id):
    if not _logged_in():
        return redirect(url_for("public.welcome"))
    try:
        storage = get_storage()
        p = storage.get_participant_by_id(participant_id)
        results = storage.load_results()
    except Exception:
        return redirect(url_for("public.welcome"))
    if not p:
        return redirect(url_for("public.welcome"))
    return _render("ver_prediccion", nombre=p["name"],
                   predicciones=p.get("prediction") or {},
                   resultados=results)


@public_bp.route("/prediccion/grupos", methods=["GET", "POST"])
def grupos_fase():
    if not _logged_in():
        return redirect(url_for("public.welcome"))
    nombre = session.get("pred_nombre", "")
    if not nombre:
        return redirect(url_for("public.nueva_prediccion"))

    if request.method == "POST":
        grupos_data = request.form.to_dict()
        session["pred_grupos"] = grupos_data
        # No guardamos hasta que el usuario complete y pulse el botón final
        # Build clasificados for elimination section
        clasificados = []
        seen = set()
        for letra in "ABCDEFGHIJKL":
            for pos in ("1", "2", "3"):
                eq = grupos_data.get(f"g_{letra}_{pos}", "")
                if eq and eq not in seen:
                    clasificados.append(eq)
                    seen.add(eq)
        # Render same page: groups summary (read-only) + elimination form below
        return _render("prediccion_completa",
                       grupos=_grupos_fmt(), saved=grupos_data,
                       nombre=nombre, clasificados=clasificados)

    saved = session.get("pred_grupos", {})
    if not saved:
        try:
            p = get_storage().get_prediction_by_name(nombre)
            if p:
                saved = p.get("prediction", {}).get("grupos", {})
        except Exception:
            pass
    return _render("fase_grupos", grupos=_grupos_fmt(), saved=saved)


@public_bp.route("/prediccion/eliminatorias", methods=["GET", "POST"])
def eliminatorias_fase():
    if not _logged_in():
        return redirect(url_for("public.welcome"))
    nombre = session.get("pred_nombre", "")
    if not nombre:
        return redirect(url_for("public.nueva_prediccion"))
    if request.method == "POST":
        elim = {
            "octavos": request.form.getlist("octavos"),
            "cuartos": request.form.getlist("cuartos"),
            "semis": request.form.getlist("semis"),
            "final": request.form.getlist("final"),
            "campeon": request.form.get("campeon"),
            "subcampeon": request.form.get("subcampeon"),
            "pichichi": request.form.get("pichichi"),
        }
        try:
            storage = get_storage()
            # Los grupos vienen de la sesión (no se guardan antes)
            grupos_data = session.get("pred_grupos", {})
            pred = {"grupos": grupos_data, "eliminatorias": elim}
            storage.save_prediction_by_name(nombre, pred)
            session.pop("pred_nombre", None)
            session.pop("pred_grupos", None)
            return redirect(url_for("public.welcome"))
        except Exception as exc:
            # Show error in the form so user can retry
            grupos_data = session.get("pred_grupos", {})
            clasificados = []
            seen = set()
            for letra in "ABCDEFGHIJKL":
                for pos in ("1", "2", "3"):
                    eq = grupos_data.get(f"g_{letra}_{pos}", "")
                    if eq and eq not in seen:
                        clasificados.append(eq)
                        seen.add(eq)
            return _render("prediccion_completa",
                           grupos=_grupos_fmt(), saved=grupos_data,
                           nombre=nombre, clasificados=clasificados,
                           elim_error=f"Error al guardar: {exc}. Inténtalo de nuevo.")
    # Should not reach here normally, redirect back to grupos
    return redirect(url_for("public.grupos_fase"))


# ---------------------------------------------------------------------------
# ADMIN
# ---------------------------------------------------------------------------
@public_bp.route("/admin", methods=["GET", "POST"])
def admin_panel():
    from flask import current_app

    if not session.get("is_admin"):
        return redirect(url_for("public.welcome"))
    authed = True

    msg, ok, error = None, False, None

    if request.method == "POST":
        action = request.form.get("action")
        if False:  # placeholder to keep elif chain
            pass

        elif action == "sync_api" and authed:
            api_key = current_app.config.get("FOOTBALL_DATA_API_KEY", "")
            if not api_key:
                msg, ok = "Falta FOOTBALL_DATA_API_KEY en las variables de entorno de Vercel.", False
            else:
                try:
                    from app.services.sync import fetch_all
                    data = fetch_all(api_key)
                    storage = get_storage()
                    new_results = data.get("results", {})
                    if new_results:
                        existing = storage.load_results()
                        existing.update(new_results)
                        storage.save_results(existing)
                    fixtures = data.get("fixtures", [])
                    if fixtures:
                        storage.save_fixtures(fixtures)
                    msg, ok = f"Sincronizado: {len(new_results)} resultados, {len(fixtures)} partidos.", True
                except Exception as exc:
                    msg, ok = f"Error al sincronizar: {exc}", False

        elif action == "save_fixture" and authed:
            try:
                storage = get_storage()
                fixtures_list = storage.load_fixtures()
                idx = int(request.form.get("fixture_idx", -1))
                if 0 <= idx < len(fixtures_list):
                    home_score_raw = request.form.get("home_score", "").strip()
                    away_score_raw = request.form.get("away_score", "").strip()
                    status = request.form.get("status", "SCHEDULED").strip()
                    fixtures_list[idx]["home_score"] = int(home_score_raw) if home_score_raw != "" else None
                    fixtures_list[idx]["away_score"] = int(away_score_raw) if away_score_raw != "" else None
                    fixtures_list[idx]["status"] = status
                    fixtures_list[idx]["is_finished"] = (status == "FINISHED")
                    fixtures_list[idx]["is_live"] = (status == "IN_PLAY")
                    storage.save_fixtures(fixtures_list)
                    msg, ok = f"Partido #{idx + 1} actualizado correctamente.", True
                else:
                    msg, ok = "Índice de partido inválido.", False
            except Exception as exc:
                msg, ok = f"Error al guardar partido: {exc}", False

        elif action == "save_results" and authed:
            try:
                results = {}
                for letra in "ABCDEFGHIJKL":
                    for pos in ("1", "2", "3"):
                        val = request.form.get(f"g_{letra}_{pos}", "").strip()
                        if val:
                            results[f"g_{letra.lower()}_{pos}"] = val
                for ronda in ("octavos", "cuartos", "semis", "final"):
                    vals = request.form.getlist(ronda)
                    if vals:
                        results[ronda] = vals
                for field in ("campeon", "subcampeon"):
                    val = request.form.get(field, "").strip()
                    if val:
                        results[field] = val
                pichichi = request.form.get("pichichi", "").strip()
                if pichichi:
                    results["pichichi"] = [pichichi.lower()]
                get_storage().save_results(results)
                msg, ok = "Resultados guardados correctamente.", True
            except Exception as exc:
                msg, ok = f"Error al guardar: {exc}", False

    current_results = {}
    current_fixtures = []
    if authed:
        try:
            storage = get_storage()
            current_results = storage.load_results()
            current_fixtures = storage.load_fixtures()
        except Exception:
            pass

    grupos_fmt = _grupos_fmt()
    all_teams = sorted(set(pais for equipos in grupos_fmt.values() for _, pais in equipos))

    from flask import current_app as _app
    has_api_key = bool(_app.config.get("FOOTBALL_DATA_API_KEY", ""))

    # Render admin with Bootstrap (same style as the rest of the app)
    ADMIN_HTML = """
<!DOCTYPE html><html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin – Porra Mundial 2026</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  body{font-family:'Poppins',sans-serif;background:#f2f9f5;color:#2c3e50;padding-top:30px;}
  .card{border-radius:15px;box-shadow:0 10px 30px rgba(0,0,0,.05);border:none;background:rgba(255,255,255,.98);}
  .team-checkbox{display:none;}
  .team-label{cursor:pointer;border:2px solid #dee2e6;border-radius:8px;padding:8px;transition:all .2s;display:block;text-align:center;background:white;font-weight:600;font-size:.85rem;}
  .team-checkbox:checked+.team-label{border-color:#198754;background:#e8f5e9;color:#0f5132;}
</style>
</head><body>
<div class="container-fluid px-4 mb-5" style="max-width:1300px;">
  <div class="d-flex justify-content-between align-items-center py-3 mb-4 border-bottom border-success">
    <h2 class="fw-bold text-success m-0">⚙️ Panel de Administrador</h2>
    <a href="/" class="btn btn-outline-success fw-bold">Clasificación actual</a>
  </div>

  {% if not authed %}
  <div class="row justify-content-center"><div class="col-md-4">
    <div class="card p-4">
      <h4 class="fw-bold text-success border-bottom pb-3 mb-4 text-center">Acceso Admin</h4>
      {% if error %}<div class="alert alert-danger py-2">{{ error }}</div>{% endif %}
      <form method="POST">
        <input type="hidden" name="action" value="login">
        <div class="mb-3"><label class="form-label fw-bold text-success">Contraseña</label>
        <input type="password" name="admin_password" class="form-control border-success" required></div>
        <button type="submit" class="btn btn-success fw-bold w-100 py-2">Entrar</button>
      </form>
    </div>
  </div></div>

  {% else %}
  {% if msg %}<div class="alert {{ 'alert-success' if ok else 'alert-danger' }} fw-bold">{{ msg }}</div>{% endif %}

  <div class="card p-3 mb-4">
    <h5 class="fw-bold text-success mb-3">🔄 Sincronización Automática</h5>
    <form method="POST" class="d-flex gap-3 align-items-center flex-wrap">
      <input type="hidden" name="action" value="sync_api">
      <button type="submit" class="btn btn-primary fw-bold" {{ '' if has_api_key else 'disabled' }}>
        🔄 Sincronizar desde API del Mundial
      </button>
      {% if not has_api_key %}
      <span class="text-danger fw-bold small">⚠️ Falta configurar FOOTBALL_DATA_API_KEY en Vercel</span>
      {% else %}
      <span class="text-muted small">Actualiza automáticamente con resultados reales de football-data.org</span>
      {% endif %}
    </form>
  </div>

  <form method="POST">
    <input type="hidden" name="action" value="save_results">

    <div class="card p-3 mb-4">
      <h5 class="fw-bold text-success mb-3">🌍 Fase de Grupos</h5>
      <div class="row">
        {% for letra, equipos in grupos.items() %}
        <div class="col-md-6 col-lg-3 mb-3">
          <div class="card bg-light border-0 shadow-sm h-100">
            <div class="card-header bg-success text-white fw-bold text-center py-2">Grupo {{ letra }}</div>
            <div class="card-body p-3 d-flex flex-column gap-2">
              {% for pos, label in [('1','1º Puesto'),('2','2º Puesto'),('3','Mejor 3º')] %}
              <select name="g_{{ letra }}_{{ pos }}" class="form-select form-select-sm fw-bold">
                <option value="">{{ label }} — sin resultado</option>
                {% for iso, pais in equipos %}
                <option value="{{ pais }}" {{ 'selected' if results.get('g_' ~ letra.lower() ~ '_' ~ pos) == pais }}>
                  {{ label }} · {{ pais }}
                </option>
                {% endfor %}
              </select>
              {% endfor %}
            </div>
          </div>
        </div>
        {% endfor %}
      </div>
    </div>

    <div class="card p-3 mb-4">
      <h5 class="fw-bold text-success mb-3">⚽ Eliminatorias</h5>
      {% for ronda, label, maxsel in [('octavos','Octavos de Final',16),('cuartos','Cuartos de Final',8),('semis','Semifinales',4),('final','Final',2)] %}
      <h6 class="fw-bold text-dark mt-3 mb-2">{{ label }} ({{ maxsel }} equipos)</h6>
      <div class="row g-2 mb-3">
        {% for tname in all_teams %}
        <div class="col-6 col-md-3 col-lg-2">
          <input type="checkbox" name="{{ ronda }}" value="{{ tname }}" id="r_{{ ronda }}_{{ loop.index }}" class="team-checkbox"
                 {{ 'checked' if tname in (results.get(ronda) or []) }}>
          <label class="team-label" for="r_{{ ronda }}_{{ loop.index }}">{{ tname }}</label>
        </div>
        {% endfor %}
      </div>
      {% endfor %}

      <div class="row mt-3">
        <div class="col-md-4 mb-3">
          <label class="form-label fw-bold text-success">🏆 Campeón</label>
          <select name="campeon" class="form-select fw-bold">
            <option value="">— sin resultado —</option>
            {% for tname in all_teams %}
            <option value="{{ tname }}" {{ 'selected' if results.get('campeon') == tname }}>{{ tname }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4 mb-3">
          <label class="form-label fw-bold text-secondary">🥈 Subcampeón</label>
          <select name="subcampeon" class="form-select fw-bold">
            <option value="">— sin resultado —</option>
            {% for tname in all_teams %}
            <option value="{{ tname }}" {{ 'selected' if results.get('subcampeon') == tname }}>{{ tname }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="col-md-4 mb-3">
          <label class="form-label fw-bold text-primary">⚽ Pichichi</label>
          <input type="text" name="pichichi" class="form-control fw-bold"
                 value="{{ results.get('pichichi',[''])[0] if results.get('pichichi') else '' }}"
                 placeholder="Ej: Kylian Mbappé">
        </div>
      </div>
    </div>

    <div class="text-center mb-5">
      <button type="submit" class="btn btn-success fw-bold px-5 py-3 fs-5">💾 Guardar resultados</button>
    </div>
  </form>

  <div class="card p-3 mb-5">
    <h5 class="fw-bold text-success mb-3">⚽ Edición Manual de Partidos</h5>
    {% if fixtures %}
    <div class="table-responsive">
      <table class="table table-hover align-middle table-sm">
        <thead class="table-dark">
          <tr>
            <th>#</th>
            <th>Fecha</th>
            <th>Hora</th>
            <th>Fase / Grupo</th>
            <th class="text-end">Local</th>
            <th class="text-center">Marcador</th>
            <th>Visitante</th>
            <th>Estado</th>
            <th class="text-center">Guardar</th>
          </tr>
        </thead>
        <tbody>
          {% for f in fixtures %}
          <tr>
            <form method="POST">
              <input type="hidden" name="action" value="save_fixture">
              <input type="hidden" name="fixture_idx" value="{{ loop.index0 }}">
              <td class="text-muted small">{{ loop.index }}</td>
              <td class="small">{{ f.fecha }}</td>
              <td class="small">{{ f.hora }}</td>
              <td class="small">
                {{ f.stage_label }}
                {% if f.group %}<span class="badge bg-secondary">{{ f.group }}</span>{% endif %}
              </td>
              <td class="text-end fw-bold small">
                {% if f.home.flag %}<img src="https://flagcdn.com/w16/{{ f.home.flag }}.png" width="16" class="me-1">{% endif %}
                {{ f.home.name }}
              </td>
              <td class="text-center">
                <div class="d-flex align-items-center justify-content-center gap-1">
                  <input type="number" name="home_score" class="form-control form-control-sm text-center fw-bold"
                         style="width:55px;" min="0" max="99"
                         value="{{ f.home_score if f.home_score is not none else '' }}"
                         placeholder="-">
                  <span class="fw-bold text-muted">–</span>
                  <input type="number" name="away_score" class="form-control form-control-sm text-center fw-bold"
                         style="width:55px;" min="0" max="99"
                         value="{{ f.away_score if f.away_score is not none else '' }}"
                         placeholder="-">
                </div>
              </td>
              <td class="fw-bold small">
                {% if f.away.flag %}<img src="https://flagcdn.com/w16/{{ f.away.flag }}.png" width="16" class="me-1">{% endif %}
                {{ f.away.name }}
              </td>
              <td>
                <select name="status" class="form-select form-select-sm" style="min-width:120px;">
                  <option value="SCHEDULED" {{ 'selected' if f.status == 'SCHEDULED' }}>Pendiente</option>
                  <option value="IN_PLAY" {{ 'selected' if f.status == 'IN_PLAY' }}>En juego</option>
                  <option value="FINISHED" {{ 'selected' if f.status == 'FINISHED' }}>Finalizado</option>
                </select>
              </td>
              <td class="text-center">
                <button type="submit" class="btn btn-sm btn-outline-success fw-bold px-3">💾</button>
              </td>
            </form>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <div class="alert alert-info mb-0">No hay fixtures cargados. Usa la sincronización API para importarlos.</div>
    {% endif %}
  </div>

  {% endif %}
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body></html>
"""
    return render_template_string(
        ADMIN_HTML,
        authed=True, grupos=grupos_fmt, all_teams=all_teams,
        results=current_results, msg=msg, ok=ok, error=error,
        has_api_key=has_api_key, fixtures=current_fixtures,
    )


@public_bp.route("/sync")
def sync_results():
    from flask import current_app
    from app.services.sync import fetch_all
    secret = current_app.config.get("SYNC_SECRET", "")
    if secret and request.args.get("secret") != secret:
        return {"error": "unauthorized"}, 401
    api_key = current_app.config.get("FOOTBALL_DATA_API_KEY", "")
    if not api_key:
        return {"error": "FOOTBALL_DATA_API_KEY not configured"}, 500
    try:
        data = fetch_all(api_key)
        storage = get_storage()
        # Save results (merge with existing manual entries)
        new_results = data.get("results", {})
        if new_results:
            existing = storage.load_results()
            existing.update(new_results)
            storage.save_results(existing)
        # Save fixtures (full replace)
        fixtures = data.get("fixtures", [])
        if fixtures:
            storage.save_fixtures(fixtures)
        return {
            "status": "ok",
            "results_keys": list(new_results.keys()),
            "fixtures_count": len(fixtures),
        }
    except Exception as exc:
        return {"error": str(exc)}, 500


@public_bp.route("/health")
def health():
    return {"status": "ok"}
