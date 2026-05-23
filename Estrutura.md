ai_data_framework/
│
├── pyproject.toml          ← Configurações centralizadas (ruff, mypy, pytest, coverage)
├── README.md
├── .env.example            ← Template de variáveis de ambiente (copiar para .env)
├── .gitignore
├── uv.lock
├── Agents.md
├── Arquiteture_guidelines.md
├── Metodologia.md
├── SPEC.md
├── LOG.md
├── sample_sales.csv
├── test_pkg_import.py
│
├── src/
│   └── ai_data_framework/
│       │
│       ├── core/
│       ├── ingestion/
│       ├── profiling/
│       ├── hypothesis/
│       ├── validation/
│       ├── visualization/
│       ├── llm/
│       ├── pipeline/
│       ├── cli/
│       ├── audit/           ← Log de auditoria (rastreabilidade)
│       └── privacy/         ← Modulo de privacidade
│
├── web/                     ← Dashboard web (FastAPI)
├── tests/
└── orientacoes/             ← Regras de governanca, validacao e visualizacao