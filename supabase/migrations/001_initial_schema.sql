-- Managed Extractors API: initial schema
-- Run this in the Supabase SQL editor (Dashboard → SQL → New query)

create extension if not exists "pgcrypto";

create table if not exists public.extractors (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    urls jsonb not null default '[]'::jsonb,
    prompt text not null,
    schema_definition jsonb not null,
    schedule text,
    monitor_id text,
    status text not null default 'active'
        check (status in ('active', 'paused', 'error')),
    health text not null default 'healthy'
        check (health in ('healthy', 'warning', 'critical')),
    model_preference text not null default 'spark-1-mini'
        check (model_preference in ('spark-1-mini', 'spark-1-pro')),
    consecutive_failures integer not null default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.extraction_runs (
    id uuid primary key default gen_random_uuid(),
    extractor_id uuid not null references public.extractors (id) on delete cascade,
    status text not null
        check (status in ('running', 'completed', 'failed', 'repaired')),
    trigger text not null default 'manual'
        check (trigger in ('manual', 'monitor')),
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    duration_ms integer,
    data jsonb,
    validation_errors jsonb not null default '[]'::jsonb,
    was_repaired boolean not null default false,
    credits_used integer not null default 0,
    error text
);

create table if not exists public.drift_signals (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.extraction_runs (id) on delete cascade,
    field text not null,
    signal_type text not null
        check (signal_type in (
            'missing_field',
            'type_change',
            'empty_value',
            'value_anomaly',
            'new_field'
        )),
    expected text not null,
    actual text not null,
    severity text not null
        check (severity in ('low', 'medium', 'high'))
);

create table if not exists public.repair_attempts (
    id uuid primary key default gen_random_uuid(),
    run_id uuid not null references public.extraction_runs (id) on delete cascade,
    strategy text not null
        check (strategy in ('prompt_refinement', 'model_upgrade', 'fresh_scrape')),
    succeeded boolean not null default false,
    prompt_used text,
    model_used text,
    data jsonb,
    error text,
    duration_ms integer not null default 0,
    credits_used integer not null default 0
);

create index if not exists idx_extraction_runs_extractor_id
    on public.extraction_runs (extractor_id);

create index if not exists idx_extraction_runs_started_at
    on public.extraction_runs (started_at desc);

create index if not exists idx_drift_signals_run_id
    on public.drift_signals (run_id);

create index if not exists idx_repair_attempts_run_id
    on public.repair_attempts (run_id);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists extractors_set_updated_at on public.extractors;

create trigger extractors_set_updated_at
before update on public.extractors
for each row
execute function public.set_updated_at();
