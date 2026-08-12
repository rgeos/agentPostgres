DROP SCHEMA IF EXISTS isolated_analytics_schema CASCADE; 
CREATE SCHEMA isolated_analytics_schema;

-- create role
CREATE ROLE llm_reader;
ALTER ROLE llm_reader LOGIN;
ALTER SCHEMA isolated_analytics_schema OWNER TO llm_reader;
COMMENT ON SCHEMA isolated_analytics_schema IS 'read only for LLM';



SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: orders; Type: TABLE; Schema: isolated_analytics_schema; Owner: postgres
--

CREATE TABLE isolated_analytics_schema.orders (
    id integer NOT NULL,
    product_id integer,
    volume_order integer,
    customer character varying(256)
);


ALTER TABLE isolated_analytics_schema.orders OWNER TO postgres;

--
-- Name: orders_id_seq; Type: SEQUENCE; Schema: isolated_analytics_schema; Owner: postgres
--

CREATE SEQUENCE isolated_analytics_schema.orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE isolated_analytics_schema.orders_id_seq OWNER TO postgres;

--
-- Name: orders_id_seq; Type: SEQUENCE OWNED BY; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER SEQUENCE isolated_analytics_schema.orders_id_seq OWNED BY isolated_analytics_schema.orders.id;


--
-- Name: products; Type: TABLE; Schema: isolated_analytics_schema; Owner: postgres
--

CREATE TABLE isolated_analytics_schema.products (
    id integer NOT NULL,
    name character varying(256),
    price integer,
    stock integer
);


ALTER TABLE isolated_analytics_schema.products OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: isolated_analytics_schema; Owner: postgres
--

CREATE SEQUENCE isolated_analytics_schema.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE isolated_analytics_schema.products_id_seq OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER SEQUENCE isolated_analytics_schema.products_id_seq OWNED BY isolated_analytics_schema.products.id;


--
-- Name: transactions; Type: TABLE; Schema: isolated_analytics_schema; Owner: postgres
--

CREATE TABLE isolated_analytics_schema.transactions (
    id integer NOT NULL,
    information jsonb DEFAULT '{}'::jsonb,
    created_on timestamp without time zone
);


ALTER TABLE isolated_analytics_schema.transactions OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: isolated_analytics_schema; Owner: postgres
--

CREATE SEQUENCE isolated_analytics_schema.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE isolated_analytics_schema.transactions_id_seq OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER SEQUENCE isolated_analytics_schema.transactions_id_seq OWNED BY isolated_analytics_schema.transactions.id;


