-- ScopeGuard - Tier 1 v2 migration
-- Run in Supabase SQL Editor AFTER Phase 1 schema exists.
-- Safe to re-run: uses IF NOT EXISTS / IF NOT EXISTS columns pattern.

-- ---------------------------------------------------------------------------
-- New tables
-- ---------------------------------------------------------------------------

create table if not exists clients (
  id uuid primary key default gen_random_uuid(),
  freelancer_slack_id text not null,
  client_slack_id text not null,
  client_label text,
  created_at timestamptz default now(),
  unique (freelancer_slack_id, client_slack_id)
);

create table if not exists absorbed_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  client_id uuid references clients(id) on delete set null,
  trigger_message_ts text,
  trigger_text text,
  task_summary text,
  estimated_value numeric,
  size text,
  source text default 'manual',
  created_at timestamptz default now()
);

create table if not exists revisions (
  id uuid primary key default gen_random_uuid(),
  deliverable_id uuid references deliverables(id) on delete cascade,
  trigger_message_ts text,
  created_at timestamptz default now()
);

-- ---------------------------------------------------------------------------
-- Alter existing tables (idempotent via DO blocks)
-- ---------------------------------------------------------------------------

alter table projects add column if not exists disclosure_ts text;
alter table projects add column if not exists retention_days int default 30;
alter table projects add column if not exists classification_enabled boolean default true;

alter table deliverables add column if not exists origin text default 'setup';
alter table deliverables add column if not exists revision_limit int;

alter table change_orders add column if not exists client_id uuid references clients(id) on delete set null;
alter table change_orders add column if not exists size text;
alter table change_orders add column if not exists estimated_value numeric;
alter table change_orders add column if not exists origin text default 'flag';

-- ---------------------------------------------------------------------------
-- RLS for new tables (dev - tighten for production)
-- ---------------------------------------------------------------------------

alter table clients enable row level security;
alter table absorbed_items enable row level security;
alter table revisions enable row level security;

drop policy if exists "service_role_all_clients" on clients;
create policy "service_role_all_clients" on clients
  for all using (true) with check (true);

drop policy if exists "service_role_all_absorbed_items" on absorbed_items;
create policy "service_role_all_absorbed_items" on absorbed_items
  for all using (true) with check (true);

drop policy if exists "service_role_all_revisions" on revisions;
create policy "service_role_all_revisions" on revisions
  for all using (true) with check (true);

-- ---------------------------------------------------------------------------
-- Backfill existing rows
-- ---------------------------------------------------------------------------

update projects
set disclosure_ts = extract(epoch from created_at)::text
where disclosure_ts is null;

update projects
set classification_enabled = true
where classification_enabled is null;

update projects
set retention_days = 30
where retention_days is null;

update deliverables
set origin = 'setup'
where origin is null;

update change_orders
set origin = 'flag'
where origin is null;
