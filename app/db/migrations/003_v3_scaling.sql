-- v3 scaling: absorbed hours + change-order hours tracking

alter table absorbed_items
  add column if not exists estimated_hours numeric;

alter table change_orders
  add column if not exists estimated_hours numeric;
