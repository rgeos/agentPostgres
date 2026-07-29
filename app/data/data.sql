-- DROP DATABASE IF EXISTS rag_database;
-- CREATE database rag_database;

drop schema if exists isolated_analytics_schema CASCADE;
create schema isolated_analytics_schema;

comment on schema isolated_analytics_schema is 'read only for LLM';

alter schema isolated_analytics_schema owner to llm_reader;

grant connect on database rag_database to llm_reader;
grant usage on schema isolated_analytics_schema to llm_reader;
grant select on all tables in schema isolated_analytics_schema to llm_reader;
alter default privileges in schema isolated_analytics_schema grant select on tables to llm_reader;

-- create some data
create table isolated_analytics_schema.products (
    id serial primary key ,
    name varchar(256),
    price int,
    stock int
);

insert into isolated_analytics_schema.products (name, price, stock)
values
('apples', 10, 100),
('oranges', 15, 200),
('apples', 20, 300),
('oranges', 25, 100),
('grapes', 10, 200);
