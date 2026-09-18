# AutoApply

Agente de postulaciones que corre **24/7 en una VM aislada** (nunca en la notebook personal). Recolecta vacantes, las compara contra un perfil/CV, arma una postulación a partir de bloques predefinidos, genera un PDF, la envía, y gestiona respuestas de reclutadores.

## Qué hace hoy

- Recolecta vacantes de **LinkedIn** (guest job search), **Computrabajo** y **Indeed** (si el portal no bloquea la IP de la VM). El feed local sigue disponible para pruebas.
- Deduplica contra SQLite para no postular dos veces al mismo puesto.
- Matchea con Gemini Flash (Groq si hay rate limit; mock si no hay API keys).
- Arma el CV **solo con bloques predefinidos** y un mail de plantilla, y exporta **PDF**.
- Aplica en dry-run por defecto. En vivo: mail de postulación si la vacante trae email, o Playwright si hay sesión guardada (`python -m autoapply login <portal>`).
- Parsea el IMAP del mail dedicado, agenda reuniones (SQLite + Google Calendar si hay credenciales) y puede reprogramar.
- Heartbeat cada 24 h y watchdog si se cae.

## Stack

| Capa | Elección |
| --- | --- |
| Lenguaje | Python 3.12 + asyncio |
| Persistencia | SQLite + SQLAlchemy 2 |
| LLM | Gemini Flash → Groq |
| Apply | SMTP del mail dedicado + Playwright |
| Collectors | HTTP público (LinkedIn guest, Computrabajo); Indeed cuando no hay 403 |
| Calendario | SQLite local, Google Calendar opcional |
| Avisos | Telegram + email + logs |
| Aislamiento | Docker Compose / systemd en una VPS |

## Cómo correrlo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
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
docker compose up --build -d
```

`AUTOAPPLY_DRY_RUN=true` por defecto. No envía postulaciones reales hasta que lo apagues y existan SMTP y/o sesiones Playwright.

## Guardrails

Cualquier texto de terceros entra como `UntrustedText`. El generador no inventa experiencia: solo combina `cv_blocks.yaml`. Los collectors no intentan bypassear captchas ni bloqueos 403/429: fallan y siguen con el resto.

## Qué falta para producción personal

1. Completar `config/profile.yaml` y `config/cv_blocks.yaml` con tus datos reales.
2. Mail dedicado + `GEMINI_API_KEY` + Telegram.
3. Sesión Playwright de cada portal en la VM (`autoapply login`).
4. Apagar dry-run cuando el dry-run se vea bien.
5. Opcional: JSON de service account de Google Calendar en `secrets/`.
