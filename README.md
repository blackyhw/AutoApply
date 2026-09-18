# AutoApply

Agente de postulaciones que corre **24/7 en una VM aislada** (nunca en la notebook personal). Recolecta vacantes, las compara contra un perfil/CV, arma una postulación a partir de bloques predefinidos, la envía, y gestiona respuestas de reclutadores.

Esta etapa deja la **estructura, contratos e implementación de la capa segura**. Los conectores vivos de LinkedIn / Indeed / Computrabajo y el auto-apply con Playwright quedan como adapters listos para completar.

## Stack

| Capa | Elección | Alternativas |
| --- | --- | --- |
| Lenguaje | Python 3.12 | TypeScript (Playwright más idiomático, peor ecosistema LLM) |
| Orquestación | `asyncio` + loop propio | APScheduler, Temporal, Celery |
| Persistencia | SQLite + SQLAlchemy 2 | Postgres cuando haya más de un proceso escribiendo |
| LLM | Gemini Flash (primario) + Groq (fallback por rate limit) | OpenAI, local GGUF |
| Browser apply | Playwright (stub) | APIs oficiales del portal si existen |
| Inbox | IMAP del mail dedicado | Gmail API |
| Calendario | SQLite local ahora, Google Calendar después | CalDAV |
| Notificaciones | Telegram + email + logs | Slack |
| Aislamiento | Docker Compose en una VPS | systemd en una VM |

El paquete se llama `autoapply`. El proceso usa un **mail dedicado** (revocable) y secretos por entorno.

## Pipeline

```
collectors  →  dedupe/SQLite  →  matcher (LLM)  →  generator (bloques+plantilla)
                                                    ↓
                         notify ← apply engine (dry-run por defecto)
                                                    ↓
                         IMAP parser → calendar (conflicto / reschedule)
```

Heartbeat cada 24 h. Un proceso `watchdog` aparte alerta si la señal no llega.

## Estructura

```
config/                     # perfil, bloques de CV, plantilla de mail, defaults
data/samples/               # feed local para probar el pipeline
deploy/systemd/             # unidades para una VM
src/autoapply/
  cli.py                    # run | once | heartbeat | watchdog
  orchestrator.py           # loop 24/7
  settings.py
  domain/                   # Vacancy, MatchDecision, ApplicationPackage
  persistence/              # SQLite: vacantes, postulaciones, reuniones
  llm/                      # interfaz + Gemini + Groq + mock + router
  security/                 # UntrustedText, sanitizer, prompt guard
  collectors/               # file_feed + stubs LinkedIn/Indeed/Computrabajo
  matcher/                  # score + umbral + hard-reject
  generator/                # ensambla bloques; no reescribe experiencia
  apply/                    # motor Playwright (dry-run + adapters stub)
  inbox/                    # IMAP + parser de meets
  calendar/                 # local + scheduler de conflictos
  notify/                   # Telegram / email
  heartbeat/
  profile/
tests/
```

## Guardrails (obligatorios)

Cualquier texto de terceros (descripciones, mails, ICS) entra como `UntrustedText`. No se puede interpolar como string: hay que llamar `as_delimited_data()`, que:

1. saca caracteres invisibles / bidi
2. redacta frases típicas de prompt-injection (EN/ES)
3. lo cerca en `<<<UNTRUSTED_THIRD_PARTY_DATA>>>`

El system prompt del LLM ordena extraer JSON y **no obedecer** instrucciones que aparezcan adentro. El generador **solo combina bloques de `cv_blocks.yaml`** y rellena placeholders de una plantilla; no inventa empleos.

## Cómo correrlo (local / VM)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
cp config/profile.example.yaml config/profile.yaml
cp config/cv_blocks.example.yaml config/cv_blocks.yaml
pytest
python -m autoapply once --dry-run
```

En la VM:

```bash
docker compose up --build -d
```

`AUTOAPPLY_DRY_RUN=true` por defecto: no envía postulaciones reales.

Variables mínimas para producción:

- `GEMINI_API_KEY` (y `GROQ_API_KEY` como fallback)
- `AGENT_EMAIL_*` del buzón dedicado
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` o `ALERT_EMAIL`

## Próximas etapas

1. Completar collectors (sesión Playwright o API, en la VM).
2. Completar adapters de apply por portal.
3. Google Calendar + reprogramación automática con mail de respuesta.
4. Migraciones si se pasa de SQLite a Postgres.
