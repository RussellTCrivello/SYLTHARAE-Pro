--
-- PostgreSQL database dump
--

\restrict t8eWpW1pfHeOGwLZ1QcfznnSc9OjvVOr59Q5WqFFWwolVrBlbT7LydFuTGjRKyn

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: report_artifacts_immutable(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.report_artifacts_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- The one accepted change: the creator's account was deleted
        -- (ON DELETE SET NULL). Everything else about an artifact is final.
        IF NEW.created_by IS NULL AND OLD.created_by IS NOT NULL
           AND (to_jsonb(NEW) - 'created_by') = (to_jsonb(OLD) - 'created_by') THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'report artifact % is immutable', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END;
    $$;


ALTER FUNCTION public.report_artifacts_immutable() OWNER TO postgres;

--
-- Name: report_run_analyses_write_once(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.report_run_analyses_write_once() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE EXCEPTION 'report run analyses are written once and never updated'
            USING ERRCODE = 'integrity_constraint_violation';
    END;
    $$;


ALTER FUNCTION public.report_run_analyses_write_once() OWNER TO postgres;

--
-- Name: report_run_datasets_write_once(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.report_run_datasets_write_once() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RAISE EXCEPTION 'report run results are written once and never updated'
            USING ERRCODE = 'integrity_constraint_violation';
    END;
    $$;


ALTER FUNCTION public.report_run_datasets_write_once() OWNER TO postgres;

--
-- Name: report_runs_terminal_immutable(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.report_runs_terminal_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- The one change a terminal run accepts: a referenced account or
        -- saved search was deleted (ON DELETE SET NULL). Each of the two
        -- references is unchanged or cleared; every other column unchanged.
        IF (NEW.requested_by IS NOT DISTINCT FROM OLD.requested_by OR NEW.requested_by IS NULL)
           AND (NEW.saved_search_id IS NOT DISTINCT FROM OLD.saved_search_id
                OR NEW.saved_search_id IS NULL)
           AND (to_jsonb(NEW) - 'requested_by' - 'saved_search_id')
               = (to_jsonb(OLD) - 'requested_by' - 'saved_search_id')
           AND to_jsonb(NEW) <> to_jsonb(OLD) THEN
            RETURN NEW;
        END IF;
        IF OLD.status IN ('completed', 'failed', 'refused', 'cancelled') THEN
            RAISE EXCEPTION 'report run % is % and cannot be changed', OLD.id, OLD.status
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END;
    $$;


ALTER FUNCTION public.report_runs_terminal_immutable() OWNER TO postgres;

--
-- Name: scenario_outcomes_append_only(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.scenario_outcomes_append_only() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
    BEGIN
        -- A cascade from a parent that is gone (the owner deleted, the
        -- content deleted by deduplication) removes the history with its
        -- subject; any other UPDATE or DELETE is refused.
        IF TG_OP = 'DELETE' AND (
                NOT EXISTS (SELECT 1 FROM scenarios WHERE id = OLD.scenario_id)
                OR NOT EXISTS (SELECT 1 FROM scenario_evaluations WHERE id = OLD.evaluation_id)
                OR NOT EXISTS (SELECT 1 FROM hashs WHERE id = OLD.hash_id)) THEN
            RETURN OLD;
        END IF;
        RAISE EXCEPTION 'scenario_outcomes is append-only (% refused)', TG_OP
            USING ERRCODE = 'integrity_constraint_violation';
    END
    $$;


ALTER FUNCTION public.scenario_outcomes_append_only() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alerts (
    id integer NOT NULL,
    type character varying(50) NOT NULL,
    priority character varying(20) NOT NULL,
    title character varying(500) NOT NULL,
    message text NOT NULL,
    file_id integer,
    file_name character varying(500),
    file_path text,
    event_date date,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    read boolean DEFAULT false,
    dismissed boolean DEFAULT false,
    recipient_user_id integer,
    rule_id integer,
    rule_evaluation_id bigint,
    scenario_id integer,
    scenario_evaluation_id bigint,
    CONSTRAINT ck_alerts_rule_addressed CHECK (((rule_id IS NULL) OR (recipient_user_id IS NOT NULL))),
    CONSTRAINT ck_alerts_scenario_addressed CHECK (((scenario_id IS NULL) OR (recipient_user_id IS NOT NULL)))
);


ALTER TABLE public.alerts OWNER TO postgres;

--
-- Name: alerts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.alerts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.alerts_id_seq OWNER TO postgres;

--
-- Name: alerts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.alerts_id_seq OWNED BY public.alerts.id;


--
-- Name: analyst_categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analyst_categories (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    color character varying(7),
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.analyst_categories OWNER TO postgres;

--
-- Name: analyst_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.analyst_categories ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.analyst_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: analyst_categorization_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analyst_categorization_log (
    id bigint NOT NULL,
    analyst_id integer,
    analyst_username character varying(64),
    action character varying(32) NOT NULL,
    category_id integer,
    category_name character varying(255),
    source_query text,
    path_ids jsonb NOT NULL,
    path_count integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.analyst_categorization_log OWNER TO postgres;

--
-- Name: analyst_categorization_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.analyst_categorization_log ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.analyst_categorization_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: analyst_file_categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analyst_file_categories (
    id integer NOT NULL,
    path_id integer NOT NULL,
    category_id integer NOT NULL,
    assigned_by integer,
    assigned_by_username character varying(64),
    source_query text,
    assigned_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.analyst_file_categories OWNER TO postgres;

--
-- Name: analyst_file_categories_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.analyst_file_categories ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.analyst_file_categories_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_log (
    id bigint NOT NULL,
    user_id integer,
    username character varying(64),
    action character varying(255) NOT NULL,
    resource character varying(255),
    detail jsonb,
    ip_address character varying(64),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_log OWNER TO postgres;

--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.audit_log ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.audit_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: categorys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.categorys (
    id integer NOT NULL,
    word_id integer NOT NULL
);


ALTER TABLE public.categorys OWNER TO postgres;

--
-- Name: categorys_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.categorys ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.categorys_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: content_signal_places; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.content_signal_places (
    signal_id bigint NOT NULL,
    place_id integer NOT NULL
);


ALTER TABLE public.content_signal_places OWNER TO postgres;

--
-- Name: content_signal_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.content_signal_runs (
    hash_id integer NOT NULL,
    detector character varying(40) NOT NULL,
    detector_ver character varying(40) NOT NULL,
    status character varying(16) NOT NULL,
    anchor_date date,
    chars_total bigint,
    chars_scanned bigint,
    signal_count integer DEFAULT 0 NOT NULL,
    trigger character varying(24) NOT NULL,
    job_id text,
    error text,
    ran_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_signal_runs_chars CHECK (((chars_scanned IS NULL) OR (chars_total IS NULL) OR (chars_scanned <= chars_total))),
    CONSTRAINT ck_signal_runs_count CHECK ((signal_count >= 0)),
    CONSTRAINT ck_signal_runs_error CHECK ((((status)::text = 'failed'::text) = (error IS NOT NULL))),
    CONSTRAINT ck_signal_runs_status CHECK (((status)::text = ANY ((ARRAY['complete'::character varying, 'truncated'::character varying, 'no_text'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT ck_signal_runs_trigger CHECK (((trigger)::text = ANY ((ARRAY['ingestion'::character varying, 'redetection'::character varying])::text[]))),
    CONSTRAINT ck_signal_runs_truncated CHECK ((((status)::text <> 'truncated'::text) OR (chars_scanned < chars_total)))
);


ALTER TABLE public.content_signal_runs OWNER TO postgres;

--
-- Name: content_signals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.content_signals (
    id bigint NOT NULL,
    hash_id integer NOT NULL,
    detector character varying(40) NOT NULL,
    detector_ver character varying(40) NOT NULL,
    signal_type character varying(40) NOT NULL,
    value text NOT NULL,
    surface text NOT NULL,
    char_start integer NOT NULL,
    char_end integer NOT NULL,
    language character varying(8),
    calendar character varying(16),
    resolution character varying(24) NOT NULL,
    date_from date,
    date_to date,
    text_orientation character varying(8),
    anchor_date date,
    evidence jsonb NOT NULL,
    dedup_key character(64) NOT NULL,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    method character varying(64),
    confidence character varying(8),
    confidence_basis character varying(40),
    evidence_sentence text,
    sentence_start integer,
    sentence_end integer,
    CONSTRAINT ck_content_signals_calendar CHECK (((calendar IS NULL) OR ((calendar)::text = ANY ((ARRAY['gregorian'::character varying, 'hijri'::character varying, 'jalali'::character varying])::text[])))),
    CONSTRAINT ck_content_signals_confidence CHECK (((confidence IS NULL) OR ((confidence)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying])::text[])))),
    CONSTRAINT ck_content_signals_dedup_hex CHECK ((dedup_key ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_content_signals_identified_place CHECK ((((resolution)::text <> 'identified'::text) OR ((signal_type)::text = 'place_mention'::text))),
    CONSTRAINT ck_content_signals_offsets CHECK (((char_start >= 0) AND (char_end > char_start))),
    CONSTRAINT ck_content_signals_orientation CHECK (((text_orientation IS NULL) OR ((text_orientation)::text = ANY ((ARRAY['future'::character varying, 'present'::character varying, 'past'::character varying])::text[])))),
    CONSTRAINT ck_content_signals_provenance_complete CHECK ((((method IS NULL) = (confidence IS NULL)) AND ((confidence IS NULL) = (confidence_basis IS NULL)) AND ((confidence IS NULL) = (evidence_sentence IS NULL)) AND ((evidence_sentence IS NULL) = (sentence_start IS NULL)) AND ((sentence_start IS NULL) = (sentence_end IS NULL)))),
    CONSTRAINT ck_content_signals_range_order CHECK (((date_from IS NULL) OR (date_from <= date_to))),
    CONSTRAINT ck_content_signals_range_pair CHECK (((date_from IS NULL) = (date_to IS NULL))),
    CONSTRAINT ck_content_signals_relative_anchor CHECK ((((resolution)::text <> 'document_relative'::text) OR (anchor_date IS NOT NULL))),
    CONSTRAINT ck_content_signals_resolution CHECK (((resolution)::text = ANY ((ARRAY['absolute'::character varying, 'approximate'::character varying, 'document_relative'::character varying, 'ambiguous'::character varying, 'unresolved'::character varying, 'identified'::character varying])::text[]))),
    CONSTRAINT ck_content_signals_resolved_has_range CHECK ((((resolution)::text = ANY ((ARRAY['absolute'::character varying, 'approximate'::character varying, 'document_relative'::character varying])::text[])) = (date_from IS NOT NULL))),
    CONSTRAINT ck_content_signals_sentence_contains CHECK (((sentence_start IS NULL) OR ((sentence_start <= char_start) AND (char_end <= sentence_end) AND (length(evidence_sentence) = (sentence_end - sentence_start))))),
    CONSTRAINT ck_content_signals_type CHECK (((signal_type)::text ~ '^[a-z][a-z_]{2,39}$'::text)),
    CONSTRAINT ck_content_signals_value CHECK ((length(value) > 0))
);


ALTER TABLE public.content_signals OWNER TO postgres;

--
-- Name: content_signals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.content_signals ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.content_signals_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: contents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contents (
    id integer NOT NULL,
    content_data bytea,
    content_date date,
    hash_id integer NOT NULL
);


ALTER TABLE public.contents OWNER TO postgres;

--
-- Name: contents_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.contents ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.contents_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: contents_raw; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contents_raw (
    id bigint NOT NULL,
    chunk_seq integer NOT NULL,
    content text NOT NULL,
    char_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    hash_id integer NOT NULL
);


ALTER TABLE public.contents_raw OWNER TO postgres;

--
-- Name: contents_raw_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.contents_raw ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.contents_raw_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: geo_gazetteer_loads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.geo_gazetteer_loads (
    id integer NOT NULL,
    seed_version character varying(40) NOT NULL,
    content_sha256 character(64) NOT NULL,
    fingerprint character(64) NOT NULL,
    place_count integer NOT NULL,
    name_count integer NOT NULL,
    stats jsonb DEFAULT '{}'::jsonb NOT NULL,
    loaded_by character varying(80) NOT NULL,
    loaded_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_geo_loads_counts CHECK (((place_count >= 0) AND (name_count >= 0))),
    CONSTRAINT ck_geo_loads_fp CHECK ((fingerprint ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_geo_loads_sha CHECK ((content_sha256 ~ '^[0-9a-f]{64}$'::text))
);


ALTER TABLE public.geo_gazetteer_loads OWNER TO postgres;

--
-- Name: geo_gazetteer_loads_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.geo_gazetteer_loads ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.geo_gazetteer_loads_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: geo_place_names; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.geo_place_names (
    id integer NOT NULL,
    place_id integer NOT NULL,
    name character varying(255) NOT NULL,
    match_key character varying(255) NOT NULL,
    language character varying(8) NOT NULL,
    script character(4) NOT NULL,
    name_type character varying(16) NOT NULL,
    homograph boolean DEFAULT false NOT NULL,
    source character varying(40) NOT NULL,
    note text,
    CONSTRAINT ck_geo_place_names_key CHECK ((length((match_key)::text) > 0)),
    CONSTRAINT ck_geo_place_names_language CHECK (((language)::text = ANY ((ARRAY['en'::character varying, 'ar'::character varying, 'he'::character varying, 'fa'::character varying, 'hr'::character varying])::text[]))),
    CONSTRAINT ck_geo_place_names_name CHECK ((length(btrim((name)::text)) > 0)),
    CONSTRAINT ck_geo_place_names_script CHECK (((((language)::text = ANY ((ARRAY['en'::character varying, 'hr'::character varying])::text[])) AND (script = 'Latn'::bpchar)) OR (((language)::text = ANY ((ARRAY['ar'::character varying, 'fa'::character varying])::text[])) AND (script = 'Arab'::bpchar)) OR (((language)::text = 'he'::text) AND (script = 'Hebr'::bpchar)))),
    CONSTRAINT ck_geo_place_names_type CHECK (((name_type)::text = ANY ((ARRAY['endonym'::character varying, 'exonym'::character varying, 'historical'::character varying, 'variant'::character varying, 'unclassified'::character varying])::text[])))
);


ALTER TABLE public.geo_place_names OWNER TO postgres;

--
-- Name: geo_place_names_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.geo_place_names ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.geo_place_names_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: geo_places; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.geo_places (
    id integer NOT NULL,
    place_key character varying(64) NOT NULL,
    label character varying(255) NOT NULL,
    feature_type character varying(16) NOT NULL,
    country_codes character(2)[] DEFAULT '{}'::bpchar[] NOT NULL,
    latitude double precision,
    longitude double precision,
    source character varying(40) NOT NULL,
    source_title character varying(255),
    seed_version character varying(40),
    retired boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_geo_places_countries CHECK ((array_to_string(country_codes, ','::text) ~ '^([A-Z]{2}(,[A-Z]{2})*)?$'::text)),
    CONSTRAINT ck_geo_places_feature CHECK (((feature_type)::text = ANY ((ARRAY['city'::character varying, 'country'::character varying, 'region'::character varying])::text[]))),
    CONSTRAINT ck_geo_places_key CHECK (((place_key)::text ~ '^[a-z][a-z0-9_]*:[A-Za-z0-9_.-]+$'::text)),
    CONSTRAINT ck_geo_places_label CHECK ((length(btrim((label)::text)) > 0)),
    CONSTRAINT ck_geo_places_lat CHECK (((latitude IS NULL) OR ((latitude >= ('-90'::integer)::double precision) AND (latitude <= (90)::double precision)))),
    CONSTRAINT ck_geo_places_lon CHECK (((longitude IS NULL) OR ((longitude >= ('-180'::integer)::double precision) AND (longitude <= (180)::double precision)))),
    CONSTRAINT ck_geo_places_point_pair CHECK (((latitude IS NULL) = (longitude IS NULL)))
);


ALTER TABLE public.geo_places OWNER TO postgres;

--
-- Name: geo_places_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.geo_places ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.geo_places_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: hash_contexts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hash_contexts (
    id integer NOT NULL,
    hash_id integer NOT NULL,
    source_id integer NOT NULL,
    side_id integer NOT NULL,
    date_creation date DEFAULT CURRENT_DATE NOT NULL
);


ALTER TABLE public.hash_contexts OWNER TO postgres;

--
-- Name: hash_contexts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.hash_contexts ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.hash_contexts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: hashs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hashs (
    id integer NOT NULL,
    hash character(64) NOT NULL
);


ALTER TABLE public.hashs OWNER TO postgres;

--
-- Name: hashs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.hashs ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.hashs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: job_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.job_events (
    event_id bigint NOT NULL,
    job_id text NOT NULL,
    event_type text NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.job_events OWNER TO postgres;

--
-- Name: job_events_event_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.job_events_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.job_events_event_id_seq OWNER TO postgres;

--
-- Name: job_events_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.job_events_event_id_seq OWNED BY public.job_events.event_id;


--
-- Name: job_schedules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.job_schedules (
    id integer NOT NULL,
    schedule_type character varying(32) NOT NULL,
    name character varying(200) NOT NULL,
    owner_user_id integer NOT NULL,
    payload jsonb DEFAULT '{}'::jsonb NOT NULL,
    interval_minutes integer NOT NULL,
    enabled boolean DEFAULT true NOT NULL,
    disabled_reason character varying(64),
    next_run_at timestamp with time zone DEFAULT now() NOT NULL,
    last_run_at timestamp with time zone,
    last_job_id text,
    last_status character varying(32),
    consecutive_failures integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_job_schedules_failures CHECK ((consecutive_failures >= 0)),
    CONSTRAINT ck_job_schedules_interval CHECK (((interval_minutes >= 5) AND (interval_minutes <= 525600))),
    CONSTRAINT ck_job_schedules_name CHECK ((length(btrim((name)::text)) > 0)),
    CONSTRAINT ck_job_schedules_type CHECK (((schedule_type)::text = ANY ((ARRAY['report_run'::character varying, 'rule_evaluation'::character varying, 'scenario_evaluation'::character varying, 'retention'::character varying])::text[])))
);


ALTER TABLE public.job_schedules OWNER TO postgres;

--
-- Name: job_schedules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.job_schedules ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.job_schedules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jobs (
    job_id text NOT NULL,
    job_type text NOT NULL,
    status text DEFAULT 'QUEUED'::text NOT NULL,
    progress integer DEFAULT 0 NOT NULL,
    current_phase text,
    current_item text,
    source text,
    options jsonb DEFAULT '{}'::jsonb,
    stats jsonb DEFAULT '{}'::jsonb,
    errors jsonb DEFAULT '[]'::jsonb,
    warnings jsonb DEFAULT '[]'::jsonb,
    result_summary jsonb,
    created_by text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    cancellation_requested boolean DEFAULT false NOT NULL,
    pause_requested boolean DEFAULT false NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.jobs OWNER TO postgres;

--
-- Name: keywords; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.keywords (
    id integer NOT NULL,
    keyword bytea NOT NULL,
    category_id integer NOT NULL
);


ALTER TABLE public.keywords OWNER TO postgres;

--
-- Name: keywords_hashs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.keywords_hashs (
    keyword_id integer CONSTRAINT keywords_paths_keyword_id_not_null NOT NULL,
    word_count integer,
    hash_id integer NOT NULL
);


ALTER TABLE public.keywords_hashs OWNER TO postgres;

--
-- Name: keywords_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.keywords ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.keywords_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: monitoring_rule_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.monitoring_rule_versions (
    rule_id integer NOT NULL,
    version integer NOT NULL,
    definition jsonb NOT NULL,
    definition_fingerprint character(64) NOT NULL,
    created_by_user_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_rule_versions_fingerprint CHECK ((definition_fingerprint ~ '^[0-9a-f]{64}$'::text))
);


ALTER TABLE public.monitoring_rule_versions OWNER TO postgres;

--
-- Name: monitoring_rules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.monitoring_rules (
    id integer NOT NULL,
    owner_user_id integer NOT NULL,
    name character varying(200) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    definition jsonb NOT NULL,
    definition_fingerprint character(64) NOT NULL,
    saved_search_id integer,
    status character varying(16) DEFAULT 'active'::character varying NOT NULL,
    disabled_reason character varying(64),
    suppressed_until timestamp with time zone,
    baselined_version integer DEFAULT 0 NOT NULL,
    last_evaluated_at timestamp with time zone,
    last_notified_at timestamp with time zone,
    last_digest_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_monitoring_rules_baselined CHECK (((baselined_version >= 0) AND (baselined_version <= version))),
    CONSTRAINT ck_monitoring_rules_disabled_reason CHECK ((((status)::text = 'disabled'::text) = (disabled_reason IS NOT NULL))),
    CONSTRAINT ck_monitoring_rules_fingerprint CHECK ((definition_fingerprint ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_monitoring_rules_name CHECK ((length(btrim((name)::text)) > 0)),
    CONSTRAINT ck_monitoring_rules_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'paused'::character varying, 'disabled'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT ck_monitoring_rules_version CHECK ((version >= 1))
);


ALTER TABLE public.monitoring_rules OWNER TO postgres;

--
-- Name: monitoring_rules_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.monitoring_rules ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.monitoring_rules_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: path_geo_mentions; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.path_geo_mentions AS
SELECT
    NULL::integer AS hash_id,
    NULL::character varying(255) AS place_name,
    NULL::character varying(255) AS country,
    NULL::double precision AS latitude,
    NULL::double precision AS longitude,
    NULL::integer AS mention_count,
    NULL::character varying(64) AS place_key,
    NULL::character varying(16) AS provenance;


ALTER VIEW public.path_geo_mentions OWNER TO postgres;

--
-- Name: path_geo_mentions_m0015; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.path_geo_mentions_m0015 (
    id integer CONSTRAINT path_geo_mentions_id_not_null NOT NULL,
    hash_id integer CONSTRAINT path_geo_mentions_hash_id_not_null NOT NULL,
    place_name character varying(255) CONSTRAINT path_geo_mentions_place_name_not_null NOT NULL,
    country character varying(255),
    latitude double precision CONSTRAINT path_geo_mentions_latitude_not_null NOT NULL,
    longitude double precision CONSTRAINT path_geo_mentions_longitude_not_null NOT NULL,
    mention_count integer DEFAULT 1 CONSTRAINT path_geo_mentions_mention_count_not_null NOT NULL,
    created_at timestamp with time zone DEFAULT now() CONSTRAINT path_geo_mentions_created_at_not_null NOT NULL
);


ALTER TABLE public.path_geo_mentions_m0015 OWNER TO postgres;

--
-- Name: path_geo_mentions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.path_geo_mentions_m0015 ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.path_geo_mentions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: path_revisions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.path_revisions (
    id bigint NOT NULL,
    path_id integer NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    changed_by integer,
    change_kind character varying(16) NOT NULL,
    old_values jsonb NOT NULL,
    new_values jsonb NOT NULL,
    CONSTRAINT path_revisions_change_kind_check CHECK (((change_kind)::text = ANY ((ARRAY['modified'::character varying, 'removed'::character varying])::text[])))
);


ALTER TABLE public.path_revisions OWNER TO postgres;

--
-- Name: path_revisions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.path_revisions ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.path_revisions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: paths; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paths (
    id integer NOT NULL,
    file_name text NOT NULL,
    file_path text NOT NULL,
    file_size bigint NOT NULL,
    file_type character varying(100) NOT NULL,
    file_status character varying(10) DEFAULT 'Unread'::character varying NOT NULL,
    file_date date NOT NULL,
    date_creation date NOT NULL,
    coordinates text,
    error_message text,
    extraction_provenance jsonb,
    parent_path_id integer,
    hierarchy_path text,
    processing_status character varying(24) DEFAULT 'discovered'::character varying NOT NULL,
    status_detail text,
    attempts integer DEFAULT 0 NOT NULL,
    status_updated_at timestamp with time zone,
    context_id integer NOT NULL,
    CONSTRAINT paths_file_size_check CHECK ((file_size >= 0)),
    CONSTRAINT paths_file_status_check CHECK (((file_status)::text = ANY ((ARRAY['Read'::character varying, 'Unread'::character varying])::text[]))),
    CONSTRAINT paths_processing_status_check CHECK (((processing_status)::text = ANY ((ARRAY['discovered'::character varying, 'queued'::character varying, 'processing'::character varying, 'processed'::character varying, 'partially_processed'::character varying, 'failed'::character varying, 'unsupported'::character varying, 'skipped'::character varying, 'retrying'::character varying])::text[])))
);


ALTER TABLE public.paths OWNER TO postgres;

--
-- Name: COLUMN paths.extraction_provenance; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.paths.extraction_provenance IS 'Per-extractor provenance: {extractor: {engine, version, confidence, derived, method, input_variant, extracted_at}}. NULL means ingested before provenance was captured.';


--
-- Name: paths_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.paths ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.paths_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: punctuation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.punctuation (
    id integer NOT NULL,
    punctuation_text text NOT NULL
);


ALTER TABLE public.punctuation OWNER TO postgres;

--
-- Name: punctuation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.punctuation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.punctuation_id_seq OWNER TO postgres;

--
-- Name: punctuation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.punctuation_id_seq OWNED BY public.punctuation.id;


--
-- Name: report_artifacts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.report_artifacts (
    id bigint NOT NULL,
    run_id bigint NOT NULL,
    format character varying(16) NOT NULL,
    dataset_key character varying(120),
    renderer_version character varying(40) NOT NULL,
    filename character varying(200) NOT NULL,
    media_type character varying(120) NOT NULL,
    byte_size bigint NOT NULL,
    sha256 character(64) NOT NULL,
    content bytea NOT NULL,
    manifest jsonb NOT NULL,
    manifest_sha256 character(64) NOT NULL,
    created_by integer,
    creator_username character varying(64) NOT NULL,
    creator_role character varying(16) NOT NULL,
    job_id character varying(32),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    language character varying(8) DEFAULT 'en'::character varying NOT NULL,
    CONSTRAINT ck_report_artifacts_digest CHECK (((sha256)::text = encode(sha256(content), 'hex'::text))),
    CONSTRAINT ck_report_artifacts_filename CHECK ((((filename)::text ~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$'::text) AND ((filename)::text !~ '\.\.'::text))),
    CONSTRAINT ck_report_artifacts_format CHECK (((format)::text ~ '^[a-z0-9]{2,16}$'::text)),
    CONSTRAINT ck_report_artifacts_language CHECK (((language)::text ~ '^[a-z]{2}(-[A-Za-z0-9]+)?$'::text)),
    CONSTRAINT ck_report_artifacts_manifest CHECK (((jsonb_typeof(manifest) = 'object'::text) AND (manifest_sha256 ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT ck_report_artifacts_size CHECK ((byte_size = octet_length(content)))
);


ALTER TABLE public.report_artifacts OWNER TO postgres;

--
-- Name: report_artifacts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.report_artifacts ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.report_artifacts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: report_baselines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.report_baselines (
    user_id integer NOT NULL,
    criteria_hash character(64) NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    last_max_id bigint NOT NULL,
    CONSTRAINT ck_report_baselines_hash_hex CHECK ((criteria_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT report_baselines_last_max_id_check CHECK ((last_max_id >= 0))
);


ALTER TABLE public.report_baselines OWNER TO postgres;

--
-- Name: report_run_analyses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.report_run_analyses (
    run_id bigint NOT NULL,
    "position" smallint NOT NULL,
    analysis_key character varying(120) NOT NULL,
    analysis_fingerprint character(64) NOT NULL,
    kind character varying(40) NOT NULL,
    state character varying(16) NOT NULL,
    reason character varying(64),
    inputs jsonb NOT NULL,
    measures jsonb NOT NULL,
    rows jsonb NOT NULL,
    narrative jsonb NOT NULL,
    template_set character varying(60) NOT NULL,
    template_version integer NOT NULL,
    CONSTRAINT ck_report_run_analyses_fingerprint CHECK ((analysis_fingerprint ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_report_run_analyses_json CHECK (((jsonb_typeof(inputs) = 'object'::text) AND (jsonb_typeof(measures) = 'object'::text) AND (jsonb_typeof(rows) = 'array'::text) AND (jsonb_typeof(narrative) = 'object'::text))),
    CONSTRAINT ck_report_run_analyses_reason CHECK ((((state)::text = 'not_measurable'::text) = (reason IS NOT NULL))),
    CONSTRAINT ck_report_run_analyses_state CHECK (((state)::text = ANY ((ARRAY['measured'::character varying, 'not_measurable'::character varying])::text[]))),
    CONSTRAINT ck_report_run_analyses_template CHECK ((template_version >= 1)),
    CONSTRAINT ck_report_run_analyses_voices CHECK (((jsonb_typeof((narrative -> 'voices'::text)) = 'array'::text) AND (jsonb_array_length((narrative -> 'voices'::text)) = 5)))
);


ALTER TABLE public.report_run_analyses OWNER TO postgres;

--
-- Name: report_run_datasets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.report_run_datasets (
    run_id bigint NOT NULL,
    "position" smallint NOT NULL,
    dataset_key character varying(120) NOT NULL,
    dataset_fingerprint character(64) NOT NULL,
    query_fingerprint character(64) NOT NULL,
    semantics character varying(8) NOT NULL,
    row_limit integer NOT NULL,
    row_count integer NOT NULL,
    truncated boolean NOT NULL,
    columns jsonb NOT NULL,
    rows jsonb NOT NULL,
    baseline jsonb,
    CONSTRAINT ck_report_run_datasets_counts CHECK (((row_limit >= 1) AND (row_count >= 0) AND (row_count <= row_limit))),
    CONSTRAINT ck_report_run_datasets_exact CHECK ((NOT (((semantics)::text = 'exact'::text) AND truncated))),
    CONSTRAINT ck_report_run_datasets_fingerprints CHECK (((dataset_fingerprint ~ '^[0-9a-f]{64}$'::text) AND (query_fingerprint ~ '^[0-9a-f]{64}$'::text))),
    CONSTRAINT ck_report_run_datasets_rows CHECK (((jsonb_typeof(rows) = 'array'::text) AND (jsonb_array_length(rows) = row_count))),
    CONSTRAINT ck_report_run_datasets_semantics CHECK (((semantics)::text = ANY ((ARRAY['exact'::character varying, 'capped'::character varying, 'top_n'::character varying])::text[])))
);


ALTER TABLE public.report_run_datasets OWNER TO postgres;

--
-- Name: report_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.report_runs (
    id bigint NOT NULL,
    report_id character varying(100) NOT NULL,
    report_version integer NOT NULL,
    definition_fingerprint character(64) NOT NULL,
    parameters jsonb NOT NULL,
    parameters_fingerprint character(64) NOT NULL,
    criteria_fingerprint character(64),
    saved_search_id integer,
    requested_by integer,
    requester_username character varying(64) NOT NULL,
    requester_role character varying(16) NOT NULL,
    job_id character varying(32),
    status character varying(16) DEFAULT 'queued'::character varying NOT NULL,
    refusal_reason character varying(64),
    error text,
    snapshot text,
    snapshot_at timestamp with time zone,
    isolation_level character varying(40),
    generator_version character varying(40) NOT NULL,
    requested_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    finished_at timestamp with time zone,
    CONSTRAINT ck_report_runs_completed CHECK ((((status)::text <> 'completed'::text) OR ((snapshot IS NOT NULL) AND (snapshot_at IS NOT NULL) AND (started_at IS NOT NULL) AND (finished_at IS NOT NULL)))),
    CONSTRAINT ck_report_runs_failed CHECK ((((status)::text <> 'failed'::text) OR (error IS NOT NULL))),
    CONSTRAINT ck_report_runs_fingerprints CHECK (((definition_fingerprint ~ '^[0-9a-f]{64}$'::text) AND (parameters_fingerprint ~ '^[0-9a-f]{64}$'::text) AND ((criteria_fingerprint IS NULL) OR (criteria_fingerprint ~ '^[0-9a-f]{64}$'::text)))),
    CONSTRAINT ck_report_runs_refused CHECK ((((status)::text = 'refused'::text) = (refusal_reason IS NOT NULL))),
    CONSTRAINT ck_report_runs_status CHECK (((status)::text = ANY ((ARRAY['queued'::character varying, 'running'::character varying, 'completed'::character varying, 'failed'::character varying, 'refused'::character varying, 'cancelled'::character varying])::text[]))),
    CONSTRAINT ck_report_runs_version CHECK ((report_version >= 1))
);


ALTER TABLE public.report_runs OWNER TO postgres;

--
-- Name: report_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.report_runs ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.report_runs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: rule_evaluations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rule_evaluations (
    id bigint NOT NULL,
    rule_id integer NOT NULL,
    rule_version integer NOT NULL,
    trigger character varying(16) NOT NULL,
    job_id text,
    status character varying(16) NOT NULL,
    owner_role character varying(20),
    access_scope jsonb,
    criteria_fingerprint character(64),
    definition_fingerprint character(64) NOT NULL,
    reference_date date NOT NULL,
    evaluated_at timestamp with time zone NOT NULL,
    counts jsonb DEFAULT '{}'::jsonb NOT NULL,
    error text,
    started_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT ck_rule_evaluations_error CHECK ((((status)::text = 'failed'::text) = (error IS NOT NULL))),
    CONSTRAINT ck_rule_evaluations_status CHECK (((status)::text = ANY ((ARRAY['completed'::character varying, 'failed'::character varying, 'owner_revoked'::character varying, 'skipped_busy'::character varying, 'not_active'::character varying])::text[]))),
    CONSTRAINT ck_rule_evaluations_trigger CHECK (((trigger)::text = ANY ((ARRAY['manual'::character varying, 'ingestion'::character varying, 'redetection'::character varying, 'all_rules'::character varying, 'schedule'::character varying])::text[])))
);


ALTER TABLE public.rule_evaluations OWNER TO postgres;

--
-- Name: rule_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.rule_evaluations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.rule_evaluations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: rule_subject_ledger; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rule_subject_ledger (
    rule_id integer NOT NULL,
    subject_key character varying(200) NOT NULL,
    hash_id integer NOT NULL,
    signal_id bigint,
    rule_version integer NOT NULL,
    state character varying(16) NOT NULL,
    group_key character varying(200) NOT NULL,
    confidence character varying(8),
    event_date_from date,
    event_date_to date,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    first_matched_at timestamp with time zone NOT NULL,
    matched_evaluation_id bigint NOT NULL,
    state_changed_at timestamp with time zone NOT NULL,
    notified_evaluation_id bigint,
    alert_id integer,
    CONSTRAINT ck_rule_ledger_confidence CHECK (((confidence IS NULL) OR ((confidence)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying])::text[])))),
    CONSTRAINT ck_rule_ledger_notified CHECK ((((state)::text = 'notified'::text) = (notified_evaluation_id IS NOT NULL))),
    CONSTRAINT ck_rule_ledger_state CHECK (((state)::text = ANY ((ARRAY['baseline'::character varying, 'pending'::character varying, 'notified'::character varying, 'suppressed'::character varying, 'expired'::character varying])::text[])))
);


ALTER TABLE public.rule_subject_ledger OWNER TO postgres;

--
-- Name: saved_search_imports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.saved_search_imports (
    id integer NOT NULL,
    source_file text NOT NULL,
    file_sha256 character(64) NOT NULL,
    entries_found integer NOT NULL,
    entries_imported integer NOT NULL,
    entries_already_present integer NOT NULL,
    failures jsonb DEFAULT '[]'::jsonb NOT NULL,
    imported_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT saved_search_imports_entries_already_present_check CHECK ((entries_already_present >= 0)),
    CONSTRAINT saved_search_imports_entries_found_check CHECK ((entries_found >= 0)),
    CONSTRAINT saved_search_imports_entries_imported_check CHECK ((entries_imported >= 0))
);


ALTER TABLE public.saved_search_imports OWNER TO postgres;

--
-- Name: saved_search_imports_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.saved_search_imports ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.saved_search_imports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: saved_searches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.saved_searches (
    id integer NOT NULL,
    owner_user_id integer,
    name character varying(255) NOT NULL,
    query text DEFAULT ''::text NOT NULL,
    filters jsonb DEFAULT '{}'::jsonb NOT NULL,
    criteria jsonb NOT NULL,
    criteria_fingerprint character(64) NOT NULL,
    criteria_schema_version integer NOT NULL,
    monitor_enabled boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used_at timestamp with time zone,
    legacy_source character varying(64),
    legacy_id integer,
    import_notes jsonb,
    CONSTRAINT ck_saved_searches_fingerprint_hex CHECK ((criteria_fingerprint ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_saved_searches_legacy_pair CHECK (((legacy_source IS NULL) = (legacy_id IS NULL))),
    CONSTRAINT ck_saved_searches_name_nonempty CHECK ((length(btrim((name)::text)) > 0))
);


ALTER TABLE public.saved_searches OWNER TO postgres;

--
-- Name: saved_searches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.saved_searches ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.saved_searches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: scenario_evaluations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scenario_evaluations (
    id bigint NOT NULL,
    scenario_id integer NOT NULL,
    scenario_version integer NOT NULL,
    kind character varying(16) NOT NULL,
    trigger character varying(16) NOT NULL,
    job_id text,
    requested_by_user_id integer,
    status character varying(16) NOT NULL,
    owner_role character varying(20),
    access_scope jsonb,
    criteria_fingerprint character(64),
    definition_fingerprint character(64) NOT NULL,
    reference_date date NOT NULL,
    evaluated_at timestamp with time zone NOT NULL,
    counts jsonb DEFAULT '{}'::jsonb NOT NULL,
    report jsonb,
    error text,
    started_at timestamp with time zone DEFAULT clock_timestamp() NOT NULL,
    finished_at timestamp with time zone,
    CONSTRAINT ck_scenario_evaluations_error CHECK ((((status)::text = 'failed'::text) = (error IS NOT NULL))),
    CONSTRAINT ck_scenario_evaluations_kind CHECK (((kind)::text = ANY ((ARRAY['evaluation'::character varying, 'dry_run'::character varying])::text[]))),
    CONSTRAINT ck_scenario_evaluations_kind_status CHECK (((((kind)::text = 'dry_run'::text) AND ((status)::text = ANY ((ARRAY['passed'::character varying, 'invalid'::character varying, 'failed'::character varying, 'owner_revoked'::character varying])::text[]))) OR (((kind)::text = 'evaluation'::text) AND ((status)::text = ANY ((ARRAY['completed'::character varying, 'failed'::character varying, 'owner_revoked'::character varying, 'skipped_busy'::character varying, 'not_active'::character varying])::text[]))))),
    CONSTRAINT ck_scenario_evaluations_report CHECK ((((kind)::text = 'evaluation'::text) OR ((status)::text = ANY ((ARRAY['failed'::character varying, 'owner_revoked'::character varying])::text[])) OR (report IS NOT NULL))),
    CONSTRAINT ck_scenario_evaluations_status CHECK (((status)::text = ANY ((ARRAY['completed'::character varying, 'passed'::character varying, 'invalid'::character varying, 'failed'::character varying, 'owner_revoked'::character varying, 'skipped_busy'::character varying, 'not_active'::character varying])::text[]))),
    CONSTRAINT ck_scenario_evaluations_trigger CHECK (((trigger)::text = ANY ((ARRAY['manual'::character varying, 'ingestion'::character varying, 'redetection'::character varying, 'all_scenarios'::character varying, 'schedule'::character varying])::text[])))
);


ALTER TABLE public.scenario_evaluations OWNER TO postgres;

--
-- Name: scenario_evaluations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.scenario_evaluations ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.scenario_evaluations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: scenario_outcomes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scenario_outcomes (
    id bigint NOT NULL,
    scenario_id integer NOT NULL,
    evaluation_id bigint NOT NULL,
    scenario_version integer NOT NULL,
    hash_id integer NOT NULL,
    outcomes text[] NOT NULL,
    matched_cases text[] NOT NULL,
    previous_outcomes text[],
    delivery character varying(16) NOT NULL,
    priority character varying(8),
    priority_basis jsonb,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_scenario_outcomes_delivery CHECK (((delivery)::text = ANY ((ARRAY['baseline'::character varying, 'recorded'::character varying, 'notified'::character varying, 'overflow'::character varying])::text[]))),
    CONSTRAINT ck_scenario_outcomes_nonempty CHECK ((cardinality(outcomes) >= 1)),
    CONSTRAINT ck_scenario_outcomes_notified_priority CHECK ((((delivery)::text <> ALL ((ARRAY['notified'::character varying, 'overflow'::character varying])::text[])) OR (priority IS NOT NULL))),
    CONSTRAINT ck_scenario_outcomes_priority CHECK (((priority IS NULL) OR ((priority)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying, 'low'::character varying])::text[]))))
);


ALTER TABLE public.scenario_outcomes OWNER TO postgres;

--
-- Name: scenario_outcomes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.scenario_outcomes ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.scenario_outcomes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: scenario_versions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scenario_versions (
    scenario_id integer NOT NULL,
    version integer NOT NULL,
    definition jsonb NOT NULL,
    definition_fingerprint character(64) NOT NULL,
    created_by_user_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_scenario_versions_fingerprint CHECK ((definition_fingerprint ~ '^[0-9a-f]{64}$'::text))
);


ALTER TABLE public.scenario_versions OWNER TO postgres;

--
-- Name: scenarios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scenarios (
    id integer NOT NULL,
    owner_user_id integer NOT NULL,
    name character varying(200) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    definition jsonb NOT NULL,
    definition_fingerprint character(64) NOT NULL,
    status character varying(16) DEFAULT 'draft'::character varying NOT NULL,
    disabled_reason character varying(64),
    activated_dry_run_id bigint,
    activated_at timestamp with time zone,
    baselined_version integer DEFAULT 0 NOT NULL,
    last_evaluated_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_scenarios_active_dry_run CHECK ((((status)::text <> 'active'::text) OR (activated_dry_run_id IS NOT NULL))),
    CONSTRAINT ck_scenarios_baselined CHECK (((baselined_version >= 0) AND (baselined_version <= version))),
    CONSTRAINT ck_scenarios_disabled_reason CHECK ((((status)::text = 'disabled'::text) = (disabled_reason IS NOT NULL))),
    CONSTRAINT ck_scenarios_fingerprint CHECK ((definition_fingerprint ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT ck_scenarios_name CHECK ((length(btrim((name)::text)) > 0)),
    CONSTRAINT ck_scenarios_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'active'::character varying, 'paused'::character varying, 'disabled'::character varying, 'archived'::character varying])::text[]))),
    CONSTRAINT ck_scenarios_version CHECK ((version >= 1))
);


ALTER TABLE public.scenarios OWNER TO postgres;

--
-- Name: scenarios_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.scenarios ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.scenarios_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.schema_migrations (
    version character varying(64) NOT NULL,
    name character varying(255) NOT NULL,
    applied_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.schema_migrations OWNER TO postgres;

--
-- Name: sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sessions (
    session_id character(64) NOT NULL,
    user_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    ip_address character varying(64),
    user_agent character varying(255)
);


ALTER TABLE public.sessions OWNER TO postgres;

--
-- Name: sides; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sides (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    importance numeric(5,4) NOT NULL,
    date_creation date NOT NULL
);


ALTER TABLE public.sides OWNER TO postgres;

--
-- Name: sides_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.sides ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.sides_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sources; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sources (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    job character varying(255) NOT NULL,
    importance numeric(5,4) NOT NULL,
    country character varying(255) NOT NULL,
    city character varying(255),
    description character varying(255),
    accounts character varying(255),
    note character varying(255),
    attachments character varying(255),
    ownership character varying(255),
    access_status character varying(255),
    entry_date timestamp without time zone,
    category_id integer,
    date_creation date NOT NULL
);


ALTER TABLE public.sources OWNER TO postgres;

--
-- Name: sources_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.sources ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.sources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: titles_content; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.titles_content (
    id integer NOT NULL,
    title_data bytea,
    title_status character varying(10) DEFAULT 'Main'::character varying NOT NULL,
    title_content_id integer,
    hash_id integer NOT NULL,
    CONSTRAINT titles_content_title_status_check CHECK (((title_status)::text = ANY ((ARRAY['Main'::character varying, 'Branch'::character varying])::text[])))
);


ALTER TABLE public.titles_content OWNER TO postgres;

--
-- Name: titles_content_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.titles_content ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.titles_content_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: translation_overrides; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.translation_overrides (
    locale character varying(16) NOT NULL,
    message_key character(64) NOT NULL,
    msgid text NOT NULL,
    translation text NOT NULL,
    updated_by integer,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT translation_overrides_translation_check CHECK ((length(translation) > 0))
);


ALTER TABLE public.translation_overrides OWNER TO postgres;

--
-- Name: user_navigation_prefs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_navigation_prefs (
    user_id integer NOT NULL,
    interface_id character varying(64) NOT NULL,
    hidden boolean DEFAULT false NOT NULL,
    "position" integer,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_user_navigation_prefs_position CHECK ((("position" IS NULL) OR ("position" >= 1)))
);


ALTER TABLE public.user_navigation_prefs OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(64) NOT NULL,
    password_hash character varying(512) NOT NULL,
    role character varying(20) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    must_change_password boolean DEFAULT false NOT NULL,
    failed_login_count integer DEFAULT 0 NOT NULL,
    locked_until timestamp with time zone,
    last_login_at timestamp with time zone,
    password_changed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'analyst'::character varying, 'viewer'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.users ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: words; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.words (
    id integer NOT NULL,
    word text NOT NULL
);


ALTER TABLE public.words OWNER TO postgres;

--
-- Name: words_categorys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.words_categorys (
    word_id integer NOT NULL,
    category_id integer NOT NULL
);


ALTER TABLE public.words_categorys OWNER TO postgres;

--
-- Name: words_hashs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.words_hashs (
    word_id integer CONSTRAINT words_paths_word_id_not_null NOT NULL,
    word_count integer,
    position_indexer bytea CONSTRAINT words_paths_position_indexer_not_null NOT NULL,
    hash_id integer NOT NULL
);


ALTER TABLE public.words_hashs OWNER TO postgres;

--
-- Name: words_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public.words ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.words_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: alerts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts ALTER COLUMN id SET DEFAULT nextval('public.alerts_id_seq'::regclass);


--
-- Name: job_events event_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_events ALTER COLUMN event_id SET DEFAULT nextval('public.job_events_event_id_seq'::regclass);


--
-- Name: punctuation id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.punctuation ALTER COLUMN id SET DEFAULT nextval('public.punctuation_id_seq'::regclass);


--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


--
-- Name: analyst_categories analyst_categories_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyst_categories
    ADD CONSTRAINT analyst_categories_name_key UNIQUE (name);


--
-- Name: analyst_categories analyst_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyst_categories
    ADD CONSTRAINT analyst_categories_pkey PRIMARY KEY (id);


--
-- Name: analyst_categorization_log analyst_categorization_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyst_categorization_log
    ADD CONSTRAINT analyst_categorization_log_pkey PRIMARY KEY (id);


--
-- Name: analyst_file_categories analyst_file_categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyst_file_categories
    ADD CONSTRAINT analyst_file_categories_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: categorys categorys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categorys
    ADD CONSTRAINT categorys_pkey PRIMARY KEY (id);


--
-- Name: categorys categorys_word_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categorys
    ADD CONSTRAINT categorys_word_id_key UNIQUE (word_id);


--
-- Name: content_signal_places content_signal_places_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signal_places
    ADD CONSTRAINT content_signal_places_pkey PRIMARY KEY (signal_id, place_id);


--
-- Name: content_signal_runs content_signal_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signal_runs
    ADD CONSTRAINT content_signal_runs_pkey PRIMARY KEY (hash_id, detector);


--
-- Name: content_signals content_signals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signals
    ADD CONSTRAINT content_signals_pkey PRIMARY KEY (id);


--
-- Name: contents contents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contents
    ADD CONSTRAINT contents_pkey PRIMARY KEY (id);


--
-- Name: contents_raw contents_raw_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contents_raw
    ADD CONSTRAINT contents_raw_pkey PRIMARY KEY (id);


--
-- Name: geo_gazetteer_loads geo_gazetteer_loads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geo_gazetteer_loads
    ADD CONSTRAINT geo_gazetteer_loads_pkey PRIMARY KEY (id);


--
-- Name: geo_place_names geo_place_names_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geo_place_names
    ADD CONSTRAINT geo_place_names_pkey PRIMARY KEY (id);


--
-- Name: geo_places geo_places_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geo_places
    ADD CONSTRAINT geo_places_pkey PRIMARY KEY (id);


--
-- Name: hash_contexts hash_contexts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hash_contexts
    ADD CONSTRAINT hash_contexts_pkey PRIMARY KEY (id);


--
-- Name: hashs hashs_hash_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hashs
    ADD CONSTRAINT hashs_hash_key UNIQUE (hash);


--
-- Name: hashs hashs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hashs
    ADD CONSTRAINT hashs_pkey PRIMARY KEY (id);


--
-- Name: job_events job_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_events
    ADD CONSTRAINT job_events_pkey PRIMARY KEY (event_id);


--
-- Name: job_schedules job_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_schedules
    ADD CONSTRAINT job_schedules_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (job_id);


--
-- Name: keywords keywords_keyword_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.keywords
    ADD CONSTRAINT keywords_keyword_key UNIQUE (keyword);


--
-- Name: keywords keywords_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.keywords
    ADD CONSTRAINT keywords_pkey PRIMARY KEY (id);


--
-- Name: monitoring_rule_versions monitoring_rule_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monitoring_rule_versions
    ADD CONSTRAINT monitoring_rule_versions_pkey PRIMARY KEY (rule_id, version);


--
-- Name: monitoring_rules monitoring_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monitoring_rules
    ADD CONSTRAINT monitoring_rules_pkey PRIMARY KEY (id);


--
-- Name: path_geo_mentions_m0015 path_geo_mentions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.path_geo_mentions_m0015
    ADD CONSTRAINT path_geo_mentions_pkey PRIMARY KEY (id);


--
-- Name: path_revisions path_revisions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.path_revisions
    ADD CONSTRAINT path_revisions_pkey PRIMARY KEY (id);


--
-- Name: paths paths_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paths
    ADD CONSTRAINT paths_pkey PRIMARY KEY (id);


--
-- Name: report_baselines pk_report_baselines; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_baselines
    ADD CONSTRAINT pk_report_baselines PRIMARY KEY (user_id, criteria_hash);


--
-- Name: punctuation punctuation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.punctuation
    ADD CONSTRAINT punctuation_pkey PRIMARY KEY (id);


--
-- Name: punctuation punctuation_punctuation_text_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.punctuation
    ADD CONSTRAINT punctuation_punctuation_text_key UNIQUE (punctuation_text);


--
-- Name: report_artifacts report_artifacts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_artifacts
    ADD CONSTRAINT report_artifacts_pkey PRIMARY KEY (id);


--
-- Name: report_run_analyses report_run_analyses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_run_analyses
    ADD CONSTRAINT report_run_analyses_pkey PRIMARY KEY (run_id, "position");


--
-- Name: report_run_datasets report_run_datasets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_run_datasets
    ADD CONSTRAINT report_run_datasets_pkey PRIMARY KEY (run_id, "position");


--
-- Name: report_runs report_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_runs
    ADD CONSTRAINT report_runs_pkey PRIMARY KEY (id);


--
-- Name: rule_evaluations rule_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_evaluations
    ADD CONSTRAINT rule_evaluations_pkey PRIMARY KEY (id);


--
-- Name: rule_subject_ledger rule_subject_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_subject_ledger
    ADD CONSTRAINT rule_subject_ledger_pkey PRIMARY KEY (rule_id, subject_key);


--
-- Name: saved_search_imports saved_search_imports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saved_search_imports
    ADD CONSTRAINT saved_search_imports_pkey PRIMARY KEY (id);


--
-- Name: saved_searches saved_searches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saved_searches
    ADD CONSTRAINT saved_searches_pkey PRIMARY KEY (id);


--
-- Name: scenario_evaluations scenario_evaluations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_evaluations
    ADD CONSTRAINT scenario_evaluations_pkey PRIMARY KEY (id);


--
-- Name: scenario_outcomes scenario_outcomes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_outcomes
    ADD CONSTRAINT scenario_outcomes_pkey PRIMARY KEY (id);


--
-- Name: scenario_versions scenario_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_versions
    ADD CONSTRAINT scenario_versions_pkey PRIMARY KEY (scenario_id, version);


--
-- Name: scenarios scenarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id);


--
-- Name: sides sides_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sides
    ADD CONSTRAINT sides_name_key UNIQUE (name);


--
-- Name: sides sides_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sides
    ADD CONSTRAINT sides_pkey PRIMARY KEY (id);


--
-- Name: sources sources_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_name_key UNIQUE (name);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: titles_content titles_content_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.titles_content
    ADD CONSTRAINT titles_content_pkey PRIMARY KEY (id);


--
-- Name: translation_overrides translation_overrides_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.translation_overrides
    ADD CONSTRAINT translation_overrides_pkey PRIMARY KEY (locale, message_key);


--
-- Name: analyst_file_categories unique_analyst_file_category; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyst_file_categories
    ADD CONSTRAINT unique_analyst_file_category UNIQUE (path_id, category_id);


--
-- Name: words_categorys unique_word_category; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words_categorys
    ADD CONSTRAINT unique_word_category UNIQUE (word_id, category_id);


--
-- Name: content_signals uq_content_signals_dedup; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signals
    ADD CONSTRAINT uq_content_signals_dedup UNIQUE (dedup_key);


--
-- Name: contents_raw uq_contents_raw_hash_chunk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contents_raw
    ADD CONSTRAINT uq_contents_raw_hash_chunk UNIQUE (hash_id, chunk_seq);


--
-- Name: geo_place_names uq_geo_place_names; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geo_place_names
    ADD CONSTRAINT uq_geo_place_names UNIQUE (place_id, language, match_key);


--
-- Name: geo_places uq_geo_places_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geo_places
    ADD CONSTRAINT uq_geo_places_key UNIQUE (place_key);


--
-- Name: hash_contexts uq_hash_contexts_hash_source_side; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hash_contexts
    ADD CONSTRAINT uq_hash_contexts_hash_source_side UNIQUE (hash_id, source_id, side_id);


--
-- Name: hash_contexts uq_hash_contexts_identity; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hash_contexts
    ADD CONSTRAINT uq_hash_contexts_identity UNIQUE (hash_id, source_id, side_id);


--
-- Name: job_schedules uq_job_schedules_owner_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_schedules
    ADD CONSTRAINT uq_job_schedules_owner_name UNIQUE (owner_user_id, name);


--
-- Name: keywords_hashs uq_keywords_hashs_hash_keyword; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.keywords_hashs
    ADD CONSTRAINT uq_keywords_hashs_hash_keyword UNIQUE (hash_id, keyword_id);


--
-- Name: path_geo_mentions_m0015 uq_path_geo_mentions_hash_place; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.path_geo_mentions_m0015
    ADD CONSTRAINT uq_path_geo_mentions_hash_place UNIQUE (hash_id, place_name);


--
-- Name: report_run_analyses uq_report_run_analyses_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_run_analyses
    ADD CONSTRAINT uq_report_run_analyses_key UNIQUE (run_id, analysis_key);


--
-- Name: report_run_datasets uq_report_run_datasets_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_run_datasets
    ADD CONSTRAINT uq_report_run_datasets_key UNIQUE (run_id, dataset_key);


--
-- Name: saved_search_imports uq_saved_search_imports_sha; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saved_search_imports
    ADD CONSTRAINT uq_saved_search_imports_sha UNIQUE (file_sha256);


--
-- Name: saved_searches uq_saved_searches_legacy; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saved_searches
    ADD CONSTRAINT uq_saved_searches_legacy UNIQUE (legacy_source, legacy_id);


--
-- Name: words_hashs uq_words_hashs_hash_word; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words_hashs
    ADD CONSTRAINT uq_words_hashs_hash_word UNIQUE (hash_id, word_id);


--
-- Name: user_navigation_prefs user_navigation_prefs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_navigation_prefs
    ADD CONSTRAINT user_navigation_prefs_pkey PRIMARY KEY (user_id, interface_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: words words_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words
    ADD CONSTRAINT words_pkey PRIMARY KEY (id);


--
-- Name: words words_word_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words
    ADD CONSTRAINT words_word_key UNIQUE (word);


--
-- Name: idx_acl_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_acl_action ON public.analyst_categorization_log USING btree (action);


--
-- Name: idx_acl_analyst_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_acl_analyst_id ON public.analyst_categorization_log USING btree (analyst_id);


--
-- Name: idx_acl_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_acl_category_id ON public.analyst_categorization_log USING btree (category_id);


--
-- Name: idx_acl_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_acl_created_at ON public.analyst_categorization_log USING btree (created_at DESC);


--
-- Name: idx_afc_assigned_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_afc_assigned_at ON public.analyst_file_categories USING btree (assigned_at DESC);


--
-- Name: idx_afc_assigned_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_afc_assigned_by ON public.analyst_file_categories USING btree (assigned_by);


--
-- Name: idx_afc_category_assigned_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_afc_category_assigned_at ON public.analyst_file_categories USING btree (category_id, assigned_at DESC);


--
-- Name: idx_afc_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_afc_category_id ON public.analyst_file_categories USING btree (category_id);


--
-- Name: idx_afc_path_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_afc_path_id ON public.analyst_file_categories USING btree (path_id);


--
-- Name: idx_alerts_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_created_at ON public.alerts USING btree (created_at);


--
-- Name: idx_alerts_dismissed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_dismissed ON public.alerts USING btree (dismissed);


--
-- Name: idx_alerts_dismissed_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_dismissed_created ON public.alerts USING btree (dismissed, created_at DESC);


--
-- Name: idx_alerts_event_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_event_date ON public.alerts USING btree (event_date);


--
-- Name: idx_alerts_file_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_file_id ON public.alerts USING btree (file_id);


--
-- Name: idx_alerts_metadata_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_metadata_hash ON public.alerts USING btree (((metadata ->> 'hash'::text))) WHERE ((type)::text = 'similar_files'::text);


--
-- Name: idx_alerts_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_priority ON public.alerts USING btree (priority);


--
-- Name: idx_alerts_read; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_read ON public.alerts USING btree (read);


--
-- Name: idx_alerts_recipient_dismissed_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_recipient_dismissed_created ON public.alerts USING btree (recipient_user_id, dismissed, created_at DESC);


--
-- Name: idx_alerts_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_type ON public.alerts USING btree (type);


--
-- Name: idx_alerts_type_dismissed_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_type_dismissed_created ON public.alerts USING btree (type, dismissed, created_at DESC);


--
-- Name: idx_alerts_type_event_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_alerts_type_event_date ON public.alerts USING btree (type, event_date);


--
-- Name: idx_analyst_categories_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analyst_categories_created_by ON public.analyst_categories USING btree (created_by);


--
-- Name: idx_analyst_categories_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_analyst_categories_name ON public.analyst_categories USING btree (name);


--
-- Name: idx_audit_log_action; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_action ON public.audit_log USING btree (action);


--
-- Name: idx_audit_log_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_created_at ON public.audit_log USING btree (created_at DESC);


--
-- Name: idx_audit_log_resource_prefix; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_resource_prefix ON public.audit_log USING btree (resource text_pattern_ops);


--
-- Name: idx_audit_log_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_user_id ON public.audit_log USING btree (user_id);


--
-- Name: idx_audit_log_user_id_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_user_id_id ON public.audit_log USING btree (user_id, id DESC);


--
-- Name: idx_audit_log_username_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_audit_log_username_id ON public.audit_log USING btree (username, id DESC);


--
-- Name: idx_categorys_word_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_categorys_word_id ON public.categorys USING btree (word_id);


--
-- Name: idx_content_signal_places_place; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signal_places_place ON public.content_signal_places USING btree (place_id, signal_id);


--
-- Name: idx_content_signal_runs_ran_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signal_runs_ran_at ON public.content_signal_runs USING btree (ran_at DESC, hash_id DESC, detector);


--
-- Name: idx_content_signal_runs_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signal_runs_version ON public.content_signal_runs USING btree (detector, detector_ver);


--
-- Name: idx_content_signals_confidence; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signals_confidence ON public.content_signals USING btree (signal_type, confidence);


--
-- Name: idx_content_signals_dates; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signals_dates ON public.content_signals USING btree (date_from, date_to) WHERE (date_from IS NOT NULL);


--
-- Name: idx_content_signals_detector; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signals_detector ON public.content_signals USING btree (detector, signal_type, resolution);


--
-- Name: idx_content_signals_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signals_hash ON public.content_signals USING btree (hash_id);


--
-- Name: idx_content_signals_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_content_signals_type ON public.content_signals USING btree (signal_type, detector, detector_ver);


--
-- Name: idx_contents_content_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_contents_content_date ON public.contents USING btree (content_date);


--
-- Name: idx_contents_hash_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_contents_hash_id ON public.contents USING btree (hash_id);


--
-- Name: idx_contents_raw_hash_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_contents_raw_hash_id ON public.contents_raw USING btree (hash_id);


--
-- Name: idx_geo_place_names_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_geo_place_names_key ON public.geo_place_names USING btree (match_key);


--
-- Name: idx_geo_place_names_place; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_geo_place_names_place ON public.geo_place_names USING btree (place_id);


--
-- Name: idx_hash_contexts_hash_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_hash_contexts_hash_id ON public.hash_contexts USING btree (hash_id);


--
-- Name: idx_hash_contexts_side_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_hash_contexts_side_id ON public.hash_contexts USING btree (side_id);


--
-- Name: idx_hash_contexts_source_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_hash_contexts_source_id ON public.hash_contexts USING btree (source_id);


--
-- Name: idx_hashs_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_hashs_hash ON public.hashs USING btree (hash);


--
-- Name: idx_job_events_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_job_events_job ON public.job_events USING btree (job_id, event_id);


--
-- Name: idx_job_schedules_due; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_job_schedules_due ON public.job_schedules USING btree (next_run_at) WHERE enabled;


--
-- Name: idx_job_schedules_owner; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_job_schedules_owner ON public.job_schedules USING btree (owner_user_id);


--
-- Name: idx_jobs_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_created_at ON public.jobs USING btree (created_at DESC);


--
-- Name: idx_jobs_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_jobs_status ON public.jobs USING btree (status);


--
-- Name: idx_keywords_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_keywords_category_id ON public.keywords USING btree (category_id);


--
-- Name: idx_keywords_hashs_hash_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_keywords_hashs_hash_id ON public.keywords_hashs USING btree (hash_id);


--
-- Name: idx_keywords_hashs_keyword_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_keywords_hashs_keyword_id ON public.keywords_hashs USING btree (keyword_id);


--
-- Name: idx_keywords_paths_keyword_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_keywords_paths_keyword_id ON public.keywords_hashs USING btree (keyword_id);


--
-- Name: idx_monitoring_rules_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_monitoring_rules_active ON public.monitoring_rules USING btree (id) WHERE ((status)::text = 'active'::text);


--
-- Name: idx_monitoring_rules_saved_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_monitoring_rules_saved_search ON public.monitoring_rules USING btree (saved_search_id) WHERE (saved_search_id IS NOT NULL);


--
-- Name: idx_path_geo_mentions_hash_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_path_geo_mentions_hash_id ON public.path_geo_mentions_m0015 USING btree (hash_id);


--
-- Name: idx_path_geo_mentions_place_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_path_geo_mentions_place_name ON public.path_geo_mentions_m0015 USING btree (place_name);


--
-- Name: idx_path_revisions_changed_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_path_revisions_changed_at ON public.path_revisions USING btree (changed_at DESC);


--
-- Name: idx_path_revisions_path_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_path_revisions_path_id ON public.path_revisions USING btree (path_id, changed_at DESC);


--
-- Name: idx_paths_context_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_context_id ON public.paths USING btree (context_id);


--
-- Name: idx_paths_date_creation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_date_creation ON public.paths USING btree (date_creation);


--
-- Name: idx_paths_file_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_file_name ON public.paths USING btree (file_name);


--
-- Name: idx_paths_file_path; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_file_path ON public.paths USING btree (file_path);


--
-- Name: idx_paths_file_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_file_status ON public.paths USING btree (file_status);


--
-- Name: idx_paths_file_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_file_type ON public.paths USING btree (file_type);


--
-- Name: idx_paths_parent_path_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_parent_path_id ON public.paths USING btree (parent_path_id);


--
-- Name: idx_paths_processing_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_paths_processing_status ON public.paths USING btree (processing_status);


--
-- Name: idx_punctuation_text; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_punctuation_text ON public.punctuation USING btree (punctuation_text);


--
-- Name: idx_report_artifacts_creator; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_report_artifacts_creator ON public.report_artifacts USING btree (created_by, created_at DESC);


--
-- Name: idx_report_artifacts_run; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_report_artifacts_run ON public.report_artifacts USING btree (run_id, id);


--
-- Name: idx_report_baselines_user_seen; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_report_baselines_user_seen ON public.report_baselines USING btree (user_id, last_seen_at DESC);


--
-- Name: idx_report_runs_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_report_runs_job ON public.report_runs USING btree (job_id);


--
-- Name: idx_report_runs_report; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_report_runs_report ON public.report_runs USING btree (report_id, requested_at DESC, id DESC);


--
-- Name: idx_report_runs_requester; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_report_runs_requester ON public.report_runs USING btree (requested_by, requested_at DESC, id DESC);


--
-- Name: idx_report_runs_saved_search; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_report_runs_saved_search ON public.report_runs USING btree (saved_search_id) WHERE (saved_search_id IS NOT NULL);


--
-- Name: idx_rule_evaluations_rule; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rule_evaluations_rule ON public.rule_evaluations USING btree (rule_id, id DESC);


--
-- Name: idx_rule_ledger_alert; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rule_ledger_alert ON public.rule_subject_ledger USING btree (alert_id) WHERE (alert_id IS NOT NULL);


--
-- Name: idx_rule_ledger_pending; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_rule_ledger_pending ON public.rule_subject_ledger USING btree (rule_id, first_matched_at) WHERE ((state)::text = 'pending'::text);


--
-- Name: idx_saved_searches_fingerprint; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_saved_searches_fingerprint ON public.saved_searches USING btree (criteria_fingerprint);


--
-- Name: idx_saved_searches_monitor; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_saved_searches_monitor ON public.saved_searches USING btree (id) WHERE monitor_enabled;


--
-- Name: idx_saved_searches_owner_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_saved_searches_owner_created ON public.saved_searches USING btree (owner_user_id, created_at DESC);


--
-- Name: idx_scenario_evaluations_scenario; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_scenario_evaluations_scenario ON public.scenario_evaluations USING btree (scenario_id, kind, id DESC);


--
-- Name: idx_scenario_outcomes_evaluation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_scenario_outcomes_evaluation ON public.scenario_outcomes USING btree (evaluation_id);


--
-- Name: idx_scenario_outcomes_latest; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_scenario_outcomes_latest ON public.scenario_outcomes USING btree (scenario_id, hash_id, id DESC);


--
-- Name: idx_scenarios_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_scenarios_active ON public.scenarios USING btree (id) WHERE ((status)::text = 'active'::text);


--
-- Name: idx_sessions_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_expires_at ON public.sessions USING btree (expires_at);


--
-- Name: idx_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sessions_user_id ON public.sessions USING btree (user_id);


--
-- Name: idx_sides_date_creation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sides_date_creation ON public.sides USING btree (date_creation);


--
-- Name: idx_sides_importance; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sides_importance ON public.sides USING btree (importance DESC);


--
-- Name: idx_sources_access_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_access_status ON public.sources USING btree (access_status);


--
-- Name: idx_sources_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_category_id ON public.sources USING btree (category_id);


--
-- Name: idx_sources_country; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_country ON public.sources USING btree (country);


--
-- Name: idx_sources_date_creation; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_date_creation ON public.sources USING btree (date_creation);


--
-- Name: idx_sources_entry_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_entry_date ON public.sources USING btree (entry_date);


--
-- Name: idx_sources_importance; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_importance ON public.sources USING btree (importance DESC);


--
-- Name: idx_sources_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_job ON public.sources USING btree (job);


--
-- Name: idx_sources_ownership; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_sources_ownership ON public.sources USING btree (ownership);


--
-- Name: idx_titles_content_hash_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_titles_content_hash_id ON public.titles_content USING btree (hash_id);


--
-- Name: idx_titles_content_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_titles_content_status ON public.titles_content USING btree (title_status);


--
-- Name: idx_user_navigation_prefs_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_navigation_prefs_user ON public.user_navigation_prefs USING btree (user_id);


--
-- Name: idx_wc_category_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_wc_category_id ON public.words_categorys USING btree (category_id);


--
-- Name: idx_wc_word_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_wc_word_id ON public.words_categorys USING btree (word_id);


--
-- Name: idx_words_hashs_hash_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_words_hashs_hash_id ON public.words_hashs USING btree (hash_id);


--
-- Name: idx_words_hashs_word_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_words_hashs_word_id ON public.words_hashs USING btree (word_id);


--
-- Name: idx_words_paths_word_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_words_paths_word_id ON public.words_hashs USING btree (word_id);


--
-- Name: idx_words_word; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_words_word ON public.words USING btree (word);


--
-- Name: uq_analyst_categories_lower_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_analyst_categories_lower_name ON public.analyst_categories USING btree (lower((name)::text));


--
-- Name: uq_monitoring_rules_owner_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_monitoring_rules_owner_name ON public.monitoring_rules USING btree (owner_user_id, lower((name)::text)) WHERE ((status)::text <> 'archived'::text);


--
-- Name: uq_report_artifacts_rendering; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_report_artifacts_rendering ON public.report_artifacts USING btree (run_id, format, COALESCE(dataset_key, ''::character varying), renderer_version, language);


--
-- Name: uq_scenarios_owner_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX uq_scenarios_owner_name ON public.scenarios USING btree (owner_user_id, lower((name)::text)) WHERE ((status)::text <> 'archived'::text);


--
-- Name: path_geo_mentions _RETURN; Type: RULE; Schema: public; Owner: postgres
--

CREATE OR REPLACE VIEW public.path_geo_mentions AS
 SELECT s.hash_id,
    g.label AS place_name,
    (( SELECT string_agg((c.label)::text, ', '::text ORDER BY (c.label)::text) AS string_agg
           FROM public.geo_places c
          WHERE (((c.feature_type)::text = 'country'::text) AND (NOT c.retired) AND (cardinality(c.country_codes) = 1) AND (c.country_codes <@ g.country_codes))))::character varying(255) AS country,
    g.latitude,
    g.longitude,
    (count(*))::integer AS mention_count,
    g.place_key,
    'signals'::character varying(16) AS provenance
   FROM ((public.content_signals s
     JOIN public.content_signal_places csp ON ((csp.signal_id = s.id)))
     JOIN public.geo_places g ON ((g.id = csp.place_id)))
  WHERE (((s.detector)::text = 'places'::text) AND ((s.resolution)::text = 'identified'::text) AND ((s.confidence)::text = ANY ((ARRAY['high'::character varying, 'medium'::character varying])::text[])) AND (g.latitude IS NOT NULL))
  GROUP BY s.hash_id, g.id
UNION ALL
 SELECT m.hash_id,
    m.place_name,
    m.country,
    m.latitude,
    m.longitude,
    m.mention_count,
    NULL::character varying(64) AS place_key,
    'legacy_m0015'::character varying(16) AS provenance
   FROM public.path_geo_mentions_m0015 m
  WHERE (NOT (EXISTS ( SELECT 1
           FROM public.content_signal_runs r
          WHERE ((r.hash_id = m.hash_id) AND ((r.detector)::text = 'places'::text) AND ((r.status)::text <> 'failed'::text)))));


--
-- Name: report_artifacts trg_report_artifacts_immutable; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_report_artifacts_immutable BEFORE UPDATE ON public.report_artifacts FOR EACH ROW EXECUTE FUNCTION public.report_artifacts_immutable();


--
-- Name: report_run_analyses trg_report_run_analyses_write_once; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_report_run_analyses_write_once BEFORE UPDATE ON public.report_run_analyses FOR EACH ROW EXECUTE FUNCTION public.report_run_analyses_write_once();


--
-- Name: report_run_datasets trg_report_run_datasets_write_once; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_report_run_datasets_write_once BEFORE UPDATE ON public.report_run_datasets FOR EACH ROW EXECUTE FUNCTION public.report_run_datasets_write_once();


--
-- Name: report_runs trg_report_runs_terminal_immutable; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_report_runs_terminal_immutable BEFORE UPDATE ON public.report_runs FOR EACH ROW EXECUTE FUNCTION public.report_runs_terminal_immutable();


--
-- Name: scenario_outcomes trg_scenario_outcomes_append_only; Type: TRIGGER; Schema: public; Owner: postgres
--

CREATE TRIGGER trg_scenario_outcomes_append_only BEFORE DELETE OR UPDATE ON public.scenario_outcomes FOR EACH ROW EXECUTE FUNCTION public.scenario_outcomes_append_only();


--
-- Name: alerts alerts_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.paths(id) ON DELETE CASCADE;


--
-- Name: alerts alerts_recipient_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_recipient_user_id_fkey FOREIGN KEY (recipient_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: alerts alerts_rule_evaluation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_rule_evaluation_id_fkey FOREIGN KEY (rule_evaluation_id) REFERENCES public.rule_evaluations(id) ON DELETE SET NULL;


--
-- Name: alerts alerts_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.monitoring_rules(id) ON DELETE SET NULL;


--
-- Name: alerts alerts_scenario_evaluation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_scenario_evaluation_id_fkey FOREIGN KEY (scenario_evaluation_id) REFERENCES public.scenario_evaluations(id) ON DELETE SET NULL;


--
-- Name: alerts alerts_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE SET NULL;


--
-- Name: analyst_file_categories analyst_file_categories_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyst_file_categories
    ADD CONSTRAINT analyst_file_categories_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.analyst_categories(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: analyst_file_categories analyst_file_categories_path_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analyst_file_categories
    ADD CONSTRAINT analyst_file_categories_path_id_fkey FOREIGN KEY (path_id) REFERENCES public.paths(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: categorys categorys_word_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categorys
    ADD CONSTRAINT categorys_word_id_fkey FOREIGN KEY (word_id) REFERENCES public.words(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: content_signal_places content_signal_places_place_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signal_places
    ADD CONSTRAINT content_signal_places_place_id_fkey FOREIGN KEY (place_id) REFERENCES public.geo_places(id) ON DELETE RESTRICT;


--
-- Name: content_signal_places content_signal_places_signal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signal_places
    ADD CONSTRAINT content_signal_places_signal_id_fkey FOREIGN KEY (signal_id) REFERENCES public.content_signals(id) ON DELETE CASCADE;


--
-- Name: content_signal_runs content_signal_runs_hash_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signal_runs
    ADD CONSTRAINT content_signal_runs_hash_id_fkey FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON DELETE CASCADE;


--
-- Name: content_signals content_signals_hash_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.content_signals
    ADD CONSTRAINT content_signals_hash_id_fkey FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON DELETE CASCADE;


--
-- Name: contents fk_contents_hash; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contents
    ADD CONSTRAINT fk_contents_hash FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: contents_raw fk_contents_raw_hash; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contents_raw
    ADD CONSTRAINT fk_contents_raw_hash FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: hash_contexts fk_hash_contexts_hash; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hash_contexts
    ADD CONSTRAINT fk_hash_contexts_hash FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON UPDATE CASCADE;


--
-- Name: keywords_hashs fk_keywords_hashs_hash; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.keywords_hashs
    ADD CONSTRAINT fk_keywords_hashs_hash FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: paths fk_paths_context; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paths
    ADD CONSTRAINT fk_paths_context FOREIGN KEY (context_id) REFERENCES public.hash_contexts(id) ON UPDATE CASCADE;


--
-- Name: paths fk_paths_parent; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paths
    ADD CONSTRAINT fk_paths_parent FOREIGN KEY (parent_path_id) REFERENCES public.paths(id) ON DELETE SET NULL;


--
-- Name: scenarios fk_scenarios_activated_dry_run; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT fk_scenarios_activated_dry_run FOREIGN KEY (activated_dry_run_id) REFERENCES public.scenario_evaluations(id);


--
-- Name: titles_content fk_titles_content_hash; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.titles_content
    ADD CONSTRAINT fk_titles_content_hash FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: words_hashs fk_words_hashs_hash; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words_hashs
    ADD CONSTRAINT fk_words_hashs_hash FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: geo_place_names geo_place_names_place_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geo_place_names
    ADD CONSTRAINT geo_place_names_place_id_fkey FOREIGN KEY (place_id) REFERENCES public.geo_places(id) ON DELETE CASCADE;


--
-- Name: hash_contexts hash_contexts_side_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hash_contexts
    ADD CONSTRAINT hash_contexts_side_id_fkey FOREIGN KEY (side_id) REFERENCES public.sides(id) ON UPDATE CASCADE;


--
-- Name: hash_contexts hash_contexts_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hash_contexts
    ADD CONSTRAINT hash_contexts_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id) ON UPDATE CASCADE;


--
-- Name: job_events job_events_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_events
    ADD CONSTRAINT job_events_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.jobs(job_id) ON DELETE CASCADE;


--
-- Name: job_schedules job_schedules_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_schedules
    ADD CONSTRAINT job_schedules_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: keywords keywords_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.keywords
    ADD CONSTRAINT keywords_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categorys(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: keywords_hashs keywords_paths_keyword_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.keywords_hashs
    ADD CONSTRAINT keywords_paths_keyword_id_fkey FOREIGN KEY (keyword_id) REFERENCES public.keywords(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: monitoring_rule_versions monitoring_rule_versions_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monitoring_rule_versions
    ADD CONSTRAINT monitoring_rule_versions_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: monitoring_rule_versions monitoring_rule_versions_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monitoring_rule_versions
    ADD CONSTRAINT monitoring_rule_versions_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.monitoring_rules(id) ON DELETE CASCADE;


--
-- Name: monitoring_rules monitoring_rules_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monitoring_rules
    ADD CONSTRAINT monitoring_rules_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: monitoring_rules monitoring_rules_saved_search_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.monitoring_rules
    ADD CONSTRAINT monitoring_rules_saved_search_id_fkey FOREIGN KEY (saved_search_id) REFERENCES public.saved_searches(id) ON DELETE SET NULL;


--
-- Name: path_geo_mentions_m0015 path_geo_mentions_hash_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.path_geo_mentions_m0015
    ADD CONSTRAINT path_geo_mentions_hash_id_fkey FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: path_revisions path_revisions_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.path_revisions
    ADD CONSTRAINT path_revisions_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: path_revisions path_revisions_path_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.path_revisions
    ADD CONSTRAINT path_revisions_path_id_fkey FOREIGN KEY (path_id) REFERENCES public.paths(id) ON DELETE CASCADE;


--
-- Name: report_artifacts report_artifacts_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_artifacts
    ADD CONSTRAINT report_artifacts_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: report_artifacts report_artifacts_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_artifacts
    ADD CONSTRAINT report_artifacts_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.report_runs(id) ON DELETE CASCADE;


--
-- Name: report_baselines report_baselines_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_baselines
    ADD CONSTRAINT report_baselines_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: report_run_analyses report_run_analyses_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_run_analyses
    ADD CONSTRAINT report_run_analyses_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.report_runs(id) ON DELETE CASCADE;


--
-- Name: report_run_datasets report_run_datasets_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_run_datasets
    ADD CONSTRAINT report_run_datasets_run_id_fkey FOREIGN KEY (run_id) REFERENCES public.report_runs(id) ON DELETE CASCADE;


--
-- Name: report_runs report_runs_requested_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_runs
    ADD CONSTRAINT report_runs_requested_by_fkey FOREIGN KEY (requested_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: report_runs report_runs_saved_search_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.report_runs
    ADD CONSTRAINT report_runs_saved_search_id_fkey FOREIGN KEY (saved_search_id) REFERENCES public.saved_searches(id) ON DELETE SET NULL;


--
-- Name: rule_evaluations rule_evaluations_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_evaluations
    ADD CONSTRAINT rule_evaluations_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.monitoring_rules(id) ON DELETE CASCADE;


--
-- Name: rule_subject_ledger rule_subject_ledger_alert_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_subject_ledger
    ADD CONSTRAINT rule_subject_ledger_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES public.alerts(id) ON DELETE SET NULL;


--
-- Name: rule_subject_ledger rule_subject_ledger_hash_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_subject_ledger
    ADD CONSTRAINT rule_subject_ledger_hash_id_fkey FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON DELETE CASCADE;


--
-- Name: rule_subject_ledger rule_subject_ledger_matched_evaluation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_subject_ledger
    ADD CONSTRAINT rule_subject_ledger_matched_evaluation_id_fkey FOREIGN KEY (matched_evaluation_id) REFERENCES public.rule_evaluations(id) ON DELETE CASCADE;


--
-- Name: rule_subject_ledger rule_subject_ledger_notified_evaluation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_subject_ledger
    ADD CONSTRAINT rule_subject_ledger_notified_evaluation_id_fkey FOREIGN KEY (notified_evaluation_id) REFERENCES public.rule_evaluations(id) ON DELETE SET NULL;


--
-- Name: rule_subject_ledger rule_subject_ledger_rule_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rule_subject_ledger
    ADD CONSTRAINT rule_subject_ledger_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES public.monitoring_rules(id) ON DELETE CASCADE;


--
-- Name: saved_searches saved_searches_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.saved_searches
    ADD CONSTRAINT saved_searches_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: scenario_evaluations scenario_evaluations_requested_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_evaluations
    ADD CONSTRAINT scenario_evaluations_requested_by_user_id_fkey FOREIGN KEY (requested_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: scenario_evaluations scenario_evaluations_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_evaluations
    ADD CONSTRAINT scenario_evaluations_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE CASCADE;


--
-- Name: scenario_outcomes scenario_outcomes_evaluation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_outcomes
    ADD CONSTRAINT scenario_outcomes_evaluation_id_fkey FOREIGN KEY (evaluation_id) REFERENCES public.scenario_evaluations(id) ON DELETE CASCADE;


--
-- Name: scenario_outcomes scenario_outcomes_hash_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_outcomes
    ADD CONSTRAINT scenario_outcomes_hash_id_fkey FOREIGN KEY (hash_id) REFERENCES public.hashs(id) ON DELETE CASCADE;


--
-- Name: scenario_outcomes scenario_outcomes_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_outcomes
    ADD CONSTRAINT scenario_outcomes_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE CASCADE;


--
-- Name: scenario_versions scenario_versions_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_versions
    ADD CONSTRAINT scenario_versions_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: scenario_versions scenario_versions_scenario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenario_versions
    ADD CONSTRAINT scenario_versions_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.scenarios(id) ON DELETE CASCADE;


--
-- Name: scenarios scenarios_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scenarios
    ADD CONSTRAINT scenarios_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: sources sources_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categorys(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: titles_content titles_content_title_content_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.titles_content
    ADD CONSTRAINT titles_content_title_content_id_fkey FOREIGN KEY (title_content_id) REFERENCES public.titles_content(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: translation_overrides translation_overrides_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.translation_overrides
    ADD CONSTRAINT translation_overrides_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_navigation_prefs user_navigation_prefs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_navigation_prefs
    ADD CONSTRAINT user_navigation_prefs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: words_categorys words_categorys_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words_categorys
    ADD CONSTRAINT words_categorys_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categorys(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: words_categorys words_categorys_word_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words_categorys
    ADD CONSTRAINT words_categorys_word_id_fkey FOREIGN KEY (word_id) REFERENCES public.words(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: words_hashs words_paths_word_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.words_hashs
    ADD CONSTRAINT words_paths_word_id_fkey FOREIGN KEY (word_id) REFERENCES public.words(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict t8eWpW1pfHeOGwLZ1QcfznnSc9OjvVOr59Q5WqFFWwolVrBlbT7LydFuTGjRKyn

