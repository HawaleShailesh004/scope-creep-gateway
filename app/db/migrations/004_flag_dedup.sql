-- v4: prevent duplicate scope flags from Slack event retries.
-- Run in Supabase SQL Editor. Safe to re-run.

-- Remove any pre-existing duplicate 'flag' change orders (keep the earliest per
-- (project_id, trigger_message_ts)) so the unique index can be created. ctid
-- breaks ties when created_at is identical.
delete from change_orders c
using change_orders keep
where c.origin = 'flag'
  and keep.origin = 'flag'
  and c.project_id = keep.project_id
  and c.trigger_message_ts = keep.trigger_message_ts
  and c.trigger_message_ts is not null
  and (c.created_at, c.ctid) > (keep.created_at, keep.ctid);

-- One auto-generated scope flag per (project, triggering message).
create unique index if not exists uniq_change_order_flag_trigger
  on change_orders (project_id, trigger_message_ts)
  where origin = 'flag' and trigger_message_ts is not null;
