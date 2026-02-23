# ADR-046: Infor Connector + Part↔TimeVision FK [PARTIAL — Part↔TV done, Infor kroky 1-2/4 hotové]
> Archive: docs/ADR/archive/046-infor-connector.md — Claude může požádat o přečtení

## Rozhodnutí
TimeVisionEstimation má přímý `part_id` FK. Infor Connector importuje Parts+Operations z IDO API (kroky 1-2 hotové, VP routing + ProductionRecords pending).

## Pattern
- `app/models/time_vision.py` — `part_id` FK (DONE)
- `app/services/infor_part_importer.py` — SLItems → Parts (DONE)
- `app/services/infor_job_routing_importer.py` — SLJobRoutes → Operations (DONE)
- `app/services/infor_api_client.py` — HTTP client pro IDO API
- `app/services/infor_wc_mapper.py` — WC code → Gestima WorkCenter id

## Nesmíš
- používat filename-based matching pro TimeVision (nahrazeno part_id FK)
- duplikovat WC mapping mimo InforWcMapper
