# AutoApply

Agente de postulaciones que corre **24/7 en una VM aislada** (nunca en la notebook personal). Recolecta vacantes, las compara contra un perfil/CV, arma una postulación a partir de bloques predefinidos, genera un PDF, la envía, y gestiona respuestas de reclutadores.

## Tokens: scraping sin IA

Recolectar y filtrar vacantes **no llama a ningún LLM**. El matcher es overlap de keywords/tags del perfil. Eso evita gastar tokens en cada aviso scrapeado.

La IA entra **solo después** de que una vacante ya pasó el filtro, y en una sola llamada:

- elegir qué bloques de `cv_blocks.yaml` incluir (sin reescribir experiencia)
- completar los campos de la plantilla de mail / cover letter

Si Gemini/Groq fallan, se usa el armado heurístico. El inbox de reuniones también es heurístico (ICS / link de Meet), no LLM.

Sin API keys, el provider mock no consume nada.

## Qué hace hoy

- Recolecta vacantes de **LinkedIn** (guest job search), **Computrabajo** (HTML público) e **Indeed**. Indeed suele devolver 403/429 por HTTP desde una VPS: el collector pasa a Chromium (Playwright) y parsea las cards `data-jk`. Si aparece captcha o login wall, corta; no hay bypass.
- Deduplica contra SQLite para no postular dos veces al mismo puesto.
- Matchea por keywords. Gemini Flash (o Groq) solo reformula el paquete de postulación de los matches.
- Arma el CV **solo con bloques predefinidos** y un mail de plantilla, y exporta **PDF**.
- Aplica en dry-run por defecto. En vivo: mail de postulación si la vacante trae email, o Playwright si hay sesión guardada (`python -m autoapply login <portal>`).
- Parsea el IMAP del mail dedicado, agenda reuniones (SQLite + Google Calendar si hay credenciales) y puede reprogramar.
- Heartbeat cada 24 h y watchdog si se cae.

## Stack

| Capa | Elección |
| --- | --- |
| Lenguaje | Python 3.12 + asyncio |
| Persistencia | SQLite + SQLAlchemy 2 |
| LLM | Gemini Flash → Groq, **solo compose** (CV + mail) |
| Matcher | keywords, sin LLM |
| Apply | SMTP del mail dedicado + Playwright |
| Collectors | HTTP público (LinkedIn guest, Computrabajo); Indeed HTTP o Chromium |
| Calendario | SQLite local, Google Calendar opcional |
| Avisos | Telegram + email + logs |
| Aislamiento | Docker Compose / systemd en una VPS |

## Cómo correrlo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cp .env.example .env
cp config/profile.example.yaml config/profile.yaml
cp config/cv_blocks.example.yaml config/cv_blocks.yaml
pytest
python -m autoapply export-cv
python -m autoapply once --dry-run
```

En la VM, con secretos en `.env`:

```bash
python -m autoapply login linkedin
python -m autoapply login computrabajo
python -m autoapply login indeed
docker compose up --build -d
```

`AUTOAPPLY_DRY_RUN=true` por defecto. No envía postulaciones reales hasta que lo apagues y existan SMTP y/o sesiones Playwright.

## Guardrails

Cualquier texto de terceros entra como `UntrustedText`. El generador no inventa experiencia: solo combina `cv_blocks.yaml`. Los collectors no intentan bypassear captchas ni bloqueos 403/429: Indeed reintenta con un browser real; si el portal sigue pidiendo captcha, falla y siguen los otros collectors.

## Qué falta para producción personal

1. Completar `config/profile.yaml` y `config/cv_blocks.yaml` con tus datos reales.
2. Mail dedicado + `GEMINI_API_KEY` + Telegram.
3. Sesión Playwright de cada portal en la VM (`autoapply login`).
4. Apagar dry-run cuando el dry-run se vea bien.
5. Opcional: JSON de service account de Google Calendar en `secrets/`.