--
-- Name: orders id; Type: DEFAULT; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER TABLE ONLY isolated_analytics_schema.orders ALTER COLUMN id SET DEFAULT nextval('isolated_analytics_schema.orders_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER TABLE ONLY isolated_analytics_schema.products ALTER COLUMN id SET DEFAULT nextval('isolated_analytics_schema.products_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER TABLE ONLY isolated_analytics_schema.transactions ALTER COLUMN id SET DEFAULT nextval('isolated_analytics_schema.transactions_id_seq'::regclass);


--
-- Data for Name: orders; Type: TABLE DATA; Schema: isolated_analytics_schema; Owner: postgres
--

INSERT INTO isolated_analytics_schema.orders VALUES (1, 1, 50, 'Mr. Brown');
INSERT INTO isolated_analytics_schema.orders VALUES (2, 1, 20, 'Mr. White');
INSERT INTO isolated_analytics_schema.orders VALUES (3, 2, 150, 'Mr. Yellow');
INSERT INTO isolated_analytics_schema.orders VALUES (4, 4, 100, 'Ms. Alice');
INSERT INTO isolated_analytics_schema.orders VALUES (5, 5, 150, 'Ms. Claire');
INSERT INTO isolated_analytics_schema.orders VALUES (6, 5, 100, 'Ms. Grapes');


--
-- Data for Name: products; Type: TABLE DATA; Schema: isolated_analytics_schema; Owner: postgres
--

INSERT INTO isolated_analytics_schema.products VALUES (1, 'apples', 10, 100);
INSERT INTO isolated_analytics_schema.products VALUES (2, 'oranges', 15, 200);
INSERT INTO isolated_analytics_schema.products VALUES (3, 'apples', 20, 300);
INSERT INTO isolated_analytics_schema.products VALUES (4, 'oranges', 25, 100);
INSERT INTO isolated_analytics_schema.products VALUES (5, 'grapes', 10, 200);


--
-- Data for Name: transactions; Type: TABLE DATA; Schema: isolated_analytics_schema; Owner: postgres
--

INSERT INTO isolated_analytics_schema.transactions VALUES (4, '{"items": [], "amount": 0, "status": "DELIVERED", "orderId": 75037807, "customerName": "sit Excepteur sint elit", "shippingAddress": {"city": "Tokyo", "street": "sint in eu magna culpa", "zipcode": "non aute ea Lorem anim"}}', '2026-08-09 04:31:28');
INSERT INTO isolated_analytics_schema.transactions VALUES (5, '{"items": [{"price": 3668.76, "quantity": 243, "product_id": 1, "productName": "est cupidatat do incididunt eu"}, {"price": 7348.77, "quantity": 195, "product_id": 2, "productName": "labore anim in qui"}, {"price": 4644.74, "quantity": 838, "product_id": 4, "productName": "ut"}, {"price": 8683.32, "quantity": 740, "product_id": 6, "productName": "cillum non Excepteur mollit velit"}, {"price": 2959.85, "quantity": 938, "product_id": 7, "productName": "ipsum nostrud irure esse sunt"}], "amount": 5, "status": "SHIPPED", "orderId": 17211803, "customerName": "aliquip quis", "shippingAddress": {"city": "Zurich", "street": "ipsum reprehenderit in enim consectetur", "zipcode": "cupidatat cillum"}}', '2026-08-05 04:31:36');
INSERT INTO isolated_analytics_schema.transactions VALUES (1, '{"items": [{"price": 7176.75, "quantity": 806, "product_id": 1, "productName": "est laborum consectetur adipisicing tempor"}, {"price": 1547.51, "quantity": 647, "product_id": 2, "productName": "nulla deserunt do culpa veniam"}], "amount": 2, "status": "SHIPPED", "orderId": 39449732, "customerName": "non fugiat eiusmod laborum", "shippingAddress": {"city": "Tokyo", "street": "do ipsum eiusmod", "zipcode": "anim"}}', '2026-08-11 04:31:16');
INSERT INTO isolated_analytics_schema.transactions VALUES (3, '{"items": [{"price": 7517.23, "quantity": 909, "product_id": 1, "productName": "sint minim Ut sit"}, {"price": 9418.12, "quantity": 849, "product_id": 3, "productName": "eiusmod eu"}, {"price": 8244.13, "quantity": 640, "product_id": 4, "productName": "id in ullamco fugiat do"}, {"price": 2598.03, "quantity": 276, "product_id": 5, "productName": "occaecat"}, {"price": 8547.47, "quantity": 230, "product_id": 6, "productName": "officia dolore anim in dolore"}], "amount": 5, "status": "PENDING", "orderId": 48987381, "customerName": "ullamco", "shippingAddress": {"city": "Tokyo", "street": "Ut tempor in", "zipcode": "Excepteur est"}}', '2026-08-10 04:31:22');
INSERT INTO isolated_analytics_schema.transactions VALUES (2, '{"items": [{"price": 7176.75, "quantity": 806, "product_id": 1, "productName": "est laborum consectetur adipisicing tempor"}, {"price": 1547.51, "quantity": 647, "product_id": 3, "productName": "nulla deserunt do culpa veniam"}], "amount": 2, "status": "SHIPPED", "orderId": 39449732, "customerName": "non fugiat eiusmod laborum", "shippingAddress": {"city": "Basel", "street": "do ipsum eiusmod", "zipcode": "anim"}}', '2026-08-11 04:31:20');


--
-- Name: orders_id_seq; Type: SEQUENCE SET; Schema: isolated_analytics_schema; Owner: postgres
--

SELECT pg_catalog.setval('isolated_analytics_schema.orders_id_seq', 6, true);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: isolated_analytics_schema; Owner: postgres
--

SELECT pg_catalog.setval('isolated_analytics_schema.products_id_seq', 5, true);


--
-- Name: transactions_id_seq; Type: SEQUENCE SET; Schema: isolated_analytics_schema; Owner: postgres
--

SELECT pg_catalog.setval('isolated_analytics_schema.transactions_id_seq', 5, true);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER TABLE ONLY isolated_analytics_schema.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER TABLE ONLY isolated_analytics_schema.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pk; Type: CONSTRAINT; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER TABLE ONLY isolated_analytics_schema.transactions
    ADD CONSTRAINT transactions_pk PRIMARY KEY (id);


--
-- Name: idx_transactions_info_gin; Type: INDEX; Schema: isolated_analytics_schema; Owner: postgres
--

CREATE INDEX idx_transactions_info_gin ON isolated_analytics_schema.transactions USING gin (information);


--
-- Name: DATABASE rag_database; Type: ACL; Schema: -; Owner: postgres
--

GRANT CONNECT ON DATABASE rag_database TO llm_reader;


--
-- Name: TABLE orders; Type: ACL; Schema: isolated_analytics_schema; Owner: postgres
--

GRANT SELECT ON TABLE isolated_analytics_schema.orders TO llm_reader;


--
-- Name: TABLE products; Type: ACL; Schema: isolated_analytics_schema; Owner: postgres
--

GRANT SELECT ON TABLE isolated_analytics_schema.products TO llm_reader;


--
-- Name: TABLE transactions; Type: ACL; Schema: isolated_analytics_schema; Owner: postgres
--

GRANT SELECT ON TABLE isolated_analytics_schema.transactions TO llm_reader;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: isolated_analytics_schema; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA isolated_analytics_schema GRANT SELECT ON TABLES TO llm_reader;

GRANT CONNECT ON DATABASE rag_database TO llm_reader;
GRANT USAGE ON SCHEMA isolated_analytics_schema TO llm_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA isolated_analytics_schema TO llm_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA isolated_analytics_schema GRANT SELECT ON TABLES TO llm_reader;

--
-- PostgreSQL database dump complete
--
