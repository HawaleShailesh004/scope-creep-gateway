-- Scope Creep Gateway — full schema (Phase 1 + Tier 1 v2)
-- Run in Supabase SQL Editor for fresh installs.

-- projects: one row per client-freelancer project channel
create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  slack_channel_id text unique not null,
  slack_team_id text not null,
  freelancer_slack_id text not null,
  client_slack_id text,
  project_name text not null,
  budget_total numeric,
  currency text default 'INR',
  deadline date,
  canvas_id text,
  scope_health int default 100,
  disclosure_ts text,
  retention_days int default 30,
  classification_enabled boolean default true,
  created_at timestamptz default now()
);

-- client identity across projects
create table if not exists clients (
  id uuid primary key default gen_random_uuid(),
  freelancer_slack_id text not null,
  client_slack_id text not null,
  client_label text,
  created_at timestamptz default now(),
  unique (freelancer_slack_id, client_slack_id)
);

-- deliverables: in-scope items from setup or approved change orders
create table if not exists deliverables (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  description text not null,
  origin text default 'setup',
  revision_limit int
);

-- change_orders: flags, proposed/paid COs, dismissed
create table if not exists change_orders (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  client_id uuid references clients(id) on delete set null,
  trigger_message_ts text,
  trigger_text text,
  task_description text,
  estimated_cost numeric,
  timeline_impact_days int,
  status text default 'proposed',
  confidence numeric,
  prior_mention_found boolean default false,
  size text,
  estimated_value numeric,
  estimated_hours numeric,
  origin text default 'flag',
  created_at timestamptz default now()
);

-- absorbed (let-it-slide) items
create table if not exists absorbed_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references projects(id) on delete cascade,
  client_id uuid references clients(id) on delete set null,
  trigger_message_ts text,
  trigger_text text,
  task_summary text,
  estimated_value numeric,
  estimated_hours numeric,
  size text,
  source text default 'manual',
  created_at timestamptz default now()
);

-- revision round tracking per deliverable
create table if not exists revisions (
  id uuid primary key default gen_random_uuid(),
  deliverable_id uuid references deliverables(id) on delete cascade,
  trigger_message_ts text,
  created_at timestamptz default now()
);

-- Hackathon/dev: allow service role full access (tighten for production)
alter table projects enable row level security;
alter table clients enable row level security;
alter table deliverables enable row level security;
alter table change_orders enable row level security;
alter table absorbed_items enable row level security;
alter table revisions enable row level security;

create policy "service_role_all_projects" on projects
  for all using (true) with check (true);

create policy "service_role_all_clients" on clients
  for all using (true) with check (true);

create policy "service_role_all_deliverables" on deliverables
  for all using (true) with check (true);

create policy "service_role_all_change_orders" on change_orders
  for all using (true) with check (true);

create policy "service_role_all_absorbed_items" on absorbed_items
  for all using (true) with check (true);

create policy "service_role_all_revisions" on revisions
  for all using (true) with check (true);
