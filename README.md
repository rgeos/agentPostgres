```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "How many total items do we have across all products?"}'; \
     echo ""
```

```bash
curl -X GET "http://localhost:8000/health" \
     -H "Content-Type: application/json" 
```

```sql
create schema isolated_analytics_schema;

comment on schema isolated_analytics_schema is 'read only for LLM';

alter schema isolated_analytics_schema owner to llm_reader;

grant connect on database rag_database to llm_reader;
grant usage on schema isolated_analytics_schema to llm_reader;
grant select on all tables in schema isolated_analytics_schema to llm_reader;
alter default privileges in schema isolated_analytics_schema grant select on tables to llm_reader;

```