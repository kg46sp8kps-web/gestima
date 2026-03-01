# ADR-055: Server-Sent Events (SSE) — real-time push notifikace

## Status
Přijato (implementováno 2026-03-01).

## Kontext
Gestima běží na více zařízeních současně (tablety na dílně, desktop v kanceláři). Když uživatel změní tier zakázky na jednom zařízení, ostatní zařízení o změně neví — vidí stará data dokud neudělají manuální refresh. Polling (periodický dotaz) je nežádoucí kvůli zbytečné zátěži a latenci. Full-page refresh je nepřijatelný — uživatel ztrácí výběr řádku a scroll pozici.

## Rozhodnutí
Implementovat **Server-Sent Events (SSE)** jako globální infrastrukturu pro real-time push notifikace z backendu na všechny připojené klienty.

### Proč SSE a ne WebSocket
| Kritérium | SSE | WebSocket |
|-----------|-----|-----------|
| Směr komunikace | Server → klient (stačí nám) | Obousměrný (nepotřebujeme) |
| Protokol | Standardní HTTP | Vlastní upgrade |
| Autentizace | Cookie funguje automaticky | Nutný vlastní handshake |
| Reconnect | Nativní v prohlížeči | Nutný vlastní kód |
| Proxy/CDN kompatibilita | Dobrá | Problematická |
| Složitost implementace | Minimální | Vyšší |

SSE je optimální volba — potřebujeme pouze jednosměrný push z backendu.

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│  Backend (FastAPI, single worker)                           │
│                                                             │
│  event_bus.py                                               │
│  ┌──────────────────────────┐                               │
│  │ _subscribers: Set[Queue] │◄── subscribe() / unsubscribe()│
│  │                          │                               │
│  │ broadcast(type, data)    │──► put_nowait() do všech Queue│
│  └──────────────────────────┘                               │
│           ▲                                                 │
│           │ broadcast("tier_change", {job, suffix, tier})    │
│           │                                                 │
│  production_planner_service.set_tier()                      │
│  (rozšiřitelné o další služby)                              │
│                                                             │
│  GET /api/events/stream ──► StreamingResponse (text/event-stream)
└────────────────────┬────────────────────────────────────────┘
                     │ SSE
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   Tablet A      Desktop B    Tablet C
   EventSource   EventSource  EventSource
   onmessage()   onmessage()  onmessage()
        │            │            │
   tierByVp      tierByVp     tierByVp
   (reactive)    (reactive)   (reactive)
```

## Implementace

### Backend

**`app/services/event_bus.py`** — In-process pub/sub:
```python
_subscribers: Set[asyncio.Queue] = set()

def subscribe() -> asyncio.Queue      # Nový klient
def unsubscribe(q: asyncio.Queue)     # Klient odpojen
def broadcast(type: str, data: dict)  # Push všem
```

**`app/routers/events_router.py`** — SSE endpoint:
- `GET /api/events/stream` — vyžaduje autentizaci (cookie)
- Keepalive komentář každých 30s (prevence timeout proxy/browser)
- Formát: `data: {"type": "tier_change", "job": "26VP02/036", "suffix": "0", "tier": "hot"}\n\n`

**Broadcast z business logiky:**
```python
# production_planner_service.py — po úspěšném uložení tier
from app.services.event_bus import broadcast
broadcast("tier_change", {"job": safe_job, "suffix": safe_suffix, "tier": tier})
```

### Frontend

**`frontend/src/composables/useSse.ts`** — Singleton EventSource:
```typescript
// Komponenta se přihlásí k eventu:
onSseEvent('tier_change', (msg) => {
  tierByVp.value[msg.job] = msg.tier
})
```

Vlastnosti:
- **Singleton** — jedna SSE konekce sdílená všemi komponentami
- **Auto-reconnect** po 3s při výpadku
- **Auto-cleanup** — `onUnmounted()` odhlásí listener, při 0 listenerech zavře spojení
- **Lazy connect** — spojení se otevře až když první komponenta zavolá `onSseEvent()`

## Event typy

| Typ | Payload | Producent | Konzument |
|-----|---------|-----------|-----------|
| `tier_change` | `{job, suffix, tier}` | `set_tier()` | TileOrdersOverview |

Tabulka se rozšiřuje s každým novým event typem. Stačí zavolat `broadcast()` v backendu a `onSseEvent()` ve frontendu.

## Rozšiřitelnost

Přidání nového event typu vyžaduje 2 řádky kódu:

**Backend** (v libovolné službě):
```python
from app.services.event_bus import broadcast
broadcast("order_status_change", {"co_num": "...", "status": "shipped"})
```

**Frontend** (v libovolné komponentě):
```typescript
onSseEvent('order_status_change', (msg) => { /* reagovat */ })
```

## Omezení

- **Single-worker only** — `event_bus.py` je in-process. Při škálování na více workerů nutno nahradit Redis pub/sub nebo podobným brokerem.
- **Bez persistence** — klient připojený po události ji neuvidí. Pro tier to nevadí — initial stav se načte z API odpovědi (`tier` pole v orders overview datech).
- **Bez filtru** — klient dostává všechny event typy. Při velkém objemu eventů lze přidat query param `?types=tier_change,order_update`.

## Důsledky
- Tier změny se propagují v reálném čase (< 100ms) bez jakéhokoli pollingu
- Uživatel neztratí výběr ani scroll pozici — aktualizuje se jen reaktivní ref
- Infrastruktura je připravená pro budoucí real-time funkce (stav operací, notifikace, chat)
